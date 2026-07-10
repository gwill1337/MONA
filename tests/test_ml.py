from datetime import UTC, datetime, timedelta

import numpy as np

import mona_core.ml as ml
from mona_core.db import Anomaly, Metric, TrainedModel


class FakeUserModel:
    def predict(self, X):  # noqa: E402
        return np.ones(len(X))  # noqa: E402

    def decision_function(self, X):  # noqa: E402
        return np.zeros(len(X))  # noqa: E402


class FakeUserScaler:
    def transform(self, X):  # noqa: E402
        return X  # noqa: E402


class TestBuildFeatures:
    def test_build_features_shape(self):
        rows = [
            Metric(cpu=10, ram=20),
            Metric(cpu=20, ram=30),
            Metric(cpu=30, ram=40),
            Metric(cpu=40, ram=50),
            Metric(cpu=50, ram=60),
            Metric(cpu=60, ram=70),
        ]

        result = ml._build_features(rows)

        assert result.shape == (6, 6)

    def test_first_row_has_zero_deltas(self):
        rows = [
            Metric(cpu=10, ram=20),
            Metric(cpu=20, ram=30),
            Metric(cpu=30, ram=40),
            Metric(cpu=40, ram=50),
            Metric(cpu=50, ram=60),
            Metric(cpu=70, ram=80),
        ]

        result = ml._build_features(rows)

        assert list(result[0]) == [
            10,
            20,
            0,
            0,
            0,
            0,
        ]

    def test_delta_calculation(self):
        rows = [
            Metric(cpu=10, ram=10),
            Metric(cpu=30, ram=40),
            Metric(cpu=40, ram=50),
            Metric(cpu=50, ram=60),
            Metric(cpu=60, ram=70),
            Metric(cpu=80, ram=90),
        ]

        result = ml._build_features(rows)

        assert result[1][2] == 20
        assert result[1][3] == 30

        assert result[5][4] == 70
        assert result[5][5] == 80


class TestDescribeReason:
    def test_high_cpu_reason(self):
        row = Metric(
            cpu=90,
            ram=30,
        )

        result = ml._describe_reason(
            row,
            0,
            0,
            0,
            0,
        )

        assert "high cpu" in result

    def test_high_ram_reason(self):
        row = Metric(
            cpu=30,
            ram=90,
        )

        result = ml._describe_reason(
            row,
            0,
            0,
            0,
            0,
        )

        assert "high ram" in result

    def test_cpu_jump_reason(self):
        row = Metric(
            cpu=50,
            ram=50,
        )

        result = ml._describe_reason(
            row,
            30,
            0,
            0,
            0,
        )

        assert "sudden cpu change" in result

    def test_combined_reason(self):
        row = Metric(
            cpu=50,
            ram=50,
        )

        result = ml._describe_reason(
            row,
            1,
            1,
            1,
            1,
        )

        assert "combined anomaly" in result


class TestLoadUserModel:
    def test_no_model_returns_none(
        self,
        db_session,
    ):
        model, scaler = ml._load_user_model(db_session)

        assert model is None
        assert scaler is None

    def test_loads_latest_model(
        self,
        db_session,
    ):
        fake_model = object()
        fake_scaler = object()

        import pickle

        record = TrainedModel(
            model_data=pickle.dumps(
                (
                    fake_model,
                    fake_scaler,
                )
            ),
            trained_by="user",
            points_count=100,
            period_from=datetime.now(UTC),
            period_to=datetime.now(UTC),
        )

        db_session.add(record)
        db_session.commit()

        model, scaler = ml._load_user_model(db_session)

        assert model is not None
        assert scaler is not None


class TestDetectAnomalies:
    def _metric(
        self,
        idx,
        device="srv-1",
    ):
        return Metric(
            cpu=50 + idx,
            ram=40 + idx,
            device=device,
            timestamp=datetime.now(UTC) - timedelta(seconds=idx),
        )

    def test_skip_device_with_not_enough_points(
        self,
        db_session,
    ):
        db_session.add_all([self._metric(i) for i in range(10)])

        db_session.commit()

        result = ml.detect_anomalies()

        assert result["status"] == "ok"
        assert result["anomalies_found"] == 0

    def test_auto_mode_detects_anomaly(
        self,
        db_session,
        monkeypatch,
    ):

        db_session.add_all([self._metric(i) for i in range(40)])

        db_session.commit()

        class FakeModel:
            def fit_predict(self, X):  # noqa: E402
                result = np.ones(len(X))  # noqa: E402
                result[-1] = -1
                return result

            def decision_function(self, X):  # noqa: E402
                result = np.zeros(len(X))  # noqa: E402
                result[-1] = -1
                return result

        monkeypatch.setattr(
            ml,
            "IsolationForest",
            lambda **kwargs: FakeModel(),
        )

        result = ml.detect_anomalies()

        assert result["status"] == "ok"
        assert result["mode"] == "auto"

    def test_existing_anomaly_not_created_again(
        self,
        db_session,
        monkeypatch,
    ):

        metrics = [self._metric(i) for i in range(40)]

        db_session.add_all(metrics)
        db_session.commit()

        db_session.add(
            Anomaly(
                metric_id=metrics[-1].id,
                cpu=90,
                ram=90,
                timestamp=metrics[-1].timestamp,
                reason="old",
                score=-1,
                device="srv-1",
            )
        )

        db_session.commit()

        class FakeModel:
            def fit_predict(self, X):  # noqa: E402
                result = np.ones(len(X))  # noqa: E402
                result[-1] = -1
                return result

            def decision_function(self, X):  # noqa: E402
                result = np.zeros(len(X))  # noqa: E402
                result[-1] = -1
                return result

        monkeypatch.setattr(
            ml,
            "IsolationForest",
            lambda **x: FakeModel(),
        )

        ml.detect_anomalies()

        assert db_session.query(Anomaly).count() == 1

    def test_user_model_mode(
        self,
        db_session,
        monkeypatch,
    ):
        db_session.add_all([self._metric(i) for i in range(40)])

        db_session.commit()

        import pickle

        db_session.add(
            TrainedModel(
                model_data=pickle.dumps(
                    (
                        FakeUserModel(),
                        FakeUserScaler(),
                    )
                ),
                trained_by="user",
                points_count=40,
                period_from=datetime.now(UTC),
                period_to=datetime.now(UTC),
            )
        )

        db_session.commit()

        result = ml.detect_anomalies()

        assert result["mode"] == "user_model"

    def test_error_returns_error_status(
        self,
        monkeypatch,
    ):

        monkeypatch.setattr(
            ml,
            "_load_user_model",
            lambda db: (_ for _ in ()).throw(Exception("broken")),
        )

        result = ml.detect_anomalies()

        assert result["status"] == "error"
        assert "broken" in result["error"]
