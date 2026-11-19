"""Pydantic data models for slot records and session summary."""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_face.constants import (
    ESTIMATION_NOT_AVAILABLE,
    FROZEN_BLENDSHAPE_NAMES,
    SCHEMA_VERSION,
)


class PoseDeg(BaseModel):
    """Head pose orientation angles in degrees."""

    model_config = ConfigDict(extra="forbid")

    yaw: float
    pitch: float
    roll: float

    @field_validator("yaw", "pitch", "roll")
    @classmethod
    def validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError(f"Pose angle must be a finite number, got {v}")
        return float(v)


class SlotRecord(BaseModel):
    """Acquisition slot record matching AI-FACE schema specification."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    session_id: str
    slot_index: int = Field(ge=0)
    target_ms: int = Field(ge=0)
    frame_ms: int | None = None
    valid: bool
    reasons: list[str] = Field(default_factory=list)
    blendshapes: dict[str, float] | None = None
    pose_deg: PoseDeg | None = None

    @field_validator("blendshapes")
    @classmethod
    def validate_blendshapes(cls, v: dict[str, float] | None, info: Any) -> dict[str, float] | None:
        if v is None:
            return None

        # Check all 52 canonical blendshapes are present
        if len(v) != len(FROZEN_BLENDSHAPE_NAMES):
            raise ValueError(
                f"Expected exactly {len(FROZEN_BLENDSHAPE_NAMES)} blendshapes, got {len(v)}"
            )

        for name in FROZEN_BLENDSHAPE_NAMES:
            if name not in v:
                raise ValueError(f"Missing required blendshape category: {name}")
            val = v[name]
            if not math.isfinite(val):
                raise ValueError(f"Blendshape {name} value must be finite, got {val}")

        return v


class DeviceMetadata(BaseModel):
    """Camera or video input source metadata."""

    model_config = ConfigDict(extra="forbid")

    source_type: str  # "webcam", "video", "synthetic"
    source_identifier: str
    requested_fps: float | None = None
    reported_fps: float | None = None
    measured_fps: float | None = None
    requested_width: int | None = None
    requested_height: int | None = None
    actual_width: int | None = None
    actual_height: int | None = None


class ModelMetadata(BaseModel):
    """MediaPipe model file identification and checksum."""

    model_config = ConfigDict(extra="forbid")

    model_path: str
    sha256: str | None = None
    version: str = "MediaPipe Face Landmarker Task (Float16)"


class EstimationStatus(BaseModel):
    """Session distress estimation status."""

    model_config = ConfigDict(extra="forbid")

    status: str = ESTIMATION_NOT_AVAILABLE
    reason: str = "Model evaluation offline stage pending"


class SessionSummary(BaseModel):
    """Summary of completed, cancelled, or failed acquisition session."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    config_version: str
    session_id: str
    status: str  # "completed", "cancelled", "failed"
    source_type: str
    source_identifier: str
    created_at_utc: str
    completed_at_utc: str
    target_duration_s: float
    actual_duration_s: float
    nominal_slots: int
    processed_slots: int
    valid_slots: int
    invalid_slots: int
    valid_ratio: float
    effective_rate_hz: float
    reasons_count: dict[str, int]
    device_metadata: DeviceMetadata
    model_metadata: ModelMetadata
    estimation: EstimationStatus = Field(default_factory=EstimationStatus)
