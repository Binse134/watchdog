from datetime import datetime, timedelta, timezone

import pytest

from app.n8n_client import N8nApiError, N8nConnectionError, N8nUnauthorizedError
from app.sync import compute_workflow_counts, sync_connection


def now():
    return datetime.now(timezone.utc)


def test_compute_workflow_counts_splits_7d_and_30d_windows(db, make_user, make_connection, make_workflow, make_execution):
    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    make_execution(workflow, "old", "success", now() - timedelta(days=20))
    make_execution(workflow, "recent-ok", "success", now() - timedelta(days=2))
    make_execution(workflow, "recent-err", "error", now() - timedelta(hours=1))
    make_execution(workflow, "too-old", "success", now() - timedelta(days=40))

    counts = compute_workflow_counts(db, [workflow.id])[workflow.id]

    assert counts.run_count_30d == 3
    assert counts.error_count_30d == 1
    assert counts.run_count_7d == 2
    assert counts.error_count_7d == 1
    # most recent execution overall is "recent-err"
    assert counts.latest_status == "error"


def test_compute_workflow_counts_handles_workflow_with_no_executions(db, make_user, make_connection, make_workflow):
    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    counts = compute_workflow_counts(db, [workflow.id])[workflow.id]

    assert counts.run_count_7d == 0
    assert counts.run_count_30d == 0
    assert counts.latest_status is None


class FakeN8nClient:
    """Stands in for app.sync.N8nClient so sync_connection can be tested
    without a real n8n instance."""

    def __init__(self, *args, **kwargs):
        pass

    def list_workflows(self):
        return self._workflows

    def list_executions(self, workflow_id, since=None):
        return self._executions_by_workflow.get(workflow_id, [])

    def check_health(self):
        return True

    def close(self):
        pass


def _patch_client(monkeypatch, workflows, executions_by_workflow=None):
    FakeN8nClient._workflows = workflows
    FakeN8nClient._executions_by_workflow = executions_by_workflow or {}
    monkeypatch.setattr("app.sync.N8nClient", FakeN8nClient)


def test_sync_connection_upserts_workflows_and_executions(db, make_user, make_connection, monkeypatch):
    user = make_user()
    connection = make_connection(user)

    _patch_client(
        monkeypatch,
        workflows=[{"id": "1", "name": "Wf One", "active": True}],
        executions_by_workflow={
            "1": [{"id": "e1", "status": "success", "startedAt": "2026-06-20T00:00:00.000Z"}]
        },
    )

    result = sync_connection(db, connection)

    assert result.workflows_synced == 1
    assert result.executions_synced == 1
    assert result.last_sync_status == "ok"
    assert connection.last_sync_status == "ok"


def test_sync_connection_running_twice_upserts_not_duplicates(db, make_user, make_connection, monkeypatch):
    from app.models import Execution, Workflow

    user = make_user()
    connection = make_connection(user)
    _patch_client(
        monkeypatch,
        workflows=[{"id": "1", "name": "Wf One", "active": True}],
        executions_by_workflow={
            "1": [{"id": "e1", "status": "success", "startedAt": "2026-06-20T00:00:00.000Z"}]
        },
    )

    sync_connection(db, connection)
    sync_connection(db, connection)

    assert db.query(Workflow).filter(Workflow.connection_id == connection.id).count() == 1
    assert db.query(Execution).count() == 1


def test_sync_connection_deletes_workflow_no_longer_in_n8n(db, make_user, make_connection, monkeypatch):
    from app.models import Execution, Workflow

    user = make_user()
    connection = make_connection(user)

    _patch_client(
        monkeypatch,
        workflows=[{"id": "1", "name": "Wf One", "active": True}],
        executions_by_workflow={
            "1": [{"id": "e1", "status": "success", "startedAt": "2026-06-20T00:00:00.000Z"}]
        },
    )
    sync_connection(db, connection)

    _patch_client(monkeypatch, workflows=[])  # workflow "1" no longer returned
    sync_connection(db, connection)

    assert db.query(Workflow).filter(Workflow.connection_id == connection.id).count() == 0
    assert db.query(Execution).count() == 0  # cascaded with the deleted workflow


def test_sync_connection_records_unauthorized_without_raising(db, make_user, make_connection, monkeypatch):
    class UnauthorizedClient(FakeN8nClient):
        def list_workflows(self):
            raise N8nUnauthorizedError("nope")

    monkeypatch.setattr("app.sync.N8nClient", UnauthorizedClient)
    user = make_user()
    connection = make_connection(user)

    result = sync_connection(db, connection)

    assert result.last_sync_status == "unauthorized"
    assert result.workflows_synced == 0


def test_sync_connection_records_unreachable_when_healthz_also_fails(db, make_user, make_connection, monkeypatch):
    class UnreachableClient(FakeN8nClient):
        def list_workflows(self):
            raise N8nConnectionError("could not reach it")

        def check_health(self):
            return False

    monkeypatch.setattr("app.sync.N8nClient", UnreachableClient)
    user = make_user()
    connection = make_connection(user)

    result = sync_connection(db, connection)

    assert result.last_sync_status == "unreachable"
    assert "could not reach it" in result.last_sync_error


def test_sync_connection_records_error_when_healthz_succeeds(db, make_user, make_connection, monkeypatch):
    """An API-level failure (eg. Public API disabled) where the instance
    itself is still up, per /healthz, is a narrower problem than a full
    outage - kept as "error" rather than "unreachable"."""

    class ApiFailingClient(FakeN8nClient):
        def list_workflows(self):
            raise N8nApiError("n8n returned 404: not found")

        def check_health(self):
            return True

    monkeypatch.setattr("app.sync.N8nClient", ApiFailingClient)
    user = make_user()
    connection = make_connection(user)

    result = sync_connection(db, connection)

    assert result.last_sync_status == "error"
    assert "404" in result.last_sync_error
