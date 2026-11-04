"""Shared feature engineering and training-data cleaning for MONA anomaly models."""

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime

import numpy as np
import skops.io as sio
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from mona_core import model_registry
from mona_core.config import settings

ANOMALY_EXCLUSION_BEFORE_MINUTES = 5
ANOMALY_EXCLUSION_AFTER_MINUTES = 5
HIGH_USAGE_EPISODE_THRESHOLD = 80.0
MAX_TRAINING_GAP_SECONDS = 90
MIN_BLOCK_POINTS = 5
OFFLINE_SAMPLE_LIMIT = 0.1
DELTA_LAG = 5
FEATURE_COUNT = 6
TRUSTED_TYPE_PREFIXES = ("sklearn.", "numpy.")


def as_utc(value: datetime) -> datetime:
    """Treat naive timestamps as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_epoch(values: Iterable[datetime]) -> np.ndarray:
    """Convert timestamps to UTC epoch seconds."""
    return np.asarray([as_utc(value).timestamp() for value in values], dtype=float)


def build_features(cpu: np.ndarray, ram: np.ndarray) -> np.ndarray:
    """Build the (N, 6) feature matrix for one contiguous series."""
    size = len(cpu)
    if size == 0:
        return np.empty((0, FEATURE_COUNT), dtype=float)

    cpu_d1 = np.zeros(size)
    ram_d1 = np.zeros(size)
    cpu_d5 = np.zeros(size)
    ram_d5 = np.zeros(size)

    cpu_d1[1:] = np.diff(cpu)
    ram_d1[1:] = np.diff(ram)
    cpu_d5[DELTA_LAG:] = cpu[DELTA_LAG:] - cpu[:-DELTA_LAG]
    ram_d5[DELTA_LAG:] = ram[DELTA_LAG:] - ram[:-DELTA_LAG]

    return np.column_stack((cpu, ram, cpu_d1, ram_d1, cpu_d5, ram_d5))


def offline_mask(cpu: np.ndarray, ram: np.ndarray) -> np.ndarray:
    """Rows where both metrics are zero (offline device or missing series)."""
    return (cpu <= OFFLINE_SAMPLE_LIMIT) & (ram <= OFFLINE_SAMPLE_LIMIT)


def segment_bounds(ts: np.ndarray, offline: np.ndarray) -> list[tuple[int, int]]:
    """Split into [start, end) ranges at time gaps and offline/online switches."""
    if len(ts) == 0:
        return []
    gaps = np.diff(ts) > MAX_TRAINING_GAP_SECONDS
    switches = offline[1:] != offline[:-1]
    breaks = np.flatnonzero(gaps | switches) + 1
    starts = np.concatenate(([0], breaks))
    ends = np.concatenate((breaks, [len(ts)]))
    return list(zip(starts.tolist(), ends.tolist(), strict=True))


def build_features_segmented(
    ts: np.ndarray,
    cpu: np.ndarray,
    ram: np.ndarray,
) -> np.ndarray:
    """Build features for every row without deltas crossing gaps or offline periods."""
    features = np.empty((len(ts), FEATURE_COUNT), dtype=float)
    for start, end in segment_bounds(ts, offline_mask(cpu, ram)):
        features[start:end] = build_features(cpu[start:end], ram[start:end])
    return features


def known_anomaly_mask(
    ts: np.ndarray,
    cpu: np.ndarray,
    ram: np.ndarray,
    anomaly_times: Sequence[datetime],
) -> np.ndarray:
    """Mask rows around known anomalies and their contiguous high-load episodes."""
    size = len(ts)
    excluded = np.zeros(size, dtype=bool)
    times = to_epoch(value for value in anomaly_times if value is not None)
    if size == 0 or times.size == 0:
        return excluded

    starts = np.searchsorted(
        ts, times - ANOMALY_EXCLUSION_BEFORE_MINUTES * 60, side="left"
    )
    ends = np.searchsorted(
        ts, times + ANOMALY_EXCLUSION_AFTER_MINUTES * 60, side="right"
    )
    for start, end in zip(starts, ends, strict=True):
        excluded[start:end] = True

    position = np.searchsorted(ts, times, side="left")
    right = np.clip(position, 0, size - 1)
    left = np.clip(position - 1, 0, size - 1)
    nearest = np.where(
        np.abs(ts[left] - times) <= np.abs(ts[right] - times), left, right
    )
    close = np.abs(ts[nearest] - times) <= MAX_TRAINING_GAP_SECONDS

    high = (cpu >= HIGH_USAGE_EPISODE_THRESHOLD) | (ram >= HIGH_USAGE_EPISODE_THRESHOLD)
    run_bounds = np.concatenate(
        ([0], np.flatnonzero(np.diff(high.astype(np.int8))) + 1, [size])
    )
    for index in np.unique(nearest[close & high[nearest]]):
        run = np.searchsorted(run_bounds, index, side="right") - 1
        excluded[run_bounds[run] : run_bounds[run + 1]] = True

    return excluded


def training_blocks(
    ts: np.ndarray,
    cpu: np.ndarray,
    ram: np.ndarray,
    keep: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build features from kept rows; return them with the source row indices."""
    indices = np.flatnonzero(keep)
    kept_ts, kept_cpu, kept_ram = ts[indices], cpu[indices], ram[indices]

    blocks: list[np.ndarray] = []
    used: list[np.ndarray] = []
    for start, end in segment_bounds(kept_ts, offline_mask(kept_cpu, kept_ram)):
        if end - start >= MIN_BLOCK_POINTS:
            blocks.append(build_features(kept_cpu[start:end], kept_ram[start:end]))
            used.append(indices[start:end])

    if not blocks:
        return np.empty((0, FEATURE_COUNT), dtype=float), np.empty(0, dtype=int)
    return np.vstack(blocks), np.concatenate(used)


def fit_detector(features: np.ndarray) -> tuple[IsolationForest, StandardScaler]:
    """Fit the scaler and Isolation Forest on a training matrix."""
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    model = IsolationForest(
        n_estimators=200,
        contamination=settings.contamination,
        random_state=42,
    )
    model.fit(scaled)
    return model, scaler


def dump_model(model: IsolationForest, scaler: StandardScaler) -> bytes:
    """Serialize a (model, scaler) pair."""
    return sio.dumps((model, scaler))


def load_model(data: bytes) -> tuple[IsolationForest, StandardScaler]:
    """Deserialize a (model, scaler) pair, trusting only sklearn and numpy types."""
    trusted = [
        name
        for name in sio.get_untrusted_types(data=data)
        if name.startswith(TRUSTED_TYPE_PREFIXES)
    ]
    return sio.loads(data, trusted=trusted)


def load_active_model(
    db: Session,
) -> tuple[IsolationForest, StandardScaler] | tuple[None, None]:
    """Load the active (model, scaler) pair, or (None, None) in auto-mode."""
    record = model_registry.get_active(db)
    if record is None:
        return None, None
    return load_model(record.model_data)
