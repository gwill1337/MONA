from datetime import UTC, datetime, timedelta

import pytest

from mona_core.db import Anomaly, Metric


# ─── helpers ────────────────────────────────────────────────────────────────
def _aligned(dt: datetime, seconds: int) -> datetime:
    """Округляет dt вниз до границы бакета длиной `seconds` (по epoch)."""
    return datetime.fromtimestamp(int(dt.timestamp()) // seconds * seconds, UTC)


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _add_metric(db_session, ts, cpu=50.0, ram=50.0, device="srv-1"):
    metric = Metric(cpu=cpu, ram=ram, device=device, timestamp=ts)
    db_session.add(metric)
    db_session.commit()
    db_session.refresh(metric)
    return metric


def _add_anomaly(db_session, metric, reason="cpu_spike", score=-0.5):
    anomaly = Anomaly(
        metric_id=metric.id,
        cpu=metric.cpu,
        ram=metric.ram,
        timestamp=metric.timestamp,
        reason=reason,
        score=score,
        device=metric.device,
    )
    db_session.add(anomaly)
    db_session.commit()
    return anomaly


def _seed_bucket_probe(db_session, bucket: int, offset: timedelta) -> datetime:
    """Кладёт 3 точки так, что результат однозначно показывает размер бакета.

    p1 и p2 — в начале и в конце одного бакета (должны слиться в среднее),
    p3 — сразу за границей (должна остаться отдельной точкой).
    """
    start = _aligned(datetime.now(UTC) - offset, bucket)
    _add_metric(db_session, start + timedelta(seconds=1), cpu=10, ram=20)
    _add_metric(db_session, start + timedelta(seconds=bucket - 1), cpu=30, ram=40)
    _add_metric(db_session, start + timedelta(seconds=bucket + 1), cpu=70, ram=80)
    return start


def _points(body):
    return [(_ts(m["timestamp"]), m["cpu"], m["ram"]) for m in body["metrics"]]


# ─── /db-metrics и базовое поведение /dashboard ─────────────────────────────
class TestDashboardAndMetrics:
    def test_db_metrics_empty(self, client, mock_user_auth):
        resp = client.get("/api/v1/db-metrics")
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "next_cursor": None}

    def test_db_metrics_filter_by_device(self, client, db_session, mock_user_auth):
        db_session.add_all(
            [
                Metric(cpu=10, ram=20, device="srv-1"),
                Metric(cpu=30, ram=40, device="srv-2"),
            ]
        )
        db_session.commit()

        resp = client.get("/api/v1/db-metrics", params={"device": "srv-1"})
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["device"] == "srv-1"

    def test_dashboard_empty(self, client, mock_user_auth):
        resp = client.get("/api/v1/dashboard")

        assert resp.status_code == 200
        assert resp.json() == {
            "devices": [],
            "model": None,
            "metrics": [],
            "anomalies": [],
        }

    def test_dashboard_combines_metrics_anomalies_and_model(
        self, client, db_session, mock_user_auth
    ):
        metric = _add_metric(
            db_session, datetime.now(UTC) - timedelta(minutes=5), cpu=50, ram=60
        )
        _add_anomaly(db_session, metric, reason="cpu_spike")

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        assert resp.status_code == 200
        body = resp.json()

        assert body["devices"] == ["srv-1"]
        assert len(body["metrics"]) == 1
        assert body["metrics"][0]["device"] == "srv-1"
        assert body["metrics"][0]["cpu"] == 50.0
        assert body["metrics"][0]["ram"] == 60.0
        assert len(body["anomalies"]) == 1
        assert body["anomalies"][0]["reason"] == "cpu_spike"
        assert body["model"] is None

    def test_dashboard_respects_time_window(self, client, db_session, mock_user_auth):
        old = datetime.now(UTC) - timedelta(hours=5)
        _add_metric(db_session, old, cpu=1, ram=1)

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        assert resp.json()["metrics"] == []

    def test_dashboard_anomalies_respect_time_window(
        self, client, db_session, mock_user_auth
    ):
        old = _add_metric(db_session, datetime.now(UTC) - timedelta(hours=5))
        _add_anomaly(db_session, old, reason="too_old")

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        assert resp.json()["anomalies"] == []

    def test_dashboard_devices_not_limited_by_window(
        self, client, db_session, mock_user_auth
    ):
        """Список устройств — по всей таблице, чтобы селектор не пустел."""
        _add_metric(db_session, datetime.now(UTC) - timedelta(days=3), device="srv-old")
        _add_metric(db_session, datetime.now(UTC) - timedelta(minutes=5), device="srv-new")

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        body = resp.json()

        assert sorted(body["devices"]) == ["srv-new", "srv-old"]
        assert [m["device"] for m in body["metrics"]] == ["srv-new"]

    def test_dashboard_device_filter(self, client, db_session, mock_user_auth):
        ts = datetime.now(UTC) - timedelta(minutes=5)
        m1 = _add_metric(db_session, ts, cpu=10, device="srv-1")
        m2 = _add_metric(db_session, ts, cpu=20, device="srv-2")
        _add_anomaly(db_session, m1, reason="from_srv_1")
        _add_anomaly(db_session, m2, reason="from_srv_2")

        resp = client.get("/api/v1/dashboard", params={"hours": 1, "device": "srv-1"})
        body = resp.json()

        assert [m["device"] for m in body["metrics"]] == ["srv-1"]
        assert [a["reason"] for a in body["anomalies"]] == ["from_srv_1"]
        # фильтр по устройству не должен сужать список устройств
        assert sorted(body["devices"]) == ["srv-1", "srv-2"]

    def test_dashboard_anomalies_sorted_ascending(
        self, client, db_session, mock_user_auth
    ):
        now = datetime.now(UTC)
        late = _add_metric(db_session, now - timedelta(minutes=5))
        early = _add_metric(db_session, now - timedelta(minutes=30))
        _add_anomaly(db_session, late, reason="late")
        _add_anomaly(db_session, early, reason="early")

        resp = client.get("/api/v1/dashboard", params={"hours": 1})

        assert [a["reason"] for a in resp.json()["anomalies"]] == ["early", "late"]

    def test_dashboard_returns_latest_user_model(
        self, client, db_session, make_trained_model, mock_user_auth
    ):
        old = make_trained_model(points_count=10)
        new = make_trained_model(points_count=20)
        # trained_at задаём явно, чтобы порядок не зависел от разрешения часов
        old.trained_at = datetime(2026, 1, 1, tzinfo=UTC)
        new.trained_at = datetime(2026, 1, 2, tzinfo=UTC)
        db_session.commit()

        resp = client.get("/api/v1/dashboard")

        assert resp.json()["model"]["points_count"] == 20

    def test_dashboard_ignores_non_user_models(
        self, client, make_trained_model, mock_user_auth
    ):
        make_trained_model(trained_by="auto")

        resp = client.get("/api/v1/dashboard")

        assert resp.json()["model"] is None


# ─── даунсэмплинг: усреднение по бакетам ────────────────────────────────────
class TestDashboardBucketing:
    def test_points_in_same_bucket_are_averaged(
        self, client, db_session, mock_user_auth
    ):
        start = _aligned(datetime.now(UTC) - timedelta(minutes=10), 60)
        _add_metric(db_session, start + timedelta(seconds=5), cpu=10, ram=20)
        _add_metric(db_session, start + timedelta(seconds=35), cpu=30, ram=40)

        resp = client.get("/api/v1/dashboard", params={"hours": 1})

        assert _points(resp.json()) == [(start, 20.0, 30.0)]

    def test_points_in_different_buckets_stay_separate(
        self, client, db_session, mock_user_auth
    ):
        start = _aligned(datetime.now(UTC) - timedelta(minutes=10), 60)
        _add_metric(db_session, start + timedelta(seconds=5), cpu=10, ram=20)
        _add_metric(db_session, start + timedelta(seconds=65), cpu=50, ram=60)

        resp = client.get("/api/v1/dashboard", params={"hours": 1})

        assert _points(resp.json()) == [
            (start, 10.0, 20.0),
            (start + timedelta(seconds=60), 50.0, 60.0),
        ]

    def test_bucketing_is_per_device(self, client, db_session, mock_user_auth):
        start = _aligned(datetime.now(UTC) - timedelta(minutes=10), 60)
        _add_metric(db_session, start + timedelta(seconds=5), cpu=10, device="srv-1")
        _add_metric(db_session, start + timedelta(seconds=35), cpu=30, device="srv-1")
        _add_metric(db_session, start + timedelta(seconds=20), cpu=100, device="srv-2")

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        metrics = resp.json()["metrics"]

        assert len(metrics) == 2
        assert {m["device"]: m["cpu"] for m in metrics} == {
            "srv-1": 20.0,
            "srv-2": 100.0,
        }

    def test_metrics_sorted_by_time_ascending_with_unique_ids(
        self, client, db_session, mock_user_auth
    ):
        start = _aligned(datetime.now(UTC) - timedelta(minutes=10), 60)
        # вставляем намеренно не по порядку
        _add_metric(db_session, start + timedelta(seconds=125), cpu=3)
        _add_metric(db_session, start + timedelta(seconds=5), cpu=1)
        _add_metric(db_session, start + timedelta(seconds=65), cpu=2)

        resp = client.get("/api/v1/dashboard", params={"hours": 1})
        metrics = resp.json()["metrics"]

        assert [m["cpu"] for m in metrics] == [1.0, 2.0, 3.0]
        assert len({m["id"] for m in metrics}) == len(metrics)

    @pytest.mark.parametrize(
        "hours, bucket, offset",
        [
            pytest.param(1, 60, timedelta(minutes=20), id="1h-1min"),
            pytest.param(12, 60, timedelta(minutes=20), id="12h-1min-boundary"),
            pytest.param(13, 600, timedelta(hours=3), id="13h-10min"),
            pytest.param(167, 600, timedelta(hours=3), id="167h-10min"),
            pytest.param(168, 3600, timedelta(hours=6), id="168h-1h-boundary"),
            pytest.param(0, 3600, timedelta(hours=6), id="all-1h"),
        ],
    )
    def test_bucket_size_depends_on_hours(
        self, client, db_session, mock_user_auth, hours, bucket, offset
    ):
        start = _seed_bucket_probe(db_session, bucket, offset)

        resp = client.get("/api/v1/dashboard", params={"hours": hours})

        assert _points(resp.json()) == [
            (start, 20.0, 30.0),
            (start + timedelta(seconds=bucket), 70.0, 80.0),
        ]

    @pytest.mark.parametrize(
        "range_hours, bucket, offset",
        [
            pytest.param(2, 60, timedelta(minutes=20), id="2h-1min"),
            pytest.param(48, 600, timedelta(hours=3), id="48h-10min"),
            pytest.param(192, 3600, timedelta(hours=6), id="8d-1h"),
            pytest.param(720, 3600, timedelta(hours=6), id="30d-1h"),
        ],
    )
    def test_bucket_size_depends_on_start_end_range(
        self, client, db_session, mock_user_auth, range_hours, bucket, offset
    ):
        start = _seed_bucket_probe(db_session, bucket, offset)
        now = datetime.now(UTC)

        resp = client.get(
            "/api/v1/dashboard",
            params={
                "start": (now - timedelta(hours=range_hours)).isoformat(),
                "end": now.isoformat(),
            },
        )

        assert _points(resp.json()) == [
            (start, 20.0, 30.0),
            (start + timedelta(seconds=bucket), 70.0, 80.0),
        ]

    def test_max_points_limits_metrics(self, client, db_session, mock_user_auth):
        base = _aligned(datetime.now(UTC) - timedelta(minutes=30), 60)
        for i in range(5):
            _add_metric(db_session, base + timedelta(seconds=i * 60 + 5), cpu=i)

        resp = client.get("/api/v1/dashboard", params={"hours": 1, "max_points": 3})

        assert len(resp.json()["metrics"]) == 3


# ─── start / end ────────────────────────────────────────────────────────────
class TestDashboardRange:
    def test_hours_zero_returns_all_history(self, client, db_session, mock_user_auth):
        now = datetime.now(UTC)
        _add_metric(db_session, now - timedelta(days=100), cpu=1)
        _add_metric(db_session, now - timedelta(hours=5), cpu=2)

        resp = client.get("/api/v1/dashboard", params={"hours": 0})

        assert [m["cpu"] for m in resp.json()["metrics"]] == [1.0, 2.0]

    def test_start_end_filter_metrics_and_anomalies(
        self, client, db_session, mock_user_auth
    ):
        now = datetime.now(UTC)
        before = _add_metric(db_session, now - timedelta(hours=4), cpu=11)
        inside = _add_metric(db_session, now - timedelta(hours=2), cpu=22)
        after = _add_metric(db_session, now - timedelta(minutes=30), cpu=33)
        _add_anomaly(db_session, before, reason="before")
        _add_anomaly(db_session, inside, reason="inside")
        _add_anomaly(db_session, after, reason="after")

        resp = client.get(
            "/api/v1/dashboard",
            params={
                "start": (now - timedelta(hours=3)).isoformat(),
                "end": (now - timedelta(hours=1)).isoformat(),
            },
        )
        body = resp.json()

        assert [m["cpu"] for m in body["metrics"]] == [22.0]
        assert [a["reason"] for a in body["anomalies"]] == ["inside"]

    def test_start_end_override_hours(self, client, db_session, mock_user_auth):
        """hours=1 исключил бы точку 2 часа назад, но start/end важнее."""
        now = datetime.now(UTC)
        _add_metric(db_session, now - timedelta(hours=2), cpu=22)

        resp = client.get(
            "/api/v1/dashboard",
            params={
                "hours": 1,
                "start": (now - timedelta(hours=3)).isoformat(),
                "end": (now - timedelta(hours=1)).isoformat(),
            },
        )

        assert [m["cpu"] for m in resp.json()["metrics"]] == [22.0]

    def test_start_end_with_device_filter(self, client, db_session, mock_user_auth):
        now = datetime.now(UTC)
        ts = now - timedelta(hours=2)
        _add_metric(db_session, ts, cpu=1, device="srv-1")
        _add_metric(db_session, ts, cpu=2, device="srv-2")

        resp = client.get(
            "/api/v1/dashboard",
            params={
                "start": (now - timedelta(hours=3)).isoformat(),
                "end": (now - timedelta(hours=1)).isoformat(),
                "device": "srv-2",
            },
        )

        assert [(m["device"], m["cpu"]) for m in resp.json()["metrics"]] == [
            ("srv-2", 2.0)
        ]


# ─── валидация параметров ───────────────────────────────────────────────────
class TestDashboardParams:
    def test_max_points_upper_bound(self, client, mock_user_auth):
        ok = client.get("/api/v1/dashboard", params={"max_points": 10000})
        too_many = client.get("/api/v1/dashboard", params={"max_points": 10001})

        assert ok.status_code == 200
        assert too_many.status_code == 422

    @pytest.mark.parametrize(
        "params",
        [
            {"hours": "abc"},
            {"start": "not-a-date"},
            {"end": "yesterday"},
            {"max_points": "many"},
        ],
    )
    def test_invalid_params_rejected(self, client, mock_user_auth, params):
        resp = client.get("/api/v1/dashboard", params=params)

        assert resp.status_code == 422