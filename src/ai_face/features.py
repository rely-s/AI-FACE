"""Session-level statistical feature aggregation for distress classification."""

from typing import Sequence

import numpy as np

from ai_face.constants import FROZEN_BLENDSHAPE_NAMES
from ai_face.models import SlotRecord

# 55 base facial dimensions (52 blendshapes + yaw, pitch, roll)
FEATURE_DIMENSIONS: tuple[str, ...] = FROZEN_BLENDSHAPE_NAMES + ("yaw", "pitch", "roll")


def get_feature_names() -> list[str]:
    """Generate exact list of 220 aggregated feature column names."""
    names = []
    for dim in FEATURE_DIMENSIONS:
        names.append(f"{dim}_median")
        names.append(f"{dim}_iqr")
        names.append(f"{dim}_std")
        names.append(f"{dim}_vel_median")
    return names


def extract_session_feature_matrix(slots: Sequence[SlotRecord]) -> np.ndarray:
    """Convert valid slots in a session into a (N_valid, 55) numeric matrix."""
    valid_slots = [
        s for s in slots if (s.valid and s.blendshapes is not None and s.pose_deg is not None)
    ]
    if not valid_slots:
        return np.empty((0, len(FEATURE_DIMENSIONS)), dtype=np.float64)

    rows = []
    for s in valid_slots:
        row = [s.blendshapes[name] for name in FROZEN_BLENDSHAPE_NAMES]
        row.append(s.pose_deg.yaw)
        row.append(s.pose_deg.pitch)
        row.append(s.pose_deg.roll)
        rows.append(row)

    return np.array(rows, dtype=np.float64)


def aggregate_session_features(slots: Sequence[SlotRecord]) -> np.ndarray | None:
    """Aggregate a session's slot features into a single 220-dimensional descriptor vector.

    Computes:
    - Median (central tendency)
    - Interquartile Range (IQR = Q75 - Q25, measuring movement span/variability)
    - Standard Deviation (spread)
    - Median Absolute First-Difference (dynamic velocity between consecutive valid slots)

    Returns None if fewer than 5 valid slots exist.
    """
    mat = extract_session_feature_matrix(slots)
    n_valid, n_dims = mat.shape

    if n_valid < 5:
        return None

    # 1. Median
    medians = np.median(mat, axis=0)

    # 2. IQR (Q75 - Q25)
    q75 = np.percentile(mat, 75, axis=0)
    q25 = np.percentile(mat, 25, axis=0)
    iqrs = q75 - q25

    # 3. Standard deviation
    stds = np.std(mat, axis=0)

    # 4. First differences (velocity)
    if n_valid > 1:
        diffs = np.abs(np.diff(mat, axis=0))
        vel_medians = np.median(diffs, axis=0)
    else:
        vel_medians = np.zeros(n_dims, dtype=np.float64)

    # Interleave statistics: [med_0, iqr_0, std_0, vel_0, med_1, ...]
    vector = []
    for d in range(n_dims):
        vector.extend([medians[d], iqrs[d], stds[d], vel_medians[d]])

    return np.array(vector, dtype=np.float64)
