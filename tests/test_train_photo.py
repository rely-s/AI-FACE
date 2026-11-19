"""Tests for photo dataset training pipeline."""

from pathlib import Path

import pytest

from ai_face.training.train_photo_classifier import (
    get_photo_feature_names,
    train_photo_classifier,
)


def test_photo_feature_names_dimension() -> None:
    names = get_photo_feature_names()
    # 52 ARKit blendshapes + 31 FACS AUs = 83 features
    assert len(names) == 83
    assert "bs_browDownLeft" in names
    assert "facs_AU1" in names
    assert "facs_AU35" in names


def test_empty_dataset_raises_error(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    with pytest.raises(ValueError, match="No class subdirectories"):
        train_photo_classifier(dataset_dir)
