from datetime import UTC, datetime, timedelta

import pytest

import mona_core.tasks as tasks
from mona_core.db import Anomaly, Device, Metric, TrainedModel


def _series(job, value):
    """One Prometheus instant-vector series."""
    metric = {"job": job} if job is not None else {}
    return {"metric": metric, "value": [1700000000, value]}


def _payload(*series):
    return {"data": {"result": list(series)}}


class TestParseExporters:
    def test_parses_pairs(self, monkeypatch):
        monkeypatch.setenv("EXPORTERS", "pc1:10.0.0.1, pc2 : 10.0.0.2")

        assert tasks._parse_exporters() == {"pc1": "10.0.0.1", "pc2": "10.0.0.2"}

    def test_skips_invalid_entries(self, monkeypatch):
        monkeypatch.setenv("EXPORTERS", "badvalue,:1.1.1.1,noip:,pc1:10.0.0.1")

        assert tasks._parse_exporters() == {"pc1": "10.0.0.1"}

    def test_empty_env(self, monkeypatch):
        monkeypatch.delenv("EXPORTERS", raising=False)

        assert tasks._parse_exporters() == {}


class TestQueryPrometheus:
    def test_returns_value_per_job(self, make_prometheus_client):
        client = make_prometheus_client(cpu={"pc1": 57.8, "pc2": 12.0})

        values = tasks._query_prometheus(client, tasks.CPU_QUERY)

        assert values == {"pc1": 57.8, "pc2": 12.0}
        assert client.calls[0]["params"] == {"query": tasks.CPU_QUERY}

    def test_empty_result(self, make_prometheus_client):
        client = make_prometheus_client(payload=_payload())

        assert tasks._query_prometheus(client, "up") == {}

    def test_skips_non_finite_values_and_series_without_job(
        self, make_prometheus_client
    ):
        client = make_prometheus_client(
            payload=_payload(
                _series("pc1", "42.5"),
                _series("pc2", "NaN"),
                _series("pc3", "+Inf"),
                _series(None, "10"),
            )
        )

        assert tasks._query_prometheus(client, "up") == {"pc1": 42.5}

    @pytest.mark.parametrize(
        "payload",
        [
            _payload({"value": [1, "5"]}),  # no "metric"
            _payload({"metric": {"job": "pc1"}, "value": [1, "abc"]}),  # not a number
            _payload({"metric": {"job": "pc1"}, "value": []}),  # no value
        ],
    )
    def test_malformed_payload_returns_empty(self, make_prometheus_client, payload):
        client = make_prometheus_client(payload=payload)

        assert tasks._query_prometheus(client, "up") == {}

    def test_request_error_returns_empty(self, make_prometheus_client):
        client = make_prometheus_client(error=ValueError("boom"))

        assert tasks._query_prometheus(client, "up") == {}


class TestCollectAndSave:
    def test_collect_creates_device(
        self,
        monkeypatch,
        db_session,
        patch_prometheus_client,
    ):
        monkeypatch.setenv("EXPORTERS", "pc1:10.0.0.1")
        patch_prometheus_client(cpu={"pc1": 25.0}, ram={"pc1": 25.0})

        result = tasks.collect_and_save()

        assert len(result) == 1

        device = db_session.query(Device).first()

        assert device.name == "pc1"
        assert device.ip == "10.0.0.1"
        assert device.is_active is True

    def test_collect_updates_ip(
        self,
        monkeypatch,
        db_session,
        patch_prometheus_client,
    ):
        db_session.add(Device(name="pc1", ip="1.1.1.1", is_active=True))
        db_session.commit()

        monkeypatch.setenv("EXPORTERS", "pc1:2.2.2.2")
        patch_prometheus_client(cpu={"pc1": 10}, ram={"pc1": 10})

        tasks.collect_and_save()

        device = db_session.query(Device).first()

        assert device.ip == "2.2.2.2"

    def test_collect_skips_invalid_exporter(
        self,
        monkeypatch,
        db_session,
        patch_prometheus_client,
    ):
        monkeypatch.setenv("EXPORTERS", "badvalue")
        patch_prometheus_client()

        tasks.collect_and_save()

        assert db_session.query(Device).count() == 0

    def test_collect_saves_metric(
        self,
        monkeypatch,
        db_session,
        patch_prometheus_client,
    ):
        monkeypatch.delenv("EXPORTERS", raising=False)
        db_session.add(Device(name="pc1", ip="10.0.0.1", is_active=True))
        db_session.commit()

        patch_prometheus_client(cpu={"pc1": 55.5}, ram={"pc1": 77.7})

        result = tasks.collect_and_save()

        metric = db_session.query(Metric).first()

        assert metric.cpu == 55.5
        assert metric.ram == 77.7
        assert metric.device == "pc1"

        assert result == [{"device": "pc1", "cpu": 55.5, "ram": 77.7}]

    def test_collect_makes_one_grouped_query_per_metric(
        self,
        monkeypatch,
        db_session,
        make_device,
        patch_prometheus_client,
    ):
        monkeypatch.delenv("EXPORTERS", raising=False)
        make_device(name="pc1")
        make_device(name="pc2", ip="10.0.0.6")

        client = patch_prometheus_client(
            cpu={"pc1": 10.0, "pc2": 20.0}, ram={"pc1": 30.0, "pc2": 40.0}
        )

        result = tasks.collect_and_save()

        assert isinstance(result, list)
        assert len(client.calls) == 2  # CPU + RAM, not per device
        assert {r["device"]: (r["cpu"], r["ram"]) for r in result} == {
            "pc1": (10.0, 30.0),
            "pc2": (20.0, 40.0),
        }

    def test_collect_rounds_result_but_stores_raw_values(
        self,
        monkeypatch,
        db_session,
        make_device,
        patch_prometheus_client,
    ):
        monkeypatch.delenv("EXPORTERS", raising=False)
        make_device(name="pc1")
        patch_prometheus_client(cpu={"pc1": 12.3456}, ram={"pc1": 65.4321})

        result = tasks.collect_and_save()

        assert result == [{"device": "pc1", "cpu": 12.35, "ram": 65.43}]
        metric = db_session.query(Metric).first()
        assert metric.cpu == pytest.approx(12.3456)
        assert metric.ram == pytest.approx(65.4321)

    def test_collect_skips_inactive_devices(
        self,
        monkeypatch,
        db_session,
        make_device,
        patch_prometheus_client,
    ):
        monkeypatch.delenv("EXPORTERS", raising=False)
        make_device(name="pc1", is_active=True)
        make_device(name="pc2", ip="10.0.0.6", is_active=False)
        patch_prometheus_client(
            cpu={"pc1": 10.0, "pc2": 20.0}, ram={"pc1": 30.0, "pc2": 40.0}
        )

        result = tasks.collect_and_save()

        assert isinstance(result, list)
        assert [r["device"] for r in result] == ["pc1"]
        assert db_session.query(Metric).count() == 1

    def test_collect_stores_zero_for_device_missing_in_prometheus(
        self,
        monkeypatch,
        db_session,
        make_device,
        patch_prometheus_client,
    ):
        monkeypatch.delenv("EXPORTERS", raising=False)
        make_device(name="pc1")
        make_device(name="pc2", ip="10.0.0.6")
        patch_prometheus_client(cpu={"pc1": 10.0}, ram={"pc1": 30.0})

        result = tasks.collect_and_save()

        assert isinstance(result, list)
        by_device = {r["device"]: r for r in result}
        assert by_device["pc2"] == {"device": "pc2", "cpu": 0.0, "ram": 0.0}

    def test_collect_stores_zeros_when_prometheus_fails(
        self,
        monkeypatch,
        db_session,
        make_device,
        patch_prometheus_client,
    ):
        monkeypatch.delenv("EXPORTERS", raising=False)
        make_device(name="pc1")
        patch_prometheus_client(error=ValueError("prometheus down"))

        result = tasks.collect_and_save()

        assert result == [{"device": "pc1", "cpu": 0.0, "ram": 0.0}]
        assert db_session.query(Metric).count() == 1

    def test_collect_returns_error_on_unexpected_failure(
        self,
        monkeypatch,
        db_session,
    ):
        def boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(tasks, "_parse_exporters", boom)

        result = tasks.collect_and_save()

        assert result == {"error": "boom"}


class TestTrainModel:
    def _metric(self, i, total=40, device="pc1"):
        """`total` points, one per minute, the last one a minute ago."""
        return Metric(
            cpu=30 + i,
            ram=40 + i,
            device=device,
            timestamp=datetime.now(UTC) - timedelta(minutes=total - i),
        )

    def test_not_enough_points(
        self,
        db_session,
    ):
        db_session.add_all([self._metric(i, total=10) for i in range(10)])
        db_session.commit()

        result = tasks.train_model_task(24, "")

        assert result["status"] == "error"
        assert "Not enough clean data" in result["message"]
        assert "found 10 points" in result["message"]
        assert db_session.query(TrainedModel).count() == 0

    def test_train_success(
        self,
        db_session,
    ):
        db_session.add_all([self._metric(i) for i in range(40)])
        db_session.commit()

        result = tasks.train_model_task(24, "first model")

        assert result["status"] == "success"
        assert "40 clean points" in result["message"]

        model = db_session.query(TrainedModel).first()

        assert model is not None
        assert model.points_count == 40
        assert model.note == "first model"
        assert model.trained_by == "user"

    def test_train_activates_by_default(self, db_session):
        db_session.add_all([self._metric(i) for i in range(40)])
        db_session.commit()

        tasks.train_model_task(24, "")

        model = db_session.query(TrainedModel).first()
        assert model.is_active is True

    def test_train_without_activation(self, db_session):
        db_session.add_all([self._metric(i) for i in range(40)])
        db_session.commit()

        result = tasks.train_model_task(24, "", activate=False)

        assert result["status"] == "success"
        assert "Saved, not activated." in result["message"]
        model = db_session.query(TrainedModel).first()
        assert model.is_active is False

    def test_train_replaces_previously_active_model(
        self, db_session, make_trained_model
    ):
        old = make_trained_model(is_active=True)
        db_session.add_all([self._metric(i) for i in range(40)])
        db_session.commit()

        tasks.train_model_task(24, "")

        active = db_session.query(TrainedModel).filter_by(is_active=True).all()
        assert len(active) == 1
        assert active[0].id != old.id

    def test_train_prunes_old_models(self, db_session, make_trained_model):
        for _ in range(tasks.MAX_STORED_MODELS + 2):
            make_trained_model(is_active=False)
        db_session.add_all([self._metric(i) for i in range(40)])
        db_session.commit()

        tasks.train_model_task(24, "")

        assert db_session.query(TrainedModel).count() == tasks.MAX_STORED_MODELS
        assert db_session.query(TrainedModel).filter_by(is_active=True).count() == 1

    def test_train_uses_only_requested_period(self, db_session):
        db_session.add_all([self._metric(i, total=60) for i in range(60)])
        db_session.commit()

        result = tasks.train_model_task(0.75, "")  # last 45 minutes

        assert result["status"] == "success"
        model = db_session.query(TrainedModel).first()
        assert tasks.MIN_TRAINING_POINTS <= model.points_count <= 45

    def test_train_excludes_known_anomalies(self, db_session):
        # 60 points, one per minute. known_anomaly_mask drops +-5 minutes around the
        # anomaly (about 9-11 points); use plenty of points so what is left stays
        # above MIN_TRAINING_POINTS regardless of boundary rounding.
        metrics = [self._metric(i, total=60) for i in range(60)]
        db_session.add_all(metrics)
        db_session.commit()

        middle = metrics[30]
        db_session.add(
            Anomaly(
                metric_id=middle.id,
                cpu=middle.cpu,
                ram=middle.ram,
                timestamp=middle.timestamp,
                reason="test",
                score=-0.5,
                device="pc1",
            )
        )
        db_session.commit()

        result = tasks.train_model_task(24, "")

        assert result["status"] == "success"
        model = db_session.query(TrainedModel).first()
        assert 47 <= model.points_count <= 51

    def test_empty_note_saved_as_none(
        self,
        db_session,
    ):
        db_session.add_all([self._metric(i, total=35) for i in range(35)])
        db_session.commit()

        tasks.train_model_task(24, "   ")

        model = db_session.query(TrainedModel).first()

        assert model.note is None

    def test_serialization_failure_returns_server_error(
        self,
        monkeypatch,
        db_session,
    ):
        db_session.add_all([self._metric(i, total=35) for i in range(35)])
        db_session.commit()

        def fail(*args, **kwargs):
            raise RuntimeError("skops error")

        monkeypatch.setattr(tasks, "dump_model", fail)

        result = tasks.train_model_task(24, "")

        assert result["status"] == "error"
        assert "Server error" in result["message"]
        assert db_session.query(TrainedModel).count() == 0


class TestTasksApi:
    def test_train_model_submits_task(self, client, mock_celery, mock_admin_auth):
        resp = client.post("/api/v1/train", params={"hours": 2.5, "note": "manual run"})

        assert resp.status_code == 202
        assert resp.json()["status"] == "accepted"

        call = mock_celery["send_task_calls"][0]
        assert call["name"] == "tasks.train_model_task"
        assert call["kwargs"] == {"hours": 2.5, "note": "manual run", "activate": True}

    def test_train_model_defaults(self, client, mock_celery, mock_admin_auth):
        resp = client.post("/api/v1/train")
        assert resp.status_code == 202
        assert len(mock_celery["send_task_calls"]) == 1
        call = mock_celery["send_task_calls"][0]
        assert call["name"] == "tasks.train_model_task"

    def test_task_status_pending(self, client, mock_celery, mock_user_auth):
        resp = client.get("/api/v1/task-status/some-task-id")
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == "some-task-id"
        assert body["state"] == "PENDING"
        assert body["result"] is None

        assert mock_celery["async_result_calls"] == ["some-task-id"]

    def test_task_status_success(self, client, mock_celery, mock_user_auth):
        fake_result_class = type(mock_celery["async_result_return"])
        mock_celery["async_result_return"] = fake_result_class(
            state="SUCCESS", result={"accuracy": 0.97}
        )

        resp = client.get("/api/v1/task-status/finished-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "SUCCESS"
        assert body["result"] == {"accuracy": 0.97}

    def test_task_status_failure(self, client, mock_celery, mock_user_auth):
        fake_result_class = type(mock_celery["async_result_return"])
        mock_celery["async_result_return"] = fake_result_class(
            state="FAILURE", result="boom: division by zero"
        )

        resp = client.get("/api/v1/task-status/broken-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "FAILURE"
        assert body["result"] == "boom: division by zero"

    def test_train_model_activate_false(self, client, mock_celery, mock_admin_auth):
        resp = client.post("/api/v1/train", params={"activate": False})

        assert resp.status_code == 202
        assert mock_celery["send_task_calls"][0]["kwargs"]["activate"] is False