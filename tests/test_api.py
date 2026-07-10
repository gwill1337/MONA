from datetime import UTC, datetime, timedelta

import pytest

from mona_core.db import AdminUser, Anomaly, Device, Metric, TrainedModel


class TestProbes:
    def test_liveness_probe(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "alive"}

    def test_readiness_probe_ok(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}

    def test_readiness_probe_db_down(self, client, monkeypatch):
        from sqlalchemy.orm import Session

        def broken_execute(self, *args, **kwargs):
            raise Exception("connection refused")

        monkeypatch.setattr(Session, "execute", broken_execute)

        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Database unavailable"


class TestDevices:
    def test_get_device_empty(self, client, mock_admin_auth):
        resp = client.get("/devices")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_device(self, client, mock_admin_auth):
        payload = {"ip": "192.168.1.10", "name": "office-pc-1", "is_active": True}
        resp = client.post("/devices", json=payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["ip"] == payload["ip"]
        assert body["name"] == payload["name"]
        assert body["is_active"] is True
        assert "id" in body

    def test_create_device_default_active(self, client, mock_admin_auth):
        payload = {"ip": "192.168.1.10", "name": "office-pc-1"}
        resp = client.post("/devices", json=payload)
        assert resp.status_code == 201
        assert resp.json()["is_active"] is True

    def test_create_device_duplicate_name_conflict(self, client, mock_admin_auth):
        payload = {"ip": "10.0.0.1", "name": "dup-name"}
        first = client.post("/devices", json=payload)
        assert first.status_code == 201

        second = client.post("/devices", json={"ip": "10.0.0.2", "name": "dup-name"})
        assert second.status_code == 409
        assert second.json()["detail"] == "Name already exists"

    def test_list_devices_after_create(self, client, mock_admin_auth):
        client.post("/devices", json={"ip": "10.0.0.1", "name": "a"})
        client.post("/devices", json={"ip": "10.0.0.2", "name": "b"})

        resp = client.get("/devices")
        assert resp.status_code == 200
        names = {d["name"] for d in resp.json()}
        assert names == {"a", "b"}

    def test_delete_device_success(self, client, db_session, mock_admin_auth):
        dev = Device(ip="10.0.0.9", name="to-delete")
        db_session.add(dev)
        db_session.commit()
        db_session.refresh(dev)

        resp = client.delete(f"/devices/{dev.id}")
        assert resp.status_code == 200
        assert resp.json() == {"message": "Device deleted successfully"}

        resp2 = client.get("/devices")
        assert resp2.json() == []

    def test_delete_device_not_found(self, client, mock_admin_auth):
        resp = client.delete("/devices/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"


class TestModel:
    def test_model_info_no_model(self, client, mock_admin_auth):
        resp = client.get("/model-info")
        assert resp.status_code == 200
        assert resp.json() == {
            "status": "no_model",
            "message": "Model is not manually trained yet. Using auto-mode.",
        }

    def test_model_info_with_model(self, client, db_session, mock_admin_auth):
        db_session.add(
            TrainedModel(
                model_data=b"binary-blob",
                trained_by="user",
                points_count=1000,
                period_from=datetime(2026, 1, 1, tzinfo=UTC),
                period_to=datetime(2026, 1, 2, tzinfo=UTC),
                note="nightly training",
            )
        )
        db_session.commit()

        resp = client.get("/model-info")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model"]["points_count"] == 1000
        assert body["model"]["note"] == "nightly training"

    def test_model_info_ignores_non_user_trained(self, client, db_session, mock_admin_auth):
        db_session.add(
            TrainedModel(
                model_data=b"x",
                trained_by="auto",
                points_count=1,
                period_from=datetime(2026, 1, 1, tzinfo=UTC),
                period_to=datetime(2026, 1, 2, tzinfo=UTC),
                note="",
            )
        )
        db_session.commit()

        resp = client.get("/model-info")
        assert resp.json()["status"] == "no_model"

    def test_delete_model(self, client, db_session, mock_admin_auth):
        db_session.add(
            TrainedModel(
                model_data=b"x",
                trained_by="user",
                points_count=1,
                period_from=datetime(2026, 1, 1, tzinfo=UTC),
                period_to=datetime(2026, 1, 2, tzinfo=UTC),
                note="",
            )
        )
        db_session.commit()

        resp = client.delete("/model")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["deleted"] == 1

        assert client.get("/model-info").json()["status"] == "no_model"

    def test_delete_model_when_none_exists(self, client, mock_admin_auth):
        resp = client.delete("/model")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 0


class TestDashboardAndMetrics:
    def test_db_metrics_empty(self, client, mock_admin_auth):
        resp = client.get("/db-metrics")
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "next_cursor": None}

    def test_db_metrics_filter_by_device(self, client, db_session, mock_admin_auth):
        db_session.add_all(
            [
                Metric(cpu=10, ram=20, device="srv-1"),
                Metric(cpu=30, ram=40, device="srv-2"),
            ]
        )
        db_session.commit()

        resp = client.get("/db-metrics", params={"device": "srv-1"})
        body = resp.json()
        assert len(body) == 2
        assert body["items"][0]["device"] == "srv-1"

    def test_dashboard_combines_metrics_anomalies_and_model(self, client, db_session, mock_admin_auth):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                Metric(cpu=50, ram=60, device="srv-1", timestamp=now),
                Anomaly(
                    metric_id=1,
                    cpu=95,
                    ram=90,
                    timestamp=now,
                    reason="cpu_spike",
                    score=0.99,
                    device="srv-1",
                ),
            ]
        )
        db_session.commit()

        resp = client.get("/api/dashboard", params={"hours": 1})
        assert resp.status_code == 200
        body = resp.json()

        assert "srv-1" in body["devices"]
        assert len(body["metrics"]) == 1
        assert len(body["anomalies"]) == 1
        assert body["model"] is None

    def test_dashboard_respects_time_window(self, client, db_session, mock_admin_auth):
        old = datetime.now(UTC) - timedelta(hours=5)
        db_session.add(Metric(cpu=1, ram=1, device="srv-1", timestamp=old))
        db_session.commit()

        resp = client.get("/api/dashboard", params={"hours": 1})
        assert resp.json()["metrics"] == []


class TestTasks:
    def test_train_model_submits_task(self, client, mock_celery, mock_admin_auth):
        resp = client.post("/train", params={"hours": 2.5, "note": "manual run"})

        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "accepted"
        # assert body["task_id"] == "fake-task-id-123"
        assert "task_id" in body

        assert len(mock_celery["send_task_calls"]) == 1
        call = mock_celery["send_task_calls"][0]
        assert call["name"] == "tasks.train_model_task"
        assert call["kwargs"] == {"hours": 2.5, "note": "manual run"}

    def test_train_model_defaults(self, client, mock_celery, mock_admin_auth):
        resp = client.post("/train")
        assert resp.status_code == 202
        # call = mock_celery["send_task_calls"][0]
        # assert call["kwargs"] == {"hours": 1.0, "note": ""}
        assert len(mock_celery["send_task_calls"]) == 1
        call = mock_celery["send_task_calls"][0]
        assert call["name"] == "tasks.train_model_task"

    def test_task_status_pending(self, client, mock_celery, mock_admin_auth):
        resp = client.get("/task-status/some-task-id")
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == "some-task-id"
        assert body["state"] == "PENDING"
        assert body["result"] is None

        assert mock_celery["async_result_calls"] == ["some-task-id"]

    def test_task_status_success(self, client, mock_celery, mock_admin_auth):
        fake_result_class = type(mock_celery["async_result_return"])
        mock_celery["async_result_return"] = fake_result_class(
            state="SUCCESS", result={"accuracy": 0.97}
        )

        resp = client.get("/task-status/finished-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "SUCCESS"
        assert body["result"] == {"accuracy": 0.97}

    def test_task_status_failure(self, client, mock_celery, mock_admin_auth):
        fake_result_class = type(mock_celery["async_result_return"])
        mock_celery["async_result_return"] = fake_result_class(
            state="FAILURE", result="boom: division by zero"
        )

        resp = client.get("/task-status/broken-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "FAILURE"
        assert body["result"] == "boom: division by zero"


class TestAnomalies:
    def _make_anomaly(self, device, timestamp, score=0.9):
        return Anomaly(
            metric_id=1,
            cpu=90.0,
            ram=80.0,
            timestamp=timestamp,
            reason="cpu_spike",
            score=score,
            device=device,
        )

    def test_get_anomalies_default_window(self, client, db_session, mock_admin_auth):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                self._make_anomaly("srv-1", now - timedelta(hours=1)),
                self._make_anomaly("srv-1", now - timedelta(hours=48)),
            ]
        )
        db_session.commit()

        resp = client.get("/anomalies")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        assert body["items"][0]["device"] == "srv-1"

    def test_get_anomalies_filter_by_device(self, client, db_session, mock_admin_auth):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                self._make_anomaly("srv-1", now),
                self._make_anomaly("srv-2", now),
            ]
        )
        db_session.commit()

        resp = client.get("/anomalies", params={"device": "srv-2"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        assert body["items"][0]["device"] == "srv-2"

    def test_get_anomalies_hours_zero_disables_time_filter(self, client, db_session, mock_admin_auth):
        now = datetime.now(UTC)
        db_session.add(self._make_anomaly("srv-1", now - timedelta(days=30)))
        db_session.commit()

        resp = client.get("/anomalies", params={"hours": 0})
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_get_anomalies_ordered_desc(self, client, db_session, mock_admin_auth):
        now = datetime.now(UTC)
        db_session.add_all(
            [
                self._make_anomaly("srv-1", now - timedelta(minutes=10)),
                self._make_anomaly("srv-1", now - timedelta(minutes=1)),
            ]
        )
        db_session.commit()

        resp = client.get("/anomalies")
        body = resp.json()
        timestamps = [a["timestamp"] for a in body["items"]]
        assert timestamps == sorted(timestamps, reverse=True)


class TestPrometheus:
    def test_prometheus_targets_only_active_with_ip(self, client, db_session):
        db_session.add_all(
            [
                Device(ip="10.0.0.1", name="active-1", is_active=True),
                Device(ip="10.0.0.2", name="inactive-1", is_active=False),
            ]
        )
        db_session.commit()

        resp = client.get("/api/prometheus/targets")
        assert resp.status_code == 200
        body = resp.json()

        assert len(body) == 1
        target = body[0]
        assert target["targets"] == ["10.0.0.1:9100"]
        assert target["labels"] == {
            "job": "active-1",
            "physical_pc": "true",
            "device_label": "active-1",
        }


class TestAuth:
    def test_valid_login(self, client, db_session, mock_redis):
        admin = AdminUser(username="admin")
        admin.set_password("123456")

        db_session.add(admin)
        db_session.commit()

        resp = client.post(
            "api/auth/login", json={"username": "admin", "password": "123456"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        assert "admin_session" in resp.cookies

    def test_invalid_login(self, client, db_session, mock_redis):
        admin = AdminUser(username="admin")
        admin.set_password("password123")

        db_session.add(admin)
        db_session.commit()

        resp = client.post(
            "api/auth/login", json={"username": "admin", "password": "123456"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid username or password"

    def test_auth_me(self, client, mock_admin_auth):
        resp = client.get("/api/auth/me")

        assert resp.status_code == 200
        assert resp.json() == {"authenticated": True}

    def test_valid_logout(self, client, mock_redis):
        client.cookies.set("admin_session", "session123")

        resp = client.post(
            "/api/auth/logout",
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_password_hash(self):
        admin = AdminUser(username="admin")

        admin.set_password("123456")

        assert admin.password_hash != "123456"
        assert admin.check_password("123456")
        assert not admin.check_password("qwerty")

    def test_password_hash_random_salt(self):
        a = AdminUser(username="a")
        b = AdminUser(username="b")

        a.set_password("123456")
        b.set_password("123456")

        assert a.password_hash != b.password_hash

class TestSecureEndpoints:
    @pytest.mark.parametrize(
        "method, endpoint",
        [
            # Auth
            ("GET", "/api/auth/me"),

            # Devices
            ("GET", "/devices"),
            ("POST", "/devices"),
            ("DELETE", "/devices/1"),

            # Model & Anomalies
            ("GET", "/anomalies"),
            ("GET", "/model-info"),
            ("POST", "/train?hours=1"),
            ("DELETE", "/model"),

            # Dashboard & Metrics
            ("GET", "/api/dashboard"),
            ("GET", "/db-metrics"),

            # Tasks
            ("GET", "/task-status/dummy-task-id-123"),
        ],
    )
    def test_endpoints_without_cookie_return_401(self, client, method, endpoint):
        resp = client.request(method, endpoint)

        assert resp.status_code == 401
