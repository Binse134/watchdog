from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.email import send_email
from app.health import ALERTABLE_STATUSES
from app.models import Alert, Workflow

ALERT_MESSAGES = {
    "failing": "is failing - its most recent run ended in an error.",
    "silent": "has gone silent - it ran within the last 30 days but nothing in the last 7.",
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_workflow(db: Session, workflow: Workflow, status: str) -> None:
    """Compares a freshly-computed health status against any open alert for
    this workflow and creates/resolves/retries as needed.

    Dedupe mechanism: at most one unresolved (resolved_at IS NULL) Alert row
    per workflow at a time. A new email only goes out when that row doesn't
    exist yet (first time this incident is seen) or when the previous send
    attempt failed (retry). Recovery clears the row without emailing - V1
    only alerts when something breaks, not when it recovers.
    """
    open_alert = (
        db.query(Alert)
        .filter(Alert.workflow_id == workflow.id, Alert.resolved_at.is_(None))
        .one_or_none()
    )

    if status not in ALERTABLE_STATUSES:
        if open_alert:
            open_alert.resolved_at = now_utc()
            db.commit()
        return

    if open_alert and open_alert.alert_type == status:
        if open_alert.email_sent_at is None:
            _send_alert_email(db, open_alert, workflow, status)
        return

    if open_alert:
        open_alert.resolved_at = now_utc()

    new_alert = Alert(workflow_id=workflow.id, alert_type=status)
    db.add(new_alert)
    db.flush()
    _send_alert_email(db, new_alert, workflow, status)


def _send_alert_email(db: Session, alert: Alert, workflow: Workflow, status: str) -> None:
    user_email = workflow.connection.user.email
    subject = f'Watchdog alert: "{workflow.name}" {status}'
    html = f"<p>Your n8n workflow <strong>{workflow.name}</strong> {ALERT_MESSAGES[status]}</p>"

    error = send_email(user_email, subject, html)
    if error:
        alert.email_error = error
    else:
        alert.email_sent_at = now_utc()
        alert.email_error = None
    db.commit()
