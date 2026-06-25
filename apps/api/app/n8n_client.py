from datetime import datetime

import httpx


def parse_n8n_datetime(value: str | None) -> datetime | None:
    """n8n returns ISO 8601 timestamps like '2026-06-23T15:46:04.317Z'."""
    return datetime.fromisoformat(value) if value else None


class N8nUnauthorizedError(Exception):
    """API key is missing, wrong, or revoked."""


class N8nConnectionError(Exception):
    """Instance is unreachable (DNS, timeout, refused connection, etc)."""


class N8nApiError(Exception):
    """Instance responded, but with an unexpected error status."""


class N8nClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-N8N-API-KEY": api_key, "Accept": "application/json"},
            timeout=timeout,
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            response = self._client.get(path, params=params)
        except httpx.RequestError as exc:
            raise N8nConnectionError(f"Could not reach n8n at {self.base_url}: {exc}") from exc

        if response.status_code == 401:
            raise N8nUnauthorizedError("n8n rejected the API key (401 Unauthorized)")
        if response.status_code >= 400:
            raise N8nApiError(f"n8n returned {response.status_code}: {response.text[:300]}")

        return response.json()

    def test_connection(self) -> None:
        """Raises N8nUnauthorizedError / N8nConnectionError / N8nApiError on failure."""
        self._get("/api/v1/workflows", params={"limit": 1})

    def check_health(self) -> bool:
        """Pings n8n's unauthenticated /healthz endpoint. Only used to
        clarify an error already raised by an authenticated call (see
        sync.py) - never as a precondition, since some instances don't
        expose /healthz publicly even when their REST API works fine.
        Returns False on any failure instead of raising."""
        try:
            response = self._client.get("/healthz")
        except httpx.RequestError:
            return False
        return response.status_code == 200

    def list_workflows(self) -> list[dict]:
        """Fetches all workflows, following n8n's cursor-based pagination."""
        workflows: list[dict] = []
        cursor: str | None = None

        while True:
            params = {"limit": 100}
            if cursor:
                params["cursor"] = cursor

            page = self._get("/api/v1/workflows", params=params)
            workflows.extend(page.get("data", []))

            cursor = page.get("nextCursor")
            if not cursor:
                break

        return workflows

    def get_workflow(self, workflow_id: str) -> dict:
        """Fetches one workflow's full definition, including its nodes and
        connections graph (the list endpoint already includes these too, but
        this expresses intent when only one workflow's detail is needed)."""
        return self._get(f"/api/v1/workflows/{workflow_id}")

    def list_executions(self, workflow_id: str, since: datetime | None = None, page_size: int = 250) -> list[dict]:
        """Fetches executions for a workflow, newest first, following pagination.

        If `since` is given, stops paging once a page's oldest execution is
        older than it, instead of walking the workflow's entire history.
        """
        executions: list[dict] = []
        cursor: str | None = None

        while True:
            params = {"workflowId": workflow_id, "limit": page_size, "includeData": "false"}
            if cursor:
                params["cursor"] = cursor

            page = self._get("/api/v1/executions", params=params)
            batch = page.get("data", [])
            executions.extend(batch)

            cursor = page.get("nextCursor")
            if not cursor or not batch:
                break

            oldest_started_at = parse_n8n_datetime(batch[-1].get("startedAt"))
            if since and oldest_started_at and oldest_started_at < since:
                break

        return executions

    def close(self) -> None:
        self._client.close()
