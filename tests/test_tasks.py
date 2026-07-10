from datetime import UTC, datetime, timedelta

import mona_core.tasks as tasks
from mona_core.db import Device, Metric, TrainedModel


class TestHelpers:
    def test_build_features_shape(self):
        rows = [
            Metric(cpu=10, ram=20),
            Metric(cpu=15, ram=25),
            Metric(cpu=20, ram=35),
            Metric(cpu=30, ram=40),
            Metric(cpu=35, ram=50),
            Metric(cpu=50, ram=60),
        ]

        x = tasks._build_features(rows)

        assert x.shape == (6, 6)

    def test_build_features_first_row(self):
        rows = [
            Metric(cpu=10, ram=20),
            Metric(cpu=15, ram=25),
            Metric(cpu=20, ram=35),
            Metric(cpu=30, ram=40),
            Metric(cpu=35, ram=50),
            Metric(cpu=50, ram=60),
        ]

        x = tasks._build_features(rows)

        assert list(x[0]) == [10, 20, 0, 0, 0, 0]

    def test_build_features_delta(self):
        rows = [
            Metric(cpu=10, ram=20),
            Metric(cpu=15, ram=30),
            Metric(cpu=18, ram=35),
            Metric(cpu=22, ram=40),
            Metric(cpu=30, ram=45),
            Metric(cpu=45, ram=55),
        ]

        x = tasks._build_features(rows)

        assert x[1][2] == 5
        assert x[1][3] == 10

        assert x[5][4] == 35
        assert x[5][5] == 35


class TestQuery:
    def test_query_returns_value(self, monkeypatch):
        class FakeResponse:
            def json(self):
                return {"data": {"result": [{"value": [123, "57.8"]}]}}

        monkeypatch.setattr(tasks.requests, "get", lambda *a, **k: FakeResponse())

        value = tasks._query("http://localhost", "up")

        assert value == 57.8

    def test_query_empty_result(self, monkeypatch):
        class FakeResponse:
            def json(self):
                return {"data": {"result": []}}

        monkeypatch.setattr(tasks.requests, "get", lambda *a, **k: FakeResponse())

        assert tasks._query("url", "query") == 0


class TestCollectAndSave:
    def test_collect_creates_device(
        self,
        monkeypatch,
        db_session,
    ):
        monkeypatch.setenv(
            "EXPORTERS",
            "pc1:10.0.0.1",
        )

        monkeypatch.setattr(
            tasks,
            "_query",
            lambda *a, **k: 25.0,
        )

        result = tasks.collect_and_save()

        assert len(result) == 1

        device = db_session.query(Device).first()

        assert device.name == "pc1"
        assert device.ip == "10.0.0.1"

    def test_collect_updates_ip(
        self,
        monkeypatch,
        db_session,
    ):
        db_session.add(
            Device(
                name="pc1",
                ip="1.1.1.1",
                is_active=True,
            )
        )
        db_session.commit()

        monkeypatch.setenv(
            "EXPORTERS",
            "pc1:2.2.2.2",
        )

        monkeypatch.setattr(
            tasks,
            "_query",
            lambda *a, **k: 10,
        )

        tasks.collect_and_save()

        device = db_session.query(Device).first()

        assert device.ip == "2.2.2.2"

    def test_collect_skips_invalid_exporter(
        self,
        monkeypatch,
        db_session,
    ):
        monkeypatch.setenv(
            "EXPORTERS",
            "badvalue",
        )

        tasks.collect_and_save()

        assert db_session.query(Device).count() == 0

    def test_collect_saves_metric(
        self,
        monkeypatch,
        db_session,
    ):
        db_session.add(
            Device(
                name="pc1",
                ip="10.0.0.1",
                is_active=True,
            )
        )
        db_session.commit()

        values = iter([55.5, 77.7])

        monkeypatch.setattr(
            tasks,
            "_query",
            lambda *a, **k: next(values),
        )

        result = tasks.collect_and_save()

        metric = db_session.query(Metric).first()

        assert metric.cpu == 55.5
        assert metric.ram == 77.7

        assert result == [
            {
                "device": "pc1",
                "cpu": 55.5,
                "ram": 77.7,
            }
        ]


class TestTrainModel:
    def _metric(self, i):
        return Metric(
            cpu=30 + i,
            ram=40 + i,
            device="pc1",
            timestamp=datetime.now(UTC) - timedelta(minutes=40 - i),
        )

    def test_not_enough_points(
        self,
        db_session,
    ):
        db_session.add_all([self._metric(i) for i in range(10)])
        db_session.commit()

        result = tasks.train_model_task(
            24,
            "",
        )

        assert result["status"] == "error"
        assert "Not enough data" in result["message"]

    def test_train_success(
        self,
        db_session,
    ):
        db_session.add_all([self._metric(i) for i in range(40)])
        db_session.commit()

        result = tasks.train_model_task(
            24,
            "first model",
        )

        assert result["status"] == "success"

        model = db_session.query(TrainedModel).first()

        assert model is not None
        assert model.points_count == 40
        assert model.note == "first model"

    def test_empty_note_saved_as_none(
        self,
        db_session,
    ):
        db_session.add_all([self._metric(i) for i in range(35)])
        db_session.commit()

        tasks.train_model_task(
            24,
            "   ",
        )

        model = db_session.query(TrainedModel).first()

        assert model.note is None

    def test_pickle_failure(
        self,
        monkeypatch,
        db_session,
    ):
        db_session.add_all([self._metric(i) for i in range(35)])
        db_session.commit()

        monkeypatch.setattr(
            tasks.pickle,
            "dumps",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("pickle error")),
        )

        result = tasks.train_model_task(
            24,
            "",
        )

        assert result["status"] == "error"
        assert "pickle error" in result["message"]
