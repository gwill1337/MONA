import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from fakeredis import FakeAsyncRedis

_tmp_dir = tempfile.mkdtemp()
_TEST_DB_PATH = os.path.join(_tmp_dir, "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"


from mona_core import db as db_module  # noqa: E402
from mona_core import main as main_module  # noqa: E402
from mona_core import security as security_module  # noqa: E402
from mona_core.routers import health as health_module # noqa: E402
from mona_core.config import celery_client # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    db_module.Base.metadata.create_all(db_module.engine)
    yield
    db_module.Base.metadata.drop_all(db_module.engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    with db_module.engine.begin() as conn:
        for table in reversed(db_module.Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


@pytest.fixture()
def db_session():
    session = db_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(main_module.app) as c:
        yield c


@pytest.fixture()
def mock_celery(monkeypatch):
    class FakeAsyncResultHandle:
        def __init__(self, task_id="fake-task-id-123"):
            self.id = task_id

    class FakeAsyncResult:
        def __init__(self, state="PENDING", result=None):
            self.state = state
            self.result = result

        def ready(self):
            return self.state in ("SUCCESS", "FAILURE")

    state = {
        "send_task_return": FakeAsyncResultHandle(),
        "async_result_return": FakeAsyncResult(state="PENDING"),
        "send_task_calls": [],
        "async_result_calls": [],
    }

    def fake_send_task(name, kwargs=None, *args, **kw):
        state["send_task_calls"].append({"name": name, "kwargs": kwargs})
        return state["send_task_return"]

    def fake_async_result(task_id):
        state["async_result_calls"].append(task_id)
        return state["async_result_return"]

    monkeypatch.setattr(celery_client, "send_task", fake_send_task)
    monkeypatch.setattr(celery_client, "AsyncResult", fake_async_result)

    return state


@pytest.fixture()
def mock_user_auth():
    from mona_core.schemas import UserSession
    from mona_core.security import get_current_user
    user_session = UserSession(
        id=1,
        username="mock_user_123",
        role="user",
    )
    main_module.app.dependency_overrides[get_current_user] = lambda: user_session
    yield user_session
    main_module.app.dependency_overrides.clear()


@pytest.fixture()
def mock_admin_auth():
    from mona_core.schemas import UserSession
    from mona_core.security import get_current_user
    admin_session = UserSession(
        id=2,
        username="mock_admin_123",
        role="admin",
    )
    main_module.app.dependency_overrides[get_current_user] = lambda: admin_session
    yield admin_session
    main_module.app.dependency_overrides.clear()

@pytest.fixture()
def make_user(db_session):
    """Factory fixture: creates a Users row directly in the DB (bypassing the API).
 
    Usage:
        def test_x(self, make_user):
            admin = make_user(username="alice", password="secret123", role="admin")
    """
    from mona_core.db import Users
 
    def _make(username="testuser", password="testpass123", role="user"):
        user = Users(username=username, role=role)
        user.set_password(password)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
 
    return _make

@pytest.fixture()
def mock_redis(monkeypatch):
    fake = FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(security_module, "redis_client", fake)
    monkeypatch.setattr(health_module, "redis_client", fake)
    return fake
