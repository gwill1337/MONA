from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

import mona_core.ml as ml
from mona_core.db import Anomaly, Metric

STEP = timedelta(seconds=15)


# ─── _describe_reason ───────────────────────────────────────────────────────
def _reason(*args: float) -> str:
    """_describe_reason() that must return a reason (narrows `str | None` for type checkers)."""
    result = ml._describe_reason(*args)
    assert result is not None
    return result


class TestDescribeReason:
    """_describe_reason(cpu, ram, cpu_d1, ram_d1, cpu_d5, ram_d5) -> str | None"""

    def test_high_cpu_reason(self):
        result = _reason(90, 30, 0, 0, 0, 0)

        assert result == "high cpu=90.0%"

    def test_high_ram_reason(self):
        result = _reason(30, 90, 0, 0, 0, 0)

        assert result == "high ram=90.0%"

    def test_threshold_is_exclusive(self):
        assert ml._describe_reason(85, 85, 0, 0, 0, 0) is None
        assert "high cpu" in _reason(85.1, 50, 0, 0, 0, 0)

    def test_cpu_jump_up(self):
        result = _reason(50, 50, 30, 0, 0, 0)

        assert "sudden cpu change" in result
        assert "▲30.0%" in result

    def test_cpu_jump_down(self):
        result = _reason(50, 50, -25, 0, 0, 0)

        assert "sudden cpu change" in result
        assert "▼25.0%" in result

    def test_ram_jump(self):
        result = _reason(50, 50, 0, 20, 0, 0)

        assert "sudden ram change ▲20.0%" in result

    def test_change_over_five_samples(self):
        result = _reason(50, 50, 0, 0, 35, -25)

        assert "cpu changed by +35.0% over 5 samples" in result
        assert "ram changed by -25.0% over 5 samples" in result

    def test_multiple_reasons_are_joined(self):
        result = _reason(90, 90, 0, 0, 0, 0)

        assert result == "high cpu=90.0%, high ram=90.0%"

    def test_returns_none_when_nothing_stands_out(self):
        # The "combined anomaly" fallback now lives in detect_anomalies().
        assert ml._describe_reason(50, 50, 1, 1, 1, 1) is None


# ─── _load_user_model ───────────────────────────────────────────────────────
class TestLoadUserModel:
    def test_no_model_returns_none(self, db_session):
        model, scaler = ml._load_user_model(db_session)

        assert model is None
        assert scaler is None

    def test_loads_active_model(
        self, db_session, make_trained_model, trained_model_bytes
    ):
        make_trained_model(model_data=trained_model_bytes)

        model, scaler = ml._load_user_model(db_session)

        assert model is not None
        assert scaler is not None
        assert hasattr(model, "predict")
        assert hasattr(scaler, "transform")

    def test_inactive_model_not_loaded(
        self, db_session, make_trained_model, trained_model_bytes
    ):
        make_trained_model(model_data=trained_model_bytes, is_active=False)

        model, scaler = ml._load_user_model(db_session)

        assert model is None
        assert scaler is None

    def test_corrupt_model_falls_back_to_none(self, db_session, make_trained_model):
        make_trained_model(model_data=b"definitely not a model")

        model, scaler = ml._load_user_model(db_session)

        assert model is None
        assert scaler is None


# ─── detect_anomalies ───────────────────────────────────────────────────────
class FakeScaler:
    def transform(self, X):
        return X


class FakeModel:
    def __init__(self, prediction, score):
        self._prediction = prediction
        self._score = score

    def predict(self, X):
        return np.full(len(X), self._prediction)

    def decision_function(self, X):
        return np.full(len(X), self._score)


@pytest.fixture()
def fake_detector(monkeypatch):
    """Replace ml.fit_detector (used in auto-mode) with a deterministic fake.

    By default every checked point is predicted as an anomaly with a score
    safely below settings.score_threshold.
    """

    def _install(prediction=-1, score_offset=-1.0):
        model = FakeModel(prediction, ml.settings.score_threshold + score_offset)
        monkeypatch.setattr(ml, "fit_detector", lambda x: (model, FakeScaler()))
        return model

    return _install


def _seed(
    db,
    *,
    cpu,
    ram,
    device="srv-1",
    recent=3,
    history=None,
    history_cpu=None,
    history_ram=None,
):
    """Insert a flat metric series for one device.

    * `recent` points inside the detection lookback window (checked),
    * `history` older points outside the window (training data in auto-mode),
    flat at cpu/ram (history_cpu/history_ram override the history level), so the
    delta features stay at zero. Recent and history are > MAX_TRAINING_GAP_SECONDS
    apart, so they are separate segments.
    """
    if history is None:
        history = ml.settings.min_points + 10
    history_cpu = cpu if history_cpu is None else history_cpu
    history_ram = ram if history_ram is None else history_ram

    now = datetime.now(UTC)
    history_start = now - timedelta(minutes=ml.DETECTION_LOOKBACK_MINUTES + 1)

    recent_rows = [
        Metric(cpu=cpu, ram=ram, device=device, timestamp=now - STEP * i)
        for i in range(recent)
    ]
    history_rows = [
        Metric(
            cpu=history_cpu,
            ram=history_ram,
            device=device,
            timestamp=history_start - STEP * i,
        )
        for i in range(history)
    ]
    db.add_all(recent_rows + history_rows)
    db.commit()
    return recent_rows, history_rows


class TestDetectAnomalies:
    def test_skip_device_with_not_enough_points(self, db_session):
        _seed(db_session, cpu=50, ram=40, recent=ml.settings.min_points - 1, history=0)

        result = ml.detect_anomalies()

        assert result == {
            "status": "ok",
            "mode": "auto",
            "devices_checked": 0,
            "anomalies_found": 0,
        }

    def test_auto_mode_detects_anomaly(self, db_session, fake_detector):
        fake_detector()
        _seed(db_session, cpu=95, ram=40, recent=3)

        result = ml.detect_anomalies()

        assert result["status"] == "ok"
        assert result["mode"] == "auto"
        assert result["devices_checked"] == 1
        assert result["anomalies_found"] == 3

        saved = db_session.query(Anomaly).all()
        assert len(saved) == 3
        assert all(a.device == "srv-1" for a in saved)
        assert all("high cpu=95.0%" in a.reason for a in saved)

    def test_normal_predictions_create_no_anomalies(self, db_session, fake_detector):
        fake_detector(prediction=1, score_offset=1.0)
        _seed(db_session, cpu=95, ram=40, recent=3)

        result = ml.detect_anomalies()

        assert result["devices_checked"] == 1
        assert result["anomalies_found"] == 0
        assert db_session.query(Anomaly).count() == 0

    def test_score_above_threshold_is_ignored(self, db_session, fake_detector):
        # predicted -1, but not "anomalous enough" for settings.score_threshold
        fake_detector(prediction=-1, score_offset=1.0)
        _seed(db_session, cpu=95, ram=40, recent=3)

        result = ml.detect_anomalies()

        assert result["anomalies_found"] == 0

    def test_weak_combined_anomaly_is_skipped(self, db_session, fake_detector):
        fake_detector()
        # no single factor stands out, and both metrics are below WEAK_COMBINED_LIMIT
        _seed(db_session, cpu=70, ram=70, recent=3)

        result = ml.detect_anomalies()

        assert result["devices_checked"] == 1
        assert result["anomalies_found"] == 0

    def test_combined_anomaly_reason(self, db_session, fake_detector):
        fake_detector()
        # >= WEAK_COMBINED_LIMIT (80) but not "high" (> 85): falls back to "combined"
        _seed(db_session, cpu=82, ram=50, recent=1)

        result = ml.detect_anomalies()

        assert result["anomalies_found"] == 1
        anomaly = db_session.query(Anomaly).one()
        assert anomaly.reason == "combined anomaly (cpu=82.0%, ram=50.0%)"

    def test_existing_anomaly_not_created_again(self, db_session, fake_detector):
        fake_detector()
        # Low-load history + high-load recent points: the known anomaly excludes
        # only the recent (high-load) episode from training, history stays usable.
        recent_rows, _ = _seed(
            db_session, cpu=95, ram=40, history_cpu=30, history_ram=40, recent=3
        )

        already_saved = recent_rows[0]
        db_session.add(
            Anomaly(
                metric_id=already_saved.id,
                cpu=95,
                ram=40,
                timestamp=already_saved.timestamp,
                reason="old",
                score=-1,
                device="srv-1",
            )
        )
        db_session.commit()

        result = ml.detect_anomalies()

        assert result["anomalies_found"] == 2  # only the two new ones
        assert db_session.query(Anomaly).count() == 3
        old = db_session.query(Anomaly).filter_by(metric_id=already_saved.id).one()
        assert old.reason == "old"

    def test_auto_mode_skips_device_when_known_anomaly_excludes_all_history(
        self, db_session, fake_detector
    ):
        fake_detector()
        # Flat 95% load everywhere: the whole series is one high-load episode that
        # touches the known anomaly, so known_anomaly_mask removes all training data.
        recent_rows, _ = _seed(db_session, cpu=95, ram=40, recent=3)
        db_session.add(
            Anomaly(
                metric_id=recent_rows[0].id,
                cpu=95,
                ram=40,
                timestamp=recent_rows[0].timestamp,
                reason="old",
                score=-1,
                device="srv-1",
            )
        )
        db_session.commit()

        result = ml.detect_anomalies()

        assert result["status"] == "ok"
        assert result["devices_checked"] == 0
        assert result["anomalies_found"] == 0
        assert db_session.query(Anomaly).count() == 1

    def test_user_model_mode(self, db_session, make_trained_model, trained_model_bytes):
        _seed(db_session, cpu=50, ram=40)
        make_trained_model(model_data=trained_model_bytes, points_count=200)

        result = ml.detect_anomalies()

        assert result["status"] == "ok"
        assert result["mode"] == "user_model"
        assert result["devices_checked"] == 1

    def test_corrupt_user_model_falls_back_to_auto_mode(
        self, db_session, make_trained_model, fake_detector
    ):
        fake_detector()
        _seed(db_session, cpu=95, ram=40)
        make_trained_model(model_data=b"definitely not a model")

        result = ml.detect_anomalies()

        assert result["status"] == "ok"
        assert result["mode"] == "auto"

    def test_error_returns_error_status(self, monkeypatch):
        def boom(db):
            raise Exception("broken")

        monkeypatch.setattr(ml, "_load_user_model", boom)

        result = ml.detect_anomalies()

        assert result["status"] == "error"
        assert "Server error" in result["error"]