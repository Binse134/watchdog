import httpx
import pytest

from app.n8n_client import (
    N8nApiError,
    N8nClient,
    N8nConnectionError,
    N8nUnauthorizedError,
    parse_n8n_datetime,
)


def _client_with_handler(handler) -> N8nClient:
    client = N8nClient("http://fake-n8n", "test-key")
    client._client = httpx.Client(
        base_url=client.base_url,
        headers={"X-N8N-API-KEY": "test-key", "Accept": "application/json"},
        transport=httpx.MockTransport(handler),
    )
    return client


def test_parse_n8n_datetime_handles_z_suffix_and_none():
    parsed = parse_n8n_datetime("2026-06-23T15:46:04.317Z")
    assert parsed is not None
    assert parsed.year == 2026
    assert parse_n8n_datetime(None) is None


def test_test_connection_raises_unauthorized_on_401():
    def handler(request):
        return httpx.Response(401, json={"message": "unauthorized"})

    client = _client_with_handler(handler)
    with pytest.raises(N8nUnauthorizedError):
        client.test_connection()


def test_test_connection_raises_api_error_on_500():
    def handler(request):
        return httpx.Response(500, text="internal error")

    client = _client_with_handler(handler)
    with pytest.raises(N8nApiError):
        client.test_connection()


def test_test_connection_succeeds_on_200():
    def handler(request):
        return httpx.Response(200, json={"data": [], "nextCursor": None})

    client = _client_with_handler(handler)
    client.test_connection()  # should not raise


def test_get_raises_connection_error_on_request_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    client = _client_with_handler(handler)
    with pytest.raises(N8nConnectionError):
        client.test_connection()


def test_list_workflows_follows_pagination():
    pages = [
        httpx.Response(200, json={"data": [{"id": "1"}], "nextCursor": "page2"}),
        httpx.Response(200, json={"data": [{"id": "2"}], "nextCursor": None}),
    ]
    calls = {"n": 0}

    def handler(request):
        response = pages[calls["n"]]
        calls["n"] += 1
        return response

    client = _client_with_handler(handler)
    workflows = client.list_workflows()

    assert [w["id"] for w in workflows] == ["1", "2"]
    assert calls["n"] == 2


def test_check_health_returns_true_on_200():
    def handler(request):
        assert request.url.path == "/healthz"
        return httpx.Response(200, json={"status": "ok"})

    client = _client_with_handler(handler)
    assert client.check_health() is True


def test_check_health_returns_false_on_non_200():
    def handler(request):
        return httpx.Response(503, json={"status": "error"})

    client = _client_with_handler(handler)
    assert client.check_health() is False


def test_check_health_returns_false_on_request_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    client = _client_with_handler(handler)
    assert client.check_health() is False


def test_list_executions_stops_paging_once_older_than_since():
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=7)
    recent = datetime.now(timezone.utc).isoformat()
    old = (since - timedelta(days=10)).isoformat()

    pages = [
        httpx.Response(
            200,
            json={"data": [{"id": "1", "startedAt": recent}], "nextCursor": "page2"},
        ),
        httpx.Response(
            200,
            json={"data": [{"id": "2", "startedAt": old}], "nextCursor": "page3"},
        ),
    ]
    calls = {"n": 0}

    def handler(request):
        response = pages[calls["n"]]
        calls["n"] += 1
        return response

    client = _client_with_handler(handler)
    executions = client.list_executions("1", since=since)

    # stops after the page containing an execution older than `since`
    assert calls["n"] == 2
    assert [e["id"] for e in executions] == ["1", "2"]
