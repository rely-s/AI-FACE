"""Unit and integration tests for StressID dataset loading, windowing, and model training."""

import json
from pathlib import Path

import pytest

from ai_face.training.stressid_dataset import (
    StressIDDataset,
    build_stressid_dataset,
    load_protocol_labels,
)
from ai_face.training.train_stressid import train_and_save_stressid_model

STRESSID_DIR = Path("stressID")
FEATURES_CSV = (
    STRESSID_DIR / "Feature Extraction" / "Features" / "video11tasks_aus_gaze_mean_std.csv"
)
PROTOCOL_TXT = STRESSID_DIR / "Feature Extraction" / "audio" / "protocol.txt"


def test_load_protocol_labels_valid():
    """Verify protocol.txt correctly parses author binary labels."""
    if not PROTOCOL_TXT.is_file():
        pytest.skip("StressID protocol.txt not present.")

    labels = load_protocol_labels(PROTOCOL_TXT)
    assert len(labels) > 0
    assert "r3zm_Counting3" in labels
    assert labels["r3zm_Counting3"] == 1
    assert "wssm_Video1" in labels
    assert labels["wssm_Video1"] == 0

    # Every label must be binary 0 or 1
    for k, v in labels.items():
        assert v in (0, 1)


def test_load_protocol_labels_missing():
    """Verify FileNotFoundError on nonexistent protocol file."""
    with pytest.raises(FileNotFoundError):
        load_protocol_labels("nonexistent_protocol.txt")


def test_build_stressid_dataset_windowing():
    """Verify 30-second window generation preserves subject and task identity."""
    if not FEATURES_CSV.is_file():
        pytest.skip("StressID features CSV not present.")

    dataset = build_stressid_dataset(
        features_csv=FEATURES_CSV,
        protocol_txt=PROTOCOL_TXT if PROTOCOL_TXT.is_file() else None,
        window_sec=30.0,
        jitter_std=0.01,
        random_seed=42,
    )

    assert isinstance(dataset, StressIDDataset)
    assert len(dataset.X) == len(dataset.y) == len(dataset.groups) == len(dataset.metadata)
    assert len(dataset.feature_names) == 84
    assert len(dataset.subject_ids) > 0
    assert len(dataset.task_ids) > 0

    # Verify metadata fields and task integrity
    for meta in dataset.metadata:
        assert meta.subject_id in dataset.subject_ids
        assert meta.label in (0, 1)
        assert meta.window_id.startswith(meta.task_id)


def test_stressid_leave_subjects_out_no_leakage():
    """Verify Leave-Subjects-Out (GroupKFold) guarantees zero subject data leakage."""
    if not FEATURES_CSV.is_file():
        pytest.skip("StressID features CSV not present.")

    dataset = build_stressid_dataset(
        features_csv=FEATURES_CSV,
        protocol_txt=PROTOCOL_TXT if PROTOCOL_TXT.is_file() else None,
        window_sec=30.0,
    )

    splits = dataset.get_splits(n_splits=5)
    assert len(splits) >= 2

    for fold_i, (train_idx, test_idx) in enumerate(splits):
        train_subjs = set(dataset.groups[train_idx])
        test_subjs = set(dataset.groups[test_idx])

        # Strict test: intersection must be empty
        assert len(train_subjs.intersection(test_subjs)) == 0, (
            f"Fold {fold_i}: participant overlap between train and test sets!"
        )
        assert len(train_idx) > 0
        assert len(test_idx) > 0


def test_evaluate_stressid_cv_and_export(tmp_path: Path):
    """Verify cross-validation evaluation and model artifact persistence."""
    if not FEATURES_CSV.is_file():
        pytest.skip("StressID features CSV not present.")

    model_out = tmp_path / "test_stressid_model.joblib"
    report_out = tmp_path / "test_stressid_report.json"

    report = train_and_save_stressid_model(
        features_csv=FEATURES_CSV,
        protocol_txt=PROTOCOL_TXT if PROTOCOL_TXT.is_file() else None,
        model_type="xgboost",
        n_splits=3,
        output_model_path=model_out,
        output_report_path=report_out,
    )

    assert report.total_windows > 0
    assert report.mean_accuracy > 0.0
    assert len(report.fold_details) == 3
    assert model_out.is_file()
    assert report_out.is_file()

    with report_out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "mean_accuracy" in data
    assert "top_facial_features" in data
