from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.database import get_db as real_get_db
from app.main import app
from app.models import Connection, Execution, User, Workflow
from app.security import encrypt_secret, hash_password

TEST_DB_NAME = "watchdog_test"


def _url_with_db(db_name: str) -> str:
    parts = urlsplit(settings.database_url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{db_name}", "", ""))


@pytest.fixture(scope="session")
def test_engine():
    """Creates a throwaway watchdog_test database on the same Postgres
    instance the app uses (host port 5433) and builds the schema straight
    from the current models - no Alembic involved, since this is just a
    scratch DB recreated fresh on every test run."""
    admin_engine = create_engine(_url_with_db("postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    engine = create_engine(_url_with_db(TEST_DB_NAME))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(test_engine):
    """One test = one transaction, rolled back at the end - isolates tests
    from each other without recreating the schema every time."""
    connection = test_engine.connect()
    trans = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db, monkeypatch):
    """A TestClient wired to the test DB session above (so route handlers
    and the test see the same uncommitted rows) with the real background
    scheduler disabled - tests should never kick off real n8n/Ollama/Resend
    calls via APScheduler."""
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr("app.main.stop_scheduler", lambda: None)

    def _override_get_db():
        yield db

    from fastapi.testclient import TestClient

    app.dependency_overrides[real_get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(real_get_db, None)


@pytest.fixture()
def make_user(db):
    def _make(email: str = "user@example.com", password: str = "testpass123") -> User:
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        db.flush()
        return user

    return _make


@pytest.fixture()
def make_connection(db):
    def _make(user: User, n8n_base_url: str = "http://localhost:5678", api_key: str = "test-key") -> Connection:
        connection = Connection(
            user_id=user.id,
            n8n_base_url=n8n_base_url,
            api_key_encrypted=encrypt_secret(api_key),
            last_sync_status="ok",
        )
        db.add(connection)
        db.flush()
        return connection

    return _make


@pytest.fixture()
def make_workflow(db):
    def _make(
        connection: Connection,
        n8n_workflow_id: str = "1",
        name: str = "Test Workflow",
        enabled: bool = True,
    ) -> Workflow:
        workflow = Workflow(
            connection_id=connection.id,
            n8n_workflow_id=n8n_workflow_id,
            name=name,
            enabled=enabled,
        )
        db.add(workflow)
        db.flush()
        return workflow

    return _make


@pytest.fixture()
def make_execution(db):
    def _make(workflow: Workflow, n8n_execution_id: str, status: str, started_at) -> Execution:
        execution = Execution(
            workflow_id=workflow.id,
            n8n_execution_id=n8n_execution_id,
            status=status,
            started_at=started_at,
            finished_at=started_at,
        )
        db.add(execution)
        db.flush()
        return execution

    return _make
