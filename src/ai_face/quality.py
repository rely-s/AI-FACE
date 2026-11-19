"""Quality inspection and validity gate for extracted facial features."""

import math

from ai_face.config import QualityThresholds
from ai_face.constants import (
    REASON_FEATURE_INVALID,
    REASON_MULTIPLE_FACES,
    REASON_NO_FACE,
    REASON_POSE_OUT_OF_RANGE,
)
from ai_face.models import PoseDeg


def is_finite_number(val: float | None) -> bool:
    """Check if value is a valid finite float."""
    if val is None:
        return False
    return math.isfinite(val)


def evaluate_face_detection_quality(
    num_faces_detected: int,
    allow_multiple_faces: bool = False,
    pose: PoseDeg | None = None,
    thresholds: QualityThresholds | None = None,
) -> list[str]:
    """Evaluate quality reasons based on face detection and orientation.

    Returns a list of reason codes (empty list if all checks pass).
    """
    reasons: list[str] = []

    if num_faces_detected == 0:
        reasons.append(REASON_NO_FACE)
        return reasons

    if num_faces_detected > 1 and not allow_multiple_faces:
        reasons.append(REASON_MULTIPLE_FACES)

    if pose is not None and thresholds is not None:
        if (
            abs(pose.yaw) > thresholds.max_yaw_deg
            or abs(pose.pitch) > thresholds.max_pitch_deg
            or abs(pose.roll) > thresholds.max_roll_deg
        ):
            reasons.append(REASON_POSE_OUT_OF_RANGE)

    return reasons


def validate_extracted_features(
    blendshapes: dict[str, float] | None,
    pose: PoseDeg | None,
    expected_blendshape_count: int = 52,
) -> list[str]:
    """Validate numerical integrity of blendshapes and pose angles."""
    reasons: list[str] = []

    if blendshapes is None or pose is None:
        reasons.append(REASON_FEATURE_INVALID)
        return reasons

    if len(blendshapes) != expected_blendshape_count:
        reasons.append(REASON_FEATURE_INVALID)
        return reasons

    for k, v in blendshapes.items():
        if not is_finite_number(v):
            reasons.append(REASON_FEATURE_INVALID)
            return reasons

    if not (
        is_finite_number(pose.yaw) and is_finite_number(pose.pitch) and is_finite_number(pose.roll)
    ):
        reasons.append(REASON_FEATURE_INVALID)

    return reasons
