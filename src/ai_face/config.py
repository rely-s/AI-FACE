"""Configuration models and defaults for AI-FACE acquisition."""

from dataclasses import dataclass, field
from pathlib import Path

from ai_face.constants import CONFIG_VERSION, DEFAULT_MODEL_PATH


@dataclass(frozen=True)
class QualityThresholds:
    """Configurable quality thresholds for initial pilot monitoring."""

    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    max_yaw_deg: float = 45.0
    max_pitch_deg: float = 45.0
    max_roll_deg: float = 45.0


@dataclass(frozen=True)
class SessionConfig:
    """Session configuration for acquisition and scheduling."""

    config_version: str = CONFIG_VERSION
    duration_s: float = 30.0
    target_fps: float = 15.0
    allow_multiple_faces: bool = False
    output_dir: Path = field(default_factory=lambda: Path("output"))
    model_path: Path = field(default_factory=lambda: Path(DEFAULT_MODEL_PATH))
    preview: bool = True
    preview_mirror: bool = True
    quality: QualityThresholds = field(default_factory=QualityThresholds)

    @property
    def nominal_slots(self) -> int:
        """Calculate exact nominal slot count for session duration and target rate."""
        return int(round(self.duration_s * self.target_fps))

    @property
    def slot_interval_ms(self) -> float:
        """Nominal interval between slots in milliseconds."""
        return 1000.0 / self.target_fps
