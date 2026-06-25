import threading
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.alerts import evaluate_workflow
from app.database import get_db
from app.deps import get_current_user
from app.health import compute_health_status
from app.llm import LlmError
from app.models import Alert, Connection, User, Workflow, WorkflowSummary
from app.n8n_client import N8nApiError, N8nClient, N8nConnectionError, N8nUnauthorizedError
from app.schemas import (
    AlertOut,
    ConnectionCreate,
    ConnectionOut,
    ConnectionUpdate,
    SyncResult,
    WorkflowOut,
    WorkflowSummaryOut,
)
from app.security import decrypt_secret, encrypt_secret
from app.summaries import generate_workflow_summary
from app.sync import WorkflowCounts, compute_workflow_counts, sync_connection

router = APIRouter(prefix="/connections", tags=["connections"])

# Generating a summary makes two sequential LLM calls that can take up to a
# couple of minutes - long enough that a user navigates away and back,
# sees the button reset to "Generate summary" (component state doesn't
# survive unmount), and clicks it again while the first call is still
# running server-side. Guards against that by tracking in-progress
# generations in memory - fine for this single-process dev server.
_summary_locks_guard = threading.Lock()
_summaries_in_progress: set[uuid.UUID] = set()


def _get_owned_connection(db: Session, user: User, connection_id: uuid.UUID) -> Connection:
    connection = db.get(Connection, connection_id)
    if not connection or connection.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    return connection


def _get_owned_workflow(db: Session, connection: Connection, workflow_id: uuid.UUID) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if not workflow or workflow.connection_id != connection.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    return workflow


@router.get("", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Connection).filter(Connection.user_id == user.id).all()


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connection(
    body: ConnectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify the credentials work before saving them.
    client = N8nClient(body.n8n_base_url, body.api_key)
    try:
        client.test_connection()
    except N8nUnauthorizedError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "n8n rejected this API key")
    except N8nConnectionError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not reach that n8n instance")
    except N8nApiError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    finally:
        client.close()

    connection = Connection(
        user_id=user.id,
        n8n_base_url=body.n8n_base_url,
        api_key_encrypted=encrypt_secret(body.api_key),
        last_sync_status="ok",
        last_sync_at=datetime.now(timezone.utc),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.get("/{connection_id}", response_model=ConnectionOut)
def get_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _get_owned_connection(db, user, connection_id)


@router.patch("/{connection_id}", response_model=ConnectionOut)
def update_connection(
    connection_id: uuid.UUID,
    body: ConnectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Updates the n8n base URL and/or API key on an existing connection.

    Unlike delete+recreate, this keeps all synced workflows/executions/alerts
    intact - meant for rotating an API key or repointing at a moved instance,
    not for switching to a genuinely different n8n. Re-tests credentials
    live before saving, same as create_connection.
    """
    connection = _get_owned_connection(db, user, connection_id)

    if body.n8n_base_url is None and body.api_key is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide n8n_base_url and/or api_key to update")

    new_base_url = body.n8n_base_url or connection.n8n_base_url
    new_api_key = body.api_key or decrypt_secret(connection.api_key_encrypted)

    client = N8nClient(new_base_url, new_api_key)
    try:
        client.test_connection()
    except N8nUnauthorizedError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "n8n rejected this API key")
    except N8nConnectionError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not reach that n8n instance")
    except N8nApiError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    finally:
        client.close()

    connection.n8n_base_url = new_base_url
    connection.api_key_encrypted = encrypt_secret(new_api_key)
    connection.last_sync_status = "ok"
    connection.last_sync_error = None
    connection.last_sync_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(connection)
    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    connection = _get_owned_connection(db, user, connection_id)
    db.delete(connection)
    db.commit()


@router.post("/{connection_id}/sync", response_model=SyncResult)
def sync_workflows(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetches workflows + recent executions from n8n and persists them, then
    immediately re-evaluates health/alerts for this connection's workflows
    so a manual sync gives the same alerting outcome as waiting for the
    next scheduled check cycle, instead of leaving alerts to lag behind by
    up to sync_interval_minutes.

    Always returns 200 — the sync's own outcome (ok/unauthorized/error) is
    reported in the body via last_sync_status, since a failed sync is a
    normal, expected result to display, not a broken request.
    """
    connection = _get_owned_connection(db, user, connection_id)
    result = sync_connection(db, connection)

    if result.last_sync_status == "ok":
        workflows = db.query(Workflow).filter(Workflow.connection_id == connection.id).all()
        counts = compute_workflow_counts(db, [wf.id for wf in workflows])
        for workflow in workflows:
            status_ = compute_health_status(workflow, counts[workflow.id])
            evaluate_workflow(db, workflow, status_)

    return result


def _build_workflow_out(workflow: Workflow, counts: WorkflowCounts, summary: WorkflowSummary | None) -> WorkflowOut:
    return WorkflowOut(
        id=workflow.id,
        n8n_workflow_id=workflow.n8n_workflow_id,
        name=workflow.name,
        enabled=workflow.enabled,
        last_synced_at=workflow.last_synced_at,
        health_status=compute_health_status(workflow, counts),
        run_count_7d=counts.run_count_7d,
        error_count_7d=counts.error_count_7d,
        run_count_30d=counts.run_count_30d,
        error_count_30d=counts.error_count_30d,
        summary=summary.summary if summary else None,
        summary_generated_at=summary.generated_at if summary else None,
    )


@router.get("/{connection_id}/workflows", response_model=list[WorkflowOut])
def list_workflows(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reads previously-synced workflows from the DB. Call POST .../sync first
    (or again) to refresh them from n8n."""
    connection = _get_owned_connection(db, user, connection_id)
    workflows = db.query(Workflow).filter(Workflow.connection_id == connection.id).all()
    counts = compute_workflow_counts(db, [wf.id for wf in workflows])
    summaries = (
        db.query(WorkflowSummary).filter(WorkflowSummary.workflow_id.in_([wf.id for wf in workflows])).all()
    )
    summary_by_workflow_id = {s.workflow_id: s for s in summaries}

    return [
        _build_workflow_out(wf, counts[wf.id], summary_by_workflow_id.get(wf.id))
        for wf in workflows
    ]


@router.get("/{connection_id}/workflows/{workflow_id}", response_model=WorkflowOut)
def get_workflow(
    connection_id: uuid.UUID,
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Single-workflow detail - same fields as the list endpoint, for a
    workflow detail page that shouldn't have to fetch+filter the whole list."""
    connection = _get_owned_connection(db, user, connection_id)
    workflow = _get_owned_workflow(db, connection, workflow_id)
    counts = compute_workflow_counts(db, [workflow.id])
    summary = db.query(WorkflowSummary).filter(WorkflowSummary.workflow_id == workflow.id).one_or_none()
    return _build_workflow_out(workflow, counts[workflow.id], summary)


@router.get("/{connection_id}/alerts", response_model=list[AlertOut])
def list_alerts(
    connection_id: uuid.UUID,
    resolved: bool | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Alert history across every workflow under this connection, most recent
    first. Pass ?resolved=false for only open alerts (a "needs attention"
    view), ?resolved=true for closed ones, or omit it for both."""
    connection = _get_owned_connection(db, user, connection_id)
    query = (
        db.query(Alert)
        .join(Workflow)
        .filter(Workflow.connection_id == connection.id)
        .options(joinedload(Alert.workflow))
    )
    if resolved is True:
        query = query.filter(Alert.resolved_at.isnot(None))
    elif resolved is False:
        query = query.filter(Alert.resolved_at.is_(None))
    alerts = query.order_by(Alert.triggered_at.desc()).limit(limit).all()

    return [
        AlertOut(
            id=alert.id,
            workflow_id=alert.workflow_id,
            workflow_name=alert.workflow.name,
            alert_type=alert.alert_type,
            triggered_at=alert.triggered_at,
            resolved_at=alert.resolved_at,
            email_sent_at=alert.email_sent_at,
            email_error=alert.email_error,
        )
        for alert in alerts
    ]


@router.post("/{connection_id}/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(
    connection_id: uuid.UUID,
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually marks an open alert as resolved, for when the user already
    fixed the workflow in n8n and doesn't want to wait for the next sync's
    automatic re-evaluation to clear it. If the workflow is still actually
    failing, the next check cycle just reopens a new alert - this never
    touches health_status itself, which stays computed live from real
    execution data (see app/health.py)."""
    connection = _get_owned_connection(db, user, connection_id)
    alert = (
        db.query(Alert)
        .join(Workflow)
        .filter(Alert.id == alert_id, Workflow.connection_id == connection.id)
        .one_or_none()
    )
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")

    if alert.resolved_at is None:
        alert.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)

    return AlertOut(
        id=alert.id,
        workflow_id=alert.workflow_id,
        workflow_name=alert.workflow.name,
        alert_type=alert.alert_type,
        triggered_at=alert.triggered_at,
        resolved_at=alert.resolved_at,
        email_sent_at=alert.email_sent_at,
        email_error=alert.email_error,
    )


@router.post("/{connection_id}/workflows/{workflow_id}/summary", response_model=WorkflowSummaryOut)
def regenerate_workflow_summary(
    connection_id: uuid.UUID,
    workflow_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generates (or refreshes) a workflow's plain-English summary.

    Fetches the workflow's current definition from n8n live, hashes it, and
    skips the LLM call entirely if that hash matches the cached summary's -
    pass ?force=true to regenerate even when nothing changed.
    """
    connection = _get_owned_connection(db, user, connection_id)
    workflow = _get_owned_workflow(db, connection, workflow_id)

    with _summary_locks_guard:
        if workflow.id in _summaries_in_progress:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Already generating a summary for this workflow - wait for it to finish",
            )
        _summaries_in_progress.add(workflow.id)

    try:
        api_key = decrypt_secret(connection.api_key_encrypted)
        client = N8nClient(connection.n8n_base_url, api_key)
        try:
            raw_workflow = client.get_workflow(workflow.n8n_workflow_id)
        except N8nUnauthorizedError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "n8n rejected this API key")
        except N8nConnectionError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not reach that n8n instance")
        except N8nApiError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
        finally:
            client.close()

        try:
            return generate_workflow_summary(db, workflow, raw_workflow, force=force)
        except LlmError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    finally:
        with _summary_locks_guard:
            _summaries_in_progress.discard(workflow.id)
