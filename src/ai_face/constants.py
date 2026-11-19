"""Constants, frozen feature schemas, and canonical reason codes for AI-FACE."""

from typing import Final

SCHEMA_VERSION: Final[str] = "1.0.0"
CONFIG_VERSION: Final[str] = "1.0.0"

# Canonical 52 MediaPipe Face Landmarker blendshape names frozen for schema stability.
FROZEN_BLENDSHAPE_NAMES: Final[tuple[str, ...]] = (
    "_neutral",
    "browDownLeft",
    "browDownRight",
    "browInnerUp",
    "browOuterUpLeft",
    "browOuterUpRight",
    "cheekPuff",
    "cheekSquintLeft",
    "cheekSquintRight",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "eyeLookDownLeft",
    "eyeLookDownRight",
    "eyeLookInLeft",
    "eyeLookInRight",
    "eyeLookOutLeft",
    "eyeLookOutRight",
    "eyeLookUpLeft",
    "eyeLookUpRight",
    "eyeSquintLeft",
    "eyeSquintRight",
    "eyeWideLeft",
    "eyeWideRight",
    "jawForward",
    "jawLeft",
    "jawOpen",
    "jawRight",
    "mouthClose",
    "mouthDimpleLeft",
    "mouthDimpleRight",
    "mouthFrownLeft",
    "mouthFrownRight",
    "mouthFunnel",
    "mouthLeft",
    "mouthLowerDownLeft",
    "mouthLowerDownRight",
    "mouthPressLeft",
    "mouthPressRight",
    "mouthPucker",
    "mouthRight",
    "mouthRollLower",
    "mouthRollUpper",
    "mouthShrugLower",
    "mouthShrugUpper",
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthStretchLeft",
    "mouthStretchRight",
    "mouthUpperUpLeft",
    "mouthUpperUpRight",
    "noseSneerLeft",
    "noseSneerRight",
)

# Standard reason codes for invalid slots (doc 03, section 21)
REASON_NO_FACE: Final[str] = "NO_FACE"
REASON_MULTIPLE_FACES: Final[str] = "MULTIPLE_FACES"
REASON_FRAME_MISSED: Final[str] = "FRAME_MISSED"
REASON_FACE_OUT_OF_FRAME: Final[str] = "FACE_OUT_OF_FRAME"
REASON_LOW_LIGHT: Final[str] = "LOW_LIGHT"
REASON_OVEREXPOSED: Final[str] = "OVEREXPOSED"
REASON_BLUR: Final[str] = "BLUR"
REASON_POSE_OUT_OF_RANGE: Final[str] = "POSE_OUT_OF_RANGE"
REASON_FEATURE_INVALID: Final[str] = "FEATURE_INVALID"

# Session terminal statuses
STATUS_COMPLETED: Final[str] = "completed"
STATUS_CANCELLED: Final[str] = "cancelled"
STATUS_FAILED: Final[str] = "failed"

# Estimation status (fixed to "not_available" in phase A)
ESTIMATION_NOT_AVAILABLE: Final[str] = "not_available"

# Model details
OFFICIAL_MODEL_URL: Final[str] = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
OFFICIAL_MODEL_SHA256: Final[str] = (
    "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
)
DEFAULT_MODEL_PATH: Final[str] = "models/face_landmarker.task"
