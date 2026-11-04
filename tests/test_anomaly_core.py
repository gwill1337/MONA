from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest
import skops.io as sio
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from mona_core.anomaly_core import (
    FEATURE_COUNT,
    MAX_TRAINING_GAP_SECONDS,
    MIN_BLOCK_POINTS,
    as_utc,
    build_features,
    build_features_segmented,
    dump_model,
    fit_detector,
    known_anomaly_mask,
    load_active_model,
    load_model,
    offline_mask,
    segment_bounds,
    to_epoch,
    training_blocks,
)

T0 = 1_700_000_000.0  # integer epoch: keeps float arithmetic exact in the tests


def _ts(n, step=15.0):
    return T0 + np.arange(n) * step


def _dt(epoch):
    return datetime.fromtimestamp(float(epoch), UTC)


# ─── time helpers ───────────────────────────────────────────────────────────
class TestTimeHelpers:
    def test_as_utc_treats_naive_as_utc(self):
        result = as_utc(datetime(2026, 1, 1, 12, 0))

        assert result == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def test_as_utc_converts_other_timezones(self):
        plus_two = timezone(timedelta(hours=2))

        result = as_utc(datetime(2026, 1, 1, 14, 0, tzinfo=plus_two))

        assert result == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        assert result.utcoffset() == timedelta(0)

    def test_to_epoch_mixes_naive_and_aware(self):
        base = datetime(2026, 1, 1, tzinfo=UTC).timestamp()
        values = [datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, 0, 0, 30)]

        assert to_epoch(values).tolist() == [base, base + 30]

    def test_to_epoch_accepts_generator_and_empty_input(self):
        assert to_epoch(v for v in []).shape == (0,)


# ─── features ───────────────────────────────────────────────────────────────
class TestBuildFeatures:
    """Columns: [cpu, ram, cpu_d1, ram_d1, cpu_d5, ram_d5]."""

    def test_empty_series(self):
        x = build_features(np.array([]), np.array([]))

        assert x.shape == (0, FEATURE_COUNT)

    def test_shape(self):
        x = build_features(np.arange(6.0), np.arange(6.0))

        assert x.shape == (6, FEATURE_COUNT)

    def test_first_row_has_zero_deltas(self):
        x = build_features(np.array([10.0, 20, 30]), np.array([20.0, 30, 40]))

        assert list(x[0]) == [10, 20, 0, 0, 0, 0]

    def test_one_step_deltas(self):
        x = build_features(
            np.array([10.0, 15, 18, 22, 30, 45]),
            np.array([20.0, 30, 35, 40, 45, 55]),
        )

        assert x[1][2] == 5
        assert x[1][3] == 10
        assert x[2][2] == 3

    def test_five_step_deltas_start_at_sixth_row(self):
        x = build_features(
            np.array([10.0, 15, 18, 22, 30, 45]),
            np.array([20.0, 30, 35, 40, 45, 55]),
        )

        assert (x[:5, 4:6] == 0).all()
        assert x[5][4] == 35  # 45 - 10
        assert x[5][5] == 35  # 55 - 20


class TestOfflineMask:
    def test_both_metrics_near_zero_is_offline(self):
        cpu = np.array([0.0, 0.1, 0.0, 50.0, 0.0])
        ram = np.array([0.0, 0.1, 30.0, 40.0, 0.2])

        assert offline_mask(cpu, ram).tolist() == [True, True, False, False, False]


class TestSegmentBounds:
    def test_empty(self):
        assert segment_bounds(np.array([]), np.array([], dtype=bool)) == []

    def test_single_segment(self):
        ts = _ts(5)

        assert segment_bounds(ts, np.zeros(5, dtype=bool)) == [(0, 5)]

    def test_splits_on_time_gap(self):
        ts = np.array([0, 15, 30, 200, 215, 230], dtype=float)

        assert segment_bounds(ts, np.zeros(6, dtype=bool)) == [(0, 3), (3, 6)]

    def test_gap_equal_to_limit_does_not_split(self):
        ts = np.array([0.0, float(MAX_TRAINING_GAP_SECONDS)])

        assert segment_bounds(ts, np.zeros(2, dtype=bool)) == [(0, 2)]

    def test_splits_on_offline_switch(self):
        offline = np.array([False, False, True, True, False, False])

        assert segment_bounds(_ts(6), offline) == [(0, 2), (2, 4), (4, 6)]


class TestBuildFeaturesSegmented:
    def test_matches_plain_features_for_contiguous_series(self):
        cpu = np.array([10.0, 15, 18, 22, 30, 45])
        ram = np.array([20.0, 30, 35, 40, 45, 55])

        segmented = build_features_segmented(_ts(6), cpu, ram)

        assert np.array_equal(segmented, build_features(cpu, ram))

    def test_deltas_do_not_cross_time_gaps(self):
        ts = np.array([0, 15, 30, 300, 315, 330], dtype=float)
        cpu = np.array([10.0, 20, 30, 40, 50, 60])
        ram = np.array([10.0, 20, 30, 40, 50, 60])

        x = build_features_segmented(ts, cpu, ram)

        assert list(x[3]) == [40, 40, 0, 0, 0, 0]  # first row after the gap
        assert x[4][2] == 10

    def test_deltas_do_not_cross_offline_periods(self):
        cpu = np.array([10.0, 20, 0, 0, 30, 40])
        ram = np.array([10.0, 20, 0, 0, 30, 40])

        x = build_features_segmented(_ts(6), cpu, ram)

        assert x[1][2] == 10
        assert list(x[2]) == [0, 0, 0, 0, 0, 0]
        assert list(x[4]) == [30, 30, 0, 0, 0, 0]  # back online: no jump from 0
        assert x[5][2] == 10


# ─── known anomaly exclusion ────────────────────────────────────────────────
def _series(n=31, step=60.0, cpu=30.0, ram=30.0):
    ts = T0 + np.arange(n) * step
    return ts, np.full(n, cpu), np.full(n, ram)


def _excluded(mask):
    return np.flatnonzero(mask).tolist()


class TestKnownAnomalyMask:
    def test_no_anomalies_excludes_nothing(self):
        ts, cpu, ram = _series()

        assert not known_anomaly_mask(ts, cpu, ram, []).any()

    def test_none_timestamps_are_ignored(self):
        ts, cpu, ram = _series()

        # None is not allowed by the type hint, but the DB column may return it
        mask = known_anomaly_mask(ts, cpu, ram, [None])  # type: ignore[arg-type]

        assert not mask.any()

    def test_empty_series(self):
        empty = np.array([])

        mask = known_anomaly_mask(empty, empty, empty, [_dt(T0)])

        assert mask.shape == (0,)

    def test_excludes_five_minutes_around_anomaly(self):
        ts, cpu, ram = _series()

        mask = known_anomaly_mask(ts, cpu, ram, [_dt(ts[15])])

        # +-5 min at 1 point/min, boundaries included
        assert _excluded(mask) == list(range(10, 21))

    def test_anomaly_between_samples(self):
        ts, cpu, ram = _series()

        mask = known_anomaly_mask(ts, cpu, ram, [_dt(ts[15] + 30)])

        assert _excluded(mask) == list(range(11, 21))

    def test_naive_timestamps_are_treated_as_utc(self):
        ts, cpu, ram = _series()
        naive = _dt(ts[15]).replace(tzinfo=None)

        mask = known_anomaly_mask(ts, cpu, ram, [naive])

        assert _excluded(mask) == list(range(10, 21))

    def test_high_cpu_episode_is_excluded_entirely(self):
        ts, cpu, ram = _series()
        cpu[8:23] = 90  # episode runs past the +-5 min window
        cpu[25:28] = 90  # separate episode, must stay

        mask = known_anomaly_mask(ts, cpu, ram, [_dt(ts[15])])

        assert _excluded(mask) == list(range(8, 23))

    def test_high_ram_episode_is_excluded_too(self):
        ts, cpu, ram = _series()
        ram[8:23] = 85

        mask = known_anomaly_mask(ts, cpu, ram, [_dt(ts[15])])

        assert _excluded(mask) == list(range(8, 23))

    def test_anomaly_far_from_any_sample_does_not_extend_episode(self):
        ts, cpu, ram = _series()
        cpu[-5:] = 90
        anomaly_time = _dt(ts[-1] + 600)  # 10 min after the last sample

        mask = known_anomaly_mask(ts, cpu, ram, [anomaly_time])

        assert not mask.any()


# ─── training blocks ────────────────────────────────────────────────────────
class TestTrainingBlocks:
    def test_returns_features_and_source_indices(self):
        ts = _ts(10)
        cpu = 10.0 + np.arange(10)
        ram = cpu + 5

        features, used = training_blocks(ts, cpu, ram, np.ones(10, dtype=bool))

        assert features.shape == (10, FEATURE_COUNT)
        assert used.tolist() == list(range(10))

    def test_drops_blocks_shorter_than_minimum(self):
        short = np.array([0.0, 15, 30])  # 3 < MIN_BLOCK_POINTS
        long_ = 300.0 + np.arange(10) * 15
        ts = np.concatenate((short, long_))
        cpu = np.full(len(ts), 40.0)
        ram = np.full(len(ts), 50.0)

        features, used = training_blocks(ts, cpu, ram, np.ones(len(ts), dtype=bool))

        assert len(short) < MIN_BLOCK_POINTS
        assert features.shape == (10, FEATURE_COUNT)
        assert used.tolist() == list(range(3, 13))

    def test_removed_rows_split_blocks_and_deltas_do_not_cross(self):
        ts = _ts(30)
        cpu = 10.0 + np.arange(30)
        ram = cpu + 5
        keep = np.ones(30, dtype=bool)
        keep[10:20] = False  # 11 * 15 s = 165 s gap between kept rows

        features, used = training_blocks(ts, cpu, ram, keep)

        assert used.tolist() == list(range(10)) + list(range(20, 30))
        assert list(features[10]) == [cpu[20], ram[20], 0, 0, 0, 0]

    def test_nothing_kept_returns_empty(self):
        ts = _ts(10)
        cpu = np.full(10, 40.0)

        features, used = training_blocks(ts, cpu, cpu, np.zeros(10, dtype=bool))

        assert features.shape == (0, FEATURE_COUNT)
        assert used.size == 0

    def test_too_few_points_returns_empty(self):
        ts = _ts(MIN_BLOCK_POINTS - 1)
        cpu = np.full(len(ts), 40.0)

        features, used = training_blocks(ts, cpu, cpu, np.ones(len(ts), dtype=bool))

        assert features.shape == (0, FEATURE_COUNT)
        assert used.size == 0


# ─── model fitting and (de)serialization ────────────────────────────────────
@pytest.fixture(scope="module")
def sample_features():
    rng = np.random.default_rng(1)
    n = 300
    return np.column_stack(
        [
            rng.normal(50, 5, n),
            rng.normal(40, 5, n),
            rng.normal(0, 1, (n, 4)),
        ]
    )


class _Untrusted:
    """A type outside the sklearn/numpy allow-list."""

    def __init__(self):
        self.value = 1


class TestFitDetector:
    def test_returns_fitted_model_and_scaler(self, sample_features):
        model, scaler = fit_detector(sample_features)

        assert isinstance(model, IsolationForest)
        assert isinstance(scaler, StandardScaler)
        assert scaler.mean_ is not None
        assert np.allclose(scaler.mean_, sample_features.mean(axis=0))

    def test_is_deterministic(self, sample_features):
        model_a, scaler_a = fit_detector(sample_features)
        model_b, scaler_b = fit_detector(sample_features)

        scores_a = model_a.decision_function(scaler_a.transform(sample_features))
        scores_b = model_b.decision_function(scaler_b.transform(sample_features))

        assert np.array_equal(scores_a, scores_b)

    def test_outlier_scores_lower_than_typical_points(self, sample_features):
        model, scaler = fit_detector(sample_features)
        outlier = np.array([[200.0, 200.0, 50.0, 50.0, 50.0, 50.0]])

        typical = model.decision_function(scaler.transform(sample_features))
        outlier_score = model.decision_function(scaler.transform(outlier))

        assert outlier_score[0] < np.median(typical)


class TestModelSerialization:
    def test_round_trip(self, sample_features):
        model, scaler = fit_detector(sample_features)

        loaded_model, loaded_scaler = load_model(dump_model(model, scaler))

        scaled = scaler.transform(sample_features)
        assert scaler.mean_ is not None
        assert loaded_scaler.mean_ is not None
        assert np.allclose(loaded_scaler.mean_, scaler.mean_)
        assert np.allclose(
            loaded_model.decision_function(scaled), model.decision_function(scaled)
        )

    def test_rejects_untrusted_types(self):
        data = sio.dumps((_Untrusted(), _Untrusted()))

        with pytest.raises(Exception):
            load_model(data)

    def test_rejects_garbage(self):
        with pytest.raises(Exception):
            load_model(b"definitely not a model")


class TestLoadActiveModel:
    def test_no_model_returns_none_pair(self, db_session):
        assert load_active_model(db_session) == (None, None)

    def test_loads_active_model(
        self, db_session, make_trained_model, trained_model_bytes
    ):
        make_trained_model(model_data=trained_model_bytes)

        model, scaler = load_active_model(db_session)

        assert isinstance(model, IsolationForest)
        assert isinstance(scaler, StandardScaler)

    def test_ignores_inactive_model(
        self, db_session, make_trained_model, trained_model_bytes
    ):
        make_trained_model(model_data=trained_model_bytes, is_active=False)

        assert load_active_model(db_session) == (None, None)

    def test_ignores_models_not_trained_by_user(
        self, db_session, make_trained_model, trained_model_bytes
    ):
        make_trained_model(model_data=trained_model_bytes, trained_by="auto")

        assert load_active_model(db_session) == (None, None)