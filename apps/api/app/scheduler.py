import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.alerts import evaluate_workflow
from app.config import settings
from app.database import SessionLocal
from app.health import compute_health_status
from app.models import Connection, Workflow
from app.sync import compute_workflow_counts, sync_connection

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_check_cycle() -> None:
    """One tick: sync every connection from n8n, then recompute health and
    fire/resolve alerts for every workflow. Runs on APScheduler's own thread
    with its own DB session - the request-scoped get_db() doesn't apply
    here. max_instances defaults to 1, so a slow cycle is never overlapped
    by the next tick.

    Each connection is wrapped individually so one bad connection (or one
    buggy workflow's health check) can't skip every other user's checks.
    """
    db = SessionLocal()
    try:
        connections = db.query(Connection).all()
        for connection in connections:
            try:
                sync_connection(db, connection)
            except Exception:
                logger.exception("Sync failed for connection %s", connection.id)
                continue

            workflows = db.query(Workflow).filter(Workflow.connection_id == connection.id).all()
            counts = compute_workflow_counts(db, [wf.id for wf in workflows])
            for workflow in workflows:
                try:
                    status = compute_health_status(workflow, counts[workflow.id])
                    evaluate_workflow(db, workflow, status)
                except Exception:
                    logger.exception("Health check failed for workflow %s", workflow.id)
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(run_check_cycle, "interval", minutes=settings.sync_interval_minutes, id="check_cycle")
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
