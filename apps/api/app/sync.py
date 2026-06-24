import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Connection, Execution, Workflow
from app.n8n_client import (
    N8nApiError,
    N8nClient,
    N8nConnectionError,
    N8nUnauthorizedError,
    parse_n8n_datetime,
)
from app.schemas import SyncResult
from app.security import decrypt_secret

ERROR_STATUSES = {"error", "crashed"}
EXECUTION_HISTORY_WINDOW_DAYS = 30


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _upsert_workflow(db: Session, connection_id: uuid.UUID, raw_workflow: dict) -> Workflow:
    n8n_workflow_id = str(raw_workflow["id"])
    workflow = (
        db.query(Workflow)
        .filter(Workflow.connection_id == connection_id, Workflow.n8n_workflow_id == n8n_workflow_id)
        .first()
    )
    if workflow is None:
        workflow = Workflow(connection_id=connection_id, n8n_workflow_id=n8n_workflow_id)
        db.add(workflow)

    workflow.name = raw_workflow["name"]
    workflow.enabled = raw_workflow.get("active", False)
    workflow.last_synced_at = now_utc()
    return workflow


def _upsert_execution(db: Session, workflow_id: uuid.UUID, raw_execution: dict) -> None:
    n8n_execution_id = str(raw_execution["id"])
    execution = (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id, Execution.n8n_execution_id == n8n_execution_id)
        .first()
    )
    if execution is None:
        execution = Execution(workflow_id=workflow_id, n8n_execution_id=n8n_execution_id)
        db.add(execution)

    execution.status = raw_execution.get("status", "unknown")
    execution.started_at = parse_n8n_datetime(raw_execution.get("startedAt"))
    execution.finished_at = parse_n8n_datetime(raw_execution.get("stoppedAt"))


def _mark_orphaned_workflows(db: Session, connection_id: uuid.UUID, seen_n8n_ids: set[str]) -> None:
    """Flags workflows no longer returned by n8n as orphaned (deleted there),
    rather than deleting our row - keeps their history and any open alerts
    intact. Only called after a full, successful workflow listing, so a
    partial sync failure never falsely orphans everything."""
    workflows = db.query(Workflow).filter(Workflow.connection_id == connection_id).all()
    for workflow in workflows:
        workflow.is_orphaned = workflow.n8n_workflow_id not in seen_n8n_ids


def sync_connection(db: Session, connection: Connection) -> SyncResult:
    """Fetches workflows + recent executions from n8n and persists them.

    Never raises on n8n-side failures (unreachable instance, bad key, etc) —
    those are recorded on the connection's last_sync_status/error fields
    instead, so this can be called from a request handler or, later, an
    unattended scheduler.
    """
    api_key = decrypt_secret(connection.api_key_encrypted)
    client = N8nClient(connection.n8n_base_url, api_key)
    execution_cutoff = now_utc() - timedelta(days=EXECUTION_HISTORY_WINDOW_DAYS)
    workflows_synced = 0
    executions_synced = 0

    try:
        raw_workflows = client.list_workflows()
        seen_n8n_ids: set[str] = set()
        for raw_workflow in raw_workflows:
            workflow = _upsert_workflow(db, connection.id, raw_workflow)
            db.flush()  # assign workflow.id before using it on its executions
            workflows_synced += 1
            seen_n8n_ids.add(workflow.n8n_workflow_id)

            raw_executions = client.list_executions(str(raw_workflow["id"]), since=execution_cutoff)
            for raw_execution in raw_executions:
                _upsert_execution(db, workflow.id, raw_execution)
                executions_synced += 1

        _mark_orphaned_workflows(db, connection.id, seen_n8n_ids)

        connection.last_sync_status = "ok"
        connection.last_sync_error = None
    except N8nUnauthorizedError:
        connection.last_sync_status = "unauthorized"
        connection.last_sync_error = "API key was rejected"
    except (N8nConnectionError, N8nApiError) as exc:
        connection.last_sync_status = "error"
        connection.last_sync_error = str(exc)
    finally:
        client.close()

    connection.last_sync_at = now_utc()
    db.commit()

    return SyncResult(
        workflows_synced=workflows_synced,
        executions_synced=executions_synced,
        last_sync_status=connection.last_sync_status,
        last_sync_error=connection.last_sync_error,
        last_sync_at=connection.last_sync_at,
    )


@dataclass
class WorkflowCounts:
    run_count_7d: int = 0
    error_count_7d: int = 0
    run_count_30d: int = 0
    error_count_30d: int = 0
    # status of the most recent execution in the 30d window (None if it never ran)
    latest_status: str | None = None


def compute_workflow_counts(db: Session, workflow_ids: list[uuid.UUID]) -> dict[uuid.UUID, WorkflowCounts]:
    """Run/error counts per workflow over the last 7 and 30 days, plus each
    workflow's most recent execution status (used to detect "failing")."""
    counts = {workflow_id: WorkflowCounts() for workflow_id in workflow_ids}
    if not workflow_ids:
        return counts

    cutoff_30d = now_utc() - timedelta(days=30)
    cutoff_7d = now_utc() - timedelta(days=7)
    latest_started_at: dict[uuid.UUID, datetime] = {}

    rows = (
        db.query(Execution.workflow_id, Execution.status, Execution.started_at)
        .filter(Execution.workflow_id.in_(workflow_ids), Execution.started_at >= cutoff_30d)
        .all()
    )

    for workflow_id, status, started_at in rows:
        is_error = status in ERROR_STATUSES
        workflow_counts = counts[workflow_id]

        workflow_counts.run_count_30d += 1
        if is_error:
            workflow_counts.error_count_30d += 1

        if started_at >= cutoff_7d:
            workflow_counts.run_count_7d += 1
            if is_error:
                workflow_counts.error_count_7d += 1

        if workflow_id not in latest_started_at or started_at > latest_started_at[workflow_id]:
            latest_started_at[workflow_id] = started_at
            workflow_counts.latest_status = status

    return counts
