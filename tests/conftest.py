import math
import os
import tempfile

import numpy as np
import pytest
from fastapi.testclient import TestClient
from fakeredis import FakeAsyncRedis
from datetime import UTC, datetime
from sqlalchemy import event

_tmp_dir = tempfile.mkdtemp()
_TEST_DB_PATH = os.path.join(_tmp_dir, "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"


from mona_core import db as db_module  # noqa: E402
from mona_core import main as main_module  # noqa: E402
from mona_core import security as security_module  # noqa: E402
from mona_core import tasks as tasks_module  # noqa: E402
from mona_core.routers import health as health_module # noqa: E402
from mona_core.config import celery_client # noqa: E402

@event.listens_for(db_module.engine, "connect")
def _sqlite_pg_compat(dbapi_conn, _record):
    def to_timestamp(epoch):
        if epoch is None:
            return None
        return datetime.fromtimestamp(float(epoch), UTC).isoformat(sep=" ")

    dbapi_conn.create_function("to_timestamp", 1, to_timestamp, deterministic=True)
    dbapi_conn.create_function(
        "floor", 1, lambda x: None if x is None else math.floor(x), deterministic=True
    )

db_module.engine.dispose()

@event.listens_for(db_module.Metric, "load")
def _metric_load(target, context):
    if target.timestamp and target.timestamp.tzinfo is None:
        target.timestamp = target.timestamp.replace(tzinfo=UTC)

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

# ─── Prometheus mocks (used by tasks._query_prometheus / tasks.collect_and_save) ──
class FakeResponse:
    """Mimics an httpx2 Response: returns a fixed JSON payload."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _vector_payload(values):
    """Build a Prometheus instant-vector response from {job: value}."""
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {"metric": {"job": job}, "value": [1700000000, str(value)]}
                for job, value in values.items()
            ],
        },
    }


class FakeClient:
    """Mimics httpx2.Client used as a context manager.

    collect_and_save() now issues exactly two grouped queries (CPU, then RAM),
    and each answer carries one series per job. The fake picks the answer by
    looking at the query text, so call order does not matter.

    cpu / ram: {job: value}
    payload:   raw JSON returned for ANY query (to test malformed responses)
    error:     exception instance raised from get()
    """

    def __init__(self, cpu=None, ram=None, payload=None, error=None):
        self.cpu = cpu or {}
        self.ram = ram or {}
        self.payload = payload
        self.error = error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, url, params=None):
        self.calls.append({"url": url, "params": params})
        if self.error is not None:
            raise self.error
        if self.payload is not None:
            return FakeResponse(self.payload)

        query = (params or {}).get("query", "")
        if "node_cpu_seconds_total" in query:
            values = self.cpu
        elif "node_memory" in query:
            values = self.ram
        else:
            values = {}
        return FakeResponse(_vector_payload(values))


@pytest.fixture()
def make_prometheus_client():
    """Factory for FakeClient, e.g. to call tasks._query_prometheus(client, query) directly.

    Usage:
        client = make_prometheus_client(cpu={"pc1": 57.8})
        assert tasks._query_prometheus(client, tasks.CPU_QUERY) == {"pc1": 57.8}
    """

    def _make(cpu=None, ram=None, payload=None, error=None):
        return FakeClient(cpu=cpu, ram=ram, payload=payload, error=error)

    return _make


@pytest.fixture()
def patch_prometheus_client(monkeypatch, make_prometheus_client):
    """Patches tasks.httpx2.Client with a FakeClient.

    Usage:
        patch_prometheus_client(cpu={"pc1": 55.5}, ram={"pc1": 77.7})
        tasks.collect_and_save()
    """

    def _patch(cpu=None, ram=None, payload=None, error=None):
        fake_client = make_prometheus_client(
            cpu=cpu, ram=ram, payload=payload, error=error
        )
        monkeypatch.setattr(tasks_module.httpx2, "Client", lambda *a, **k: fake_client)
        return fake_client

    return _patch


@pytest.fixture()
def make_device(db_session):
    """Factory fixture: creates a Device row directly in the DB (bypassing the API)."""
    from mona_core.db import Device

    def _make(name="switch-me", ip="10.0.0.5", is_active=True):
        dev = Device(ip=ip, name=name, is_active=is_active)
        db_session.add(dev)
        db_session.commit()
        db_session.refresh(dev)
        return dev

    return _make


@pytest.fixture(scope="session")
def trained_model_bytes():
    """Serialized (model, scaler) made by the real anomaly_core pipeline.

    Hand-made fakes can't be used here: dump_model/load_active_model go through
    a trusted-types serializer, so custom test classes fail to load and
    detection silently falls back to auto-mode.
    """
    from mona_core.anomaly_core import dump_model, fit_detector

    rng = np.random.default_rng(0)
    n = 200
    features = np.column_stack(
        [
            rng.normal(50, 5, n),  # cpu
            rng.normal(40, 5, n),  # ram
            rng.normal(0, 1, (n, 4)),  # cpu_d1, ram_d1, cpu_d5, ram_d5
        ]
    )
    model, scaler = fit_detector(features)
    return dump_model(model, scaler)


@pytest.fixture()
def make_trained_model(db_session):
    from datetime import UTC, datetime
    from mona_core.db import TrainedModel

    def _make(
        model_data=b"x",
        trained_by="user",
        points_count=1,
        is_active=True,
        note="",
        period_from=None,
        period_to=None,
    ):
        record = TrainedModel(
            model_data=model_data,
            trained_by=trained_by,
            points_count=points_count,
            is_active=is_active,
            note=note,
            period_from=period_from or datetime(2026, 1, 1, tzinfo=UTC),
            period_to=period_to or datetime(2026, 1, 2, tzinfo=UTC),
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record

    return _make