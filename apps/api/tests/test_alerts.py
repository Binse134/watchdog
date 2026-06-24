from app.alerts import evaluate_workflow
from app.models import Alert


def _open_alerts(db, workflow):
    return db.query(Alert).filter(Alert.workflow_id == workflow.id, Alert.resolved_at.is_(None)).all()


def test_new_failing_status_creates_alert_and_sends_email(db, make_user, make_connection, make_workflow, monkeypatch):
    sent = []
    monkeypatch.setattr("app.alerts.send_email", lambda *a, **k: sent.append(a) and None)

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    evaluate_workflow(db, workflow, "failing")

    alerts = _open_alerts(db, workflow)
    assert len(alerts) == 1
    assert alerts[0].alert_type == "failing"
    assert alerts[0].email_sent_at is not None
    assert len(sent) == 1


def test_repeated_same_status_does_not_duplicate_alert_or_resend(
    db, make_user, make_connection, make_workflow, monkeypatch
):
    call_count = {"n": 0}

    def fake_send_email(*args, **kwargs):
        call_count["n"] += 1
        return None

    monkeypatch.setattr("app.alerts.send_email", fake_send_email)

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    evaluate_workflow(db, workflow, "failing")
    evaluate_workflow(db, workflow, "failing")

    assert len(_open_alerts(db, workflow)) == 1
    assert call_count["n"] == 1


def test_failed_email_send_is_retried_on_next_evaluation(db, make_user, make_connection, make_workflow, monkeypatch):
    responses = iter(["smtp down", None])
    monkeypatch.setattr("app.alerts.send_email", lambda *a, **k: next(responses))

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    evaluate_workflow(db, workflow, "failing")
    alert = _open_alerts(db, workflow)[0]
    assert alert.email_sent_at is None
    assert alert.email_error == "smtp down"

    evaluate_workflow(db, workflow, "failing")
    db.refresh(alert)
    assert alert.email_sent_at is not None
    assert alert.email_error is None


def test_recovery_resolves_alert_without_sending_email(db, make_user, make_connection, make_workflow, monkeypatch):
    sent = []
    monkeypatch.setattr("app.alerts.send_email", lambda *a, **k: sent.append(a) and None)

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    evaluate_workflow(db, workflow, "failing")
    assert len(sent) == 1

    evaluate_workflow(db, workflow, "healthy")

    assert len(_open_alerts(db, workflow)) == 0
    assert len(sent) == 1  # no second email on recovery


def test_status_change_resolves_old_alert_and_opens_new_one(db, make_user, make_connection, make_workflow, monkeypatch):
    monkeypatch.setattr("app.alerts.send_email", lambda *a, **k: None)

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    evaluate_workflow(db, workflow, "failing")
    failing_alert = _open_alerts(db, workflow)[0]

    evaluate_workflow(db, workflow, "silent")

    db.refresh(failing_alert)
    assert failing_alert.resolved_at is not None

    open_alerts = _open_alerts(db, workflow)
    assert len(open_alerts) == 1
    assert open_alerts[0].alert_type == "silent"
