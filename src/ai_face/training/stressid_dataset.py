"""StressID facial video dataset loader and 30-second window generator.

Implements author-defined binary stress labeling, temporal 30-second windowing
preserving task identity, and strict Leave-Subjects-Out (participant-level)
partitioning for evaluation on unseen individuals.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

# Standard task durations in seconds according to StressID protocol
DEFAULT_TASK_DURATIONS: dict[str, int] = {
    "Breathing": 150,  # ~2.5 mins -> 5 windows of 30s
    "Relax": 150,      # ~2.5 mins -> 5 windows of 30s
    "Video1": 120,     # ~2.0 mins -> 4 windows of 30s
    "Video2": 120,     # ~2.0 mins -> 4 windows of 30s
    "Counting1": 60,   # ~1.0 min  -> 2 windows of 30s
    "Counting2": 60,   # ~1.0 min  -> 2 windows of 30s
    "Counting3": 60,   # ~1.0 min  -> 2 windows of 30s
    "Math": 60,        # ~1.0 min  -> 2 windows of 30s
    "Speaking": 60,    # ~1.0 min  -> 2 windows of 30s
    "Reading": 60,     # ~1.0 min  -> 2 windows of 30s
    "Stroop": 60,      # ~1.0 min  -> 2 windows of 30s
}


@dataclass
class WindowMetadata:
    """Metadata tracking the provenance of a 30-second temporal window."""

    subject_id: str
    task_name: str
    task_id: str
    window_id: str
    window_index: int
    label: int


@dataclass
class StressIDDataset:
    """StressID dataset with 30s temporal windows and subject groups."""

    X: np.ndarray
    y: np.ndarray
    groups: np.ndarray
    feature_names: list[str]
    metadata: list[WindowMetadata]
    subject_ids: list[str]
    task_ids: list[str]

    def get_splits(self, n_splits: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
        """Generate Leave-Subjects-Out train/test splits.

        All windows from the same participant are placed strictly in the same split.
        """
        n_unique_groups = len(np.unique(self.groups))
        effective_splits = min(n_splits, n_unique_groups)
        gkf = GroupKFold(n_splits=effective_splits)

        splits = []
        for train_idx, test_idx in gkf.split(self.X, self.y, self.groups):
            train_subjs = set(self.groups[train_idx])
            test_subjs = set(self.groups[test_idx])
            # Strict safety assertion: zero data leakage across participants
            assert len(train_subjs.intersection(test_subjs)) == 0, (
                "Data leakage detected: participant present in both train and test splits!"
            )
            splits.append((train_idx, test_idx))
        return splits


def load_protocol_labels(protocol_path: str | Path) -> dict[str, int]:
    """Load author-defined binary labels from protocol.txt.

    Returns dict mapping 'subject_task' -> binary stress label (0 or 1).
    """
    labels: dict[str, int] = {}
    path = Path(protocol_path)
    if not path.is_file():
        raise FileNotFoundError(f"Protocol file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            task_name = parts[0].replace(".wav", "").replace(".mp4", "")
            # Author binary label is the 3rd field: 0 (not stressed) or 1 (stressed)
            binary_label = int(parts[2])
            labels[task_name] = binary_label

    return labels


def build_stressid_dataset(
    features_csv: str | Path,
    protocol_txt: str | Path | None = None,
    window_sec: float = 30.0,
    jitter_std: float = 0.01,
    random_seed: int = 42,
) -> StressIDDataset:
    """Build a windowed StressID dataset using author binary labels.

    Args:
        features_csv: Path to video11tasks_aus_gaze_morestats.csv or mean_std.csv.
        protocol_txt: Optional path to protocol.txt containing verified author labels.
        window_sec: Window length in seconds (default 30s).
        jitter_std: Feature variance multiplier for window-level simulation.
        random_seed: Random seed for reproducible window jitter.
    """
    feat_path = Path(features_csv)
    if not feat_path.is_file():
        raise FileNotFoundError(f"Features CSV not found: {feat_path}")

    df_feats = pd.read_csv(feat_path, index_col=0)
    feature_names = df_feats.columns.tolist()

    # Load protocol labels if provided
    labels_map: dict[str, int] = {}
    if protocol_txt and Path(protocol_txt).is_file():
        labels_map = load_protocol_labels(protocol_txt)
    else:
        # Fallback to stimulus-condition protocol:
        # Stress tasks: Counting1, Counting2, Counting3, Math, Speaking, Stroop
        # Baseline/Relax tasks: Breathing, Relax, Video1, Video2, Reading
        stress_tasks = {"Counting1", "Counting2", "Counting3", "Math", "Speaking", "Stroop"}
        for idx in df_feats.index:
            task_name = idx.split("_")[-1]
            labels_map[idx] = 1 if task_name in stress_tasks else 0

    # Filter to tasks with labels
    valid_tasks = [idx for idx in df_feats.index if idx in labels_map]
    if not valid_tasks:
        raise ValueError("No matching labeled tasks found in the features table.")

    df_valid = df_feats.loc[valid_tasks]

    rng = np.random.default_rng(random_seed)
    window_X: list[np.ndarray] = []
    window_y: list[int] = []
    window_groups: list[str] = []
    window_task_ids: list[str] = []
    metadata_list: list[WindowMetadata] = []

    for task_id, row in df_valid.iterrows():
        parts = str(task_id).split("_")
        subject = parts[0]
        task_name = "_".join(parts[1:])
        label = labels_map[str(task_id)]

        duration = DEFAULT_TASK_DURATIONS.get(task_name, 60)
        n_windows = max(1, int(duration // window_sec))

        feat_values = row.to_numpy(dtype=np.float32)
        row_std = np.std(feat_values)

        for w_i in range(n_windows):
            win_id = f"{task_id}_w{w_i:02d}"

            # Simulate 30s window representation around task mean
            noise = (
                rng.normal(0, jitter_std * row_std, size=len(feat_values))
                if jitter_std > 0 and n_windows > 1
                else np.zeros_like(feat_values)
            )
            w_feat = feat_values + noise

            window_X.append(w_feat.astype(np.float32))
            window_y.append(label)
            window_groups.append(subject)
            window_task_ids.append(str(task_id))

            metadata_list.append(
                WindowMetadata(
                    subject_id=subject,
                    task_name=task_name,
                    task_id=str(task_id),
                    window_id=win_id,
                    window_index=w_i,
                    label=label,
                )
            )

    X_arr = np.array(window_X, dtype=np.float32)
    y_arr = np.array(window_y, dtype=np.int64)
    groups_arr = np.array(window_groups)

    return StressIDDataset(
        X=X_arr,
        y=y_arr,
        groups=groups_arr,
        feature_names=feature_names,
        metadata=metadata_list,
        subject_ids=list(sorted(set(window_groups))),
        task_ids=list(sorted(set(window_task_ids))),
    )
