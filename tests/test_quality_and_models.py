"""Tests for data model schemas, quality validation, and frozen blendshape contracts."""

import math

import pytest
from pydantic import ValidationError

from ai_face.constants import (
    FROZEN_BLENDSHAPE_NAMES,
    REASON_FEATURE_INVALID,
    REASON_MULTIPLE_FACES,
    REASON_NO_FACE,
)
from ai_face.models import PoseDeg, SlotRecord
from ai_face.quality import evaluate_face_detection_quality, validate_extracted_features


def _make_valid_blendshapes() -> dict[str, float]:
    """Helper creating a complete 52-blendshape dictionary."""
    return {name: 0.05 for name in FROZEN_BLENDSHAPE_NAMES}


def test_frozen_blendshape_count():
    """Verify frozen blendshapes list contains exactly 52 ARKit names."""
    assert len(FROZEN_BLENDSHAPE_NAMES) == 52
    assert len(set(FROZEN_BLENDSHAPE_NAMES)) == 52
    assert "_neutral" in FROZEN_BLENDSHAPE_NAMES
    assert "eyeBlinkLeft" in FROZEN_BLENDSHAPE_NAMES


def test_slot_record_valid():
    """Verify valid SlotRecord construction with 52 blendshapes and PoseDeg."""
    slot = SlotRecord(
        session_id="test-session-123",
        slot_index=0,
        target_ms=0,
        frame_ms=10,
        valid=True,
        reasons=[],
        blendshapes=_make_valid_blendshapes(),
        pose_deg=PoseDeg(yaw=1.0, pitch=-2.0, roll=0.5),
    )
    assert slot.valid is True
    assert slot.blendshapes is not None
    assert len(slot.blendshapes) == 52
    assert slot.pose_deg.yaw == 1.0


def test_slot_record_invalid_has_null_features_and_reasons():
    """Verify invalid slot contract: valid=False, reasons non-empty, blendshapes and pose null."""
    slot = SlotRecord(
        session_id="test-session-123",
        slot_index=5,
        target_ms=333,
        frame_ms=335,
        valid=False,
        reasons=[REASON_NO_FACE],
        blendshapes=None,
        pose_deg=None,
    )
    assert slot.valid is False
    assert slot.reasons == [REASON_NO_FACE]
    assert slot.blendshapes is None
    assert slot.pose_deg is None


def test_rejection_of_incomplete_blendshape_dictionary():
    """Verify that fewer than 52 blendshapes or missing keys are rejected by Pydantic."""
    incomplete = {name: 0.1 for name in list(FROZEN_BLENDSHAPE_NAMES)[:30]}
    with pytest.raises(ValidationError):
        SlotRecord(
            session_id="test-session-123",
            slot_index=0,
            target_ms=0,
            frame_ms=0,
            valid=True,
            blendshapes=incomplete,
            pose_deg=PoseDeg(yaw=0, pitch=0, roll=0),
        )


def test_rejection_of_non_finite_blendshapes():
    """Verify that NaN or infinite blendshape values raise validation error."""
    bad_shapes = _make_valid_blendshapes()
    bad_shapes["browDownLeft"] = math.nan

    with pytest.raises(ValidationError):
        SlotRecord(
            session_id="test-session-123",
            slot_index=0,
            target_ms=0,
            frame_ms=0,
            valid=True,
            blendshapes=bad_shapes,
            pose_deg=PoseDeg(yaw=0, pitch=0, roll=0),
        )


def test_rejection_of_non_finite_pose():
    """Verify that NaN or infinite pose angle raises validation error."""
    with pytest.raises(ValidationError):
        PoseDeg(yaw=math.nan, pitch=0.0, roll=0.0)

    with pytest.raises(ValidationError):
        PoseDeg(yaw=0.0, pitch=math.inf, roll=0.0)


def test_quality_evaluator_no_face():
    """Verify evaluate_face_detection_quality detects zero faces as NO_FACE."""
    reasons = evaluate_face_detection_quality(num_faces_detected=0)
    assert reasons == [REASON_NO_FACE]


def test_quality_evaluator_multiple_faces():
    """Verify evaluate_face_detection_quality marks MULTIPLE_FACES when disabled."""
    reasons = evaluate_face_detection_quality(num_faces_detected=2, allow_multiple_faces=False)
    assert REASON_MULTIPLE_FACES in reasons

    # Allowed
    reasons_allowed = evaluate_face_detection_quality(
        num_faces_detected=2, allow_multiple_faces=True
    )
    assert REASON_MULTIPLE_FACES not in reasons_allowed


def test_validate_extracted_features_detects_invalid():
    """Verify validate_extracted_features catches None or incomplete structures."""
    reasons = validate_extracted_features(None, None)
    assert REASON_FEATURE_INVALID in reasons
