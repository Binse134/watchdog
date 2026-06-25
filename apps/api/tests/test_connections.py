from datetime import datetime, timedelta, timezone

from app.n8n_client import N8nConnectionError, N8nUnauthorizedError


def now():
    return datetime.now(timezone.utc)


def _signup(client, email="owner@example.com", password="testpass123"):
    response = client.post("/auth/signup", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


class OkClient:
    def __init__(self, *args, **kwargs):
        pass

    def test_connection(self):
        return None

    def close(self):
        pass


def _patch_create_client(monkeypatch, client_cls):
    monkeypatch.setattr("app.connections.N8nClient", client_cls)


def test_create_connection_success(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)

    response = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"})
    assert response.status_code == 201
    body = response.json()
    assert body["n8n_base_url"] == "http://localhost:5678"
    assert body["last_sync_status"] == "ok"


def test_create_connection_unauthorized_key_rejected(client, monkeypatch):
    _signup(client)

    class UnauthorizedClient(OkClient):
        def test_connection(self):
            raise N8nUnauthorizedError("nope")

    _patch_create_client(monkeypatch, UnauthorizedClient)

    response = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "bad"})
    assert response.status_code == 400


def test_create_connection_unreachable_url_rejected(client, monkeypatch):
    _signup(client)

    class UnreachableClient(OkClient):
        def test_connection(self):
            raise N8nConnectionError("nope")

    _patch_create_client(monkeypatch, UnreachableClient)

    response = client.post("/connections", json={"n8n_base_url": "http://unreachable", "api_key": "key"})
    assert response.status_code == 400


def test_list_and_get_and_delete_connection(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)

    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()
    connection_id = created["id"]

    listed = client.get("/connections")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = client.get(f"/connections/{connection_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == connection_id

    deleted = client.delete(f"/connections/{connection_id}")
    assert deleted.status_code == 204

    assert client.get(f"/connections/{connection_id}").status_code == 404


def test_connection_ownership_is_isolated_between_users(client, monkeypatch):
    _patch_create_client(monkeypatch, OkClient)
    _signup(client, email="userA@example.com")
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()
    connection_id = created["id"]
    client.post("/auth/logout")

    _signup(client, email="userB@example.com")
    other_user_view = client.get(f"/connections/{connection_id}")
    assert other_user_view.status_code == 404

    other_user_list = client.get("/connections")
    assert other_user_list.json() == []


def test_update_connection_requires_at_least_one_field(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    response = client.patch(f"/connections/{created['id']}", json={})
    assert response.status_code == 400


def test_update_connection_failure_leaves_existing_value_unchanged(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class UnreachableClient(OkClient):
        def test_connection(self):
            raise N8nConnectionError("nope")

    _patch_create_client(monkeypatch, UnreachableClient)
    response = client.patch(f"/connections/{created['id']}", json={"n8n_base_url": "http://unreachable"})
    assert response.status_code == 400

    fetched = client.get(f"/connections/{created['id']}").json()
    assert fetched["n8n_base_url"] == "http://localhost:5678"


def test_update_connection_success_updates_base_url(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    response = client.patch(f"/connections/{created['id']}", json={"n8n_base_url": "http://localhost:9999"})
    assert response.status_code == 200
    assert response.json()["n8n_base_url"] == "http://localhost:9999"


def test_sync_endpoint_persists_workflows(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class FakeSyncClient(OkClient):
        def list_workflows(self):
            return [{"id": "1", "name": "Synced Workflow", "active": True}]

        def list_executions(self, workflow_id, since=None):
            return []

    monkeypatch.setattr("app.sync.N8nClient", FakeSyncClient)

    response = client.post(f"/connections/{created['id']}/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["workflows_synced"] == 1
    assert body["last_sync_status"] == "ok"

    workflows = client.get(f"/connections/{created['id']}/workflows").json()
    assert len(workflows) == 1
    assert workflows[0]["name"] == "Synced Workflow"
    assert workflows[0]["health_status"] == "unused"  # enabled, but zero executions


def test_list_workflows_reports_health_and_counts(client, monkeypatch, make_execution):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class FakeSyncClient(OkClient):
        def list_workflows(self):
            return [{"id": "1", "name": "Failing Workflow", "active": True}]

        def list_executions(self, workflow_id, since=None):
            return [
                {"id": "e1", "status": "success", "startedAt": "2026-06-01T00:00:00.000Z"},
                {"id": "e2", "status": "error", "startedAt": (now() - timedelta(hours=1)).isoformat()},
            ]

    monkeypatch.setattr("app.sync.N8nClient", FakeSyncClient)
    client.post(f"/connections/{created['id']}/sync")

    workflows = client.get(f"/connections/{created['id']}/workflows").json()
    assert len(workflows) == 1
    wf = workflows[0]
    assert wf["health_status"] == "failing"
    assert wf["run_count_7d"] == 1
    assert wf["run_count_30d"] == 2

    detail = client.get(f"/connections/{created['id']}/workflows/{wf['id']}").json()
    assert detail["health_status"] == "failing"


def test_alerts_endpoint_filters_by_resolved(client, monkeypatch, db):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class FakeSyncClient(OkClient):
        def list_workflows(self):
            return [{"id": "1", "name": "Wf", "active": True}]

        def list_executions(self, workflow_id, since=None):
            return []

    monkeypatch.setattr("app.sync.N8nClient", FakeSyncClient)
    client.post(f"/connections/{created['id']}/sync")
    workflow_id = client.get(f"/connections/{created['id']}/workflows").json()[0]["id"]

    from app.alerts import evaluate_workflow
    from app.models import Workflow
    import uuid

    workflow = db.get(Workflow, uuid.UUID(workflow_id))
    monkeypatch.setattr("app.alerts.send_email", lambda *a, **k: None)
    evaluate_workflow(db, workflow, "failing")

    open_alerts = client.get(f"/connections/{created['id']}/alerts", params={"resolved": "false"}).json()
    assert len(open_alerts) == 1
    assert open_alerts[0]["alert_type"] == "failing"
    assert open_alerts[0]["workflow_name"] == "Wf"

    resolved_alerts = client.get(f"/connections/{created['id']}/alerts", params={"resolved": "true"}).json()
    assert resolved_alerts == []

    evaluate_workflow(db, workflow, "healthy")
    resolved_alerts = client.get(f"/connections/{created['id']}/alerts", params={"resolved": "true"}).json()
    assert len(resolved_alerts) == 1


def test_resolve_alert_endpoint_marks_resolved_manually(client, monkeypatch, db):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class FakeSyncClient(OkClient):
        def list_workflows(self):
            return [{"id": "1", "name": "Wf", "active": True}]

        def list_executions(self, workflow_id, since=None):
            return []

    monkeypatch.setattr("app.sync.N8nClient", FakeSyncClient)
    client.post(f"/connections/{created['id']}/sync")
    workflow_id = client.get(f"/connections/{created['id']}/workflows").json()[0]["id"]

    from app.alerts import evaluate_workflow
    from app.models import Workflow
    import uuid

    workflow = db.get(Workflow, uuid.UUID(workflow_id))
    monkeypatch.setattr("app.alerts.send_email", lambda *a, **k: None)
    evaluate_workflow(db, workflow, "failing")

    alert_id = client.get(f"/connections/{created['id']}/alerts", params={"resolved": "false"}).json()[0]["id"]

    response = client.post(f"/connections/{created['id']}/alerts/{alert_id}/resolve")
    assert response.status_code == 200
    assert response.json()["resolved_at"] is not None

    open_alerts = client.get(f"/connections/{created['id']}/alerts", params={"resolved": "false"}).json()
    assert open_alerts == []


def test_resolve_alert_endpoint_404_for_alert_on_other_users_connection(client, monkeypatch, db):
    _signup(client, email="owner@example.com")
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class FakeSyncClient(OkClient):
        def list_workflows(self):
            return [{"id": "1", "name": "Wf", "active": True}]

        def list_executions(self, workflow_id, since=None):
            return []

    monkeypatch.setattr("app.sync.N8nClient", FakeSyncClient)
    client.post(f"/connections/{created['id']}/sync")
    workflow_id = client.get(f"/connections/{created['id']}/workflows").json()[0]["id"]

    from app.alerts import evaluate_workflow
    from app.models import Workflow
    import uuid

    workflow = db.get(Workflow, uuid.UUID(workflow_id))
    monkeypatch.setattr("app.alerts.send_email", lambda *a, **k: None)
    evaluate_workflow(db, workflow, "failing")
    alert_id = client.get(f"/connections/{created['id']}/alerts", params={"resolved": "false"}).json()[0]["id"]

    client.post("/auth/logout")
    _signup(client, email="intruder@example.com")

    response = client.post(f"/connections/{created['id']}/alerts/{alert_id}/resolve")
    assert response.status_code == 404


def test_summary_endpoint_generates_and_caches(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class FakeSyncClient(OkClient):
        def list_workflows(self):
            return [{"id": "1", "name": "Wf", "active": True}]

        def list_executions(self, workflow_id, since=None):
            return []

    monkeypatch.setattr("app.sync.N8nClient", FakeSyncClient)
    client.post(f"/connections/{created['id']}/sync")
    workflow_id = client.get(f"/connections/{created['id']}/workflows").json()[0]["id"]

    raw_workflow = {"name": "Wf", "nodes": [{"name": "A", "type": "n8n-nodes-base.noOp", "parameters": {}}], "connections": {}}

    class SummaryClient(OkClient):
        def get_workflow(self, workflow_id):
            return raw_workflow

    monkeypatch.setattr("app.connections.N8nClient", SummaryClient)

    calls = []
    monkeypatch.setattr("app.summaries.generate_text", lambda prompt: calls.append(prompt) or "plain summary")

    response = client.post(f"/connections/{created['id']}/workflows/{workflow_id}/summary")
    assert response.status_code == 200
    assert response.json()["summary"] == "plain summary"
    assert len(calls) == 2

    # second call with the same definition should hit the cache - no new LLM calls
    response2 = client.post(f"/connections/{created['id']}/workflows/{workflow_id}/summary")
    assert response2.status_code == 200
    assert len(calls) == 2

    response3 = client.post(f"/connections/{created['id']}/workflows/{workflow_id}/summary?force=true")
    assert response3.status_code == 200
    assert len(calls) == 4


def test_summary_endpoint_returns_502_on_llm_error(client, monkeypatch):
    _signup(client)
    _patch_create_client(monkeypatch, OkClient)
    created = client.post("/connections", json={"n8n_base_url": "http://localhost:5678", "api_key": "key"}).json()

    class FakeSyncClient(OkClient):
        def list_workflows(self):
            return [{"id": "1", "name": "Wf", "active": True}]

        def list_executions(self, workflow_id, since=None):
            return []

    monkeypatch.setattr("app.sync.N8nClient", FakeSyncClient)
    client.post(f"/connections/{created['id']}/sync")
    workflow_id = client.get(f"/connections/{created['id']}/workflows").json()[0]["id"]

    class SummaryClient(OkClient):
        def get_workflow(self, workflow_id):
            return {"name": "Wf", "nodes": [], "connections": {}}

    monkeypatch.setattr("app.connections.N8nClient", SummaryClient)

    from app.llm import LlmError

    def raise_llm_error(prompt):
        raise LlmError("ollama is down")

    monkeypatch.setattr("app.summaries.generate_text", raise_llm_error)

    response = client.post(f"/connections/{created['id']}/workflows/{workflow_id}/summary")
    assert response.status_code == 502
