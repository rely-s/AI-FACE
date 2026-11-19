"""Tests for session feature aggregation and distress classification."""

from pathlib import Path

import numpy as np
import pytest

from ai_face.classifier import (
    DEFAULT_DISTRESS_MODEL_PATH,
    DistressClassifier,
)
from ai_face.constants import FROZEN_BLENDSHAPE_NAMES
from ai_face.features import aggregate_session_features, get_feature_names
from ai_face.models import PoseDeg, SlotRecord


def _create_synthetic_slots(num_slots: int = 450, valid_ratio: float = 0.9) -> list[SlotRecord]:
    slots = []
    num_valid = int(num_slots * valid_ratio)
    for i in range(num_slots):
        is_valid = i < num_valid
        if is_valid:
            shapes = {
                name: 0.05 + (0.1 if "browDown" in name else 0.0)
                for name in FROZEN_BLENDSHAPE_NAMES
            }
            pose = PoseDeg(yaw=1.0, pitch=-2.0, roll=0.5)
        else:
            shapes = None
            pose = None

        slots.append(
            SlotRecord(
                session_id="test-session",
                slot_index=i,
                target_ms=int(round(i * 1000.0 / 15.0)),
                frame_ms=int(round(i * 1000.0 / 15.0)) if is_valid else None,
                valid=is_valid,
                reasons=[] if is_valid else ["NO_FACE"],
                blendshapes=shapes,
                pose_deg=pose,
            )
        )
    return slots


def test_feature_aggregation_dimension():
    """Verify aggregated feature vector has exactly 220 dimensions."""
    slots = _create_synthetic_slots(num_slots=30, valid_ratio=1.0)
    feats = aggregate_session_features(slots)

    assert feats is not None
    assert isinstance(feats, np.ndarray)
    assert len(feats) == 220
    assert len(get_feature_names()) == 220
    assert np.all(np.isfinite(feats))


def test_distress_classifier_prediction():
    """Verify DistressClassifier outputs available prediction on valid session."""
    model_path = Path(DEFAULT_DISTRESS_MODEL_PATH)
    if not model_path.is_file():
        pytest.skip(f"Distress model not found at {model_path}")

    classifier = DistressClassifier(model_path=model_path)
    slots = _create_synthetic_slots(num_slots=450, valid_ratio=0.95)

    estimation = classifier.predict_session(slots, nominal_slots=450, min_valid_ratio=0.70)

    assert estimation.status == "available"
    assert estimation.level in ("low_distress", "moderate_distress", "high_distress")
    assert estimation.confidence is not None
    assert 0.0 <= estimation.confidence <= 1.0
    assert estimation.probabilities is not None
    assert len(estimation.probabilities) == 3


def test_distress_classifier_withheld_on_low_quality():
    """Verify Quality Gate: output is withheld if valid slots are below threshold."""
    model_path = Path(DEFAULT_DISTRESS_MODEL_PATH)
    if not model_path.is_file():
        pytest.skip(f"Distress model not found at {model_path}")

    classifier = DistressClassifier(model_path=model_path)
    # Only 40% valid slots
    slots = _create_synthetic_slots(num_slots=450, valid_ratio=0.40)

    estimation = classifier.predict_session(slots, nominal_slots=450, min_valid_ratio=0.70)

    assert estimation.status == "withheld"
    assert estimation.level is None
    assert "Insufficient valid slots" in estimation.reason
