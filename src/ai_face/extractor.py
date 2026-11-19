"""MediaPipe Face Landmarker extraction and visual overlay rendering."""

import hashlib
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from ai_face.config import QualityThresholds
from ai_face.constants import (
    DEFAULT_MODEL_PATH,
    FROZEN_BLENDSHAPE_NAMES,
    OFFICIAL_MODEL_URL,
    REASON_FEATURE_INVALID,
    REASON_MULTIPLE_FACES,
    REASON_NO_FACE,
)
from ai_face.models import ModelMetadata, PoseDeg
from ai_face.pose import matrix_4x4_to_pose_deg
from ai_face.quality import evaluate_face_detection_quality, validate_extracted_features


def compute_file_sha256(path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class FaceLandmarkerExtractor:
    """Wrapper around MediaPipe Face Landmarker in VIDEO mode."""

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        thresholds: QualityThresholds | None = None,
        allow_multiple_faces: bool = False,
    ) -> None:
        self.model_path = Path(model_path)
        self.thresholds = thresholds or QualityThresholds()
        self.allow_multiple_faces = allow_multiple_faces

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"MediaPipe Face Landmarker model not found at: {self.model_path.resolve()}\n"
                f"Please download the official model from:\n  {OFFICIAL_MODEL_URL}\n"
                f"and place it at '{self.model_path}', or use the '--download-model' CLI option."
            )

        self.model_sha256 = compute_file_sha256(self.model_path)

        base_options = python.BaseOptions(model_asset_path=str(self.model_path))
        # num_faces=2 so we can observe whether multiple faces are present
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=2,
            min_face_detection_confidence=self.thresholds.min_detection_confidence,
            min_tracking_confidence=self.thresholds.min_tracking_confidence,
        )

        self.detector = vision.FaceLandmarker.create_from_options(options)
        self._last_timestamp_ms: int = -1

    def get_metadata(self) -> ModelMetadata:
        """Return model metadata for session summary."""
        return ModelMetadata(
            model_path=str(self.model_path),
            sha256=self.model_sha256,
            version="MediaPipe Face Landmarker Task (Float16)",
        )

    def extract(
        self, frame_bgr: np.ndarray, timestamp_ms: int
    ) -> tuple[dict[str, float] | None, PoseDeg | None, list[str], Any]:
        """Extract blendshapes and 3D pose from frame at given timestamp.

        Returns:
            (blendshapes_dict, pose_deg, reasons, detection_result)
        """
        # MediaPipe VIDEO mode requires strictly monotonically increasing timestamps in ms
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self.detector.detect_for_video(mp_image, timestamp_ms)

        num_faces = len(result.face_landmarks) if result.face_landmarks else 0
        if num_faces == 0:
            return None, None, [REASON_NO_FACE], result

        if num_faces > 1 and not self.allow_multiple_faces:
            return None, None, [REASON_MULTIPLE_FACES], result

        # Extract 52 blendshapes
        if not result.face_blendshapes or len(result.face_blendshapes[0]) != len(
            FROZEN_BLENDSHAPE_NAMES
        ):
            return None, None, [REASON_FEATURE_INVALID], result

        blendshapes_dict: dict[str, float] = {}
        for b in result.face_blendshapes[0]:
            blendshapes_dict[b.category_name] = float(b.score)

        # Extract 3D head pose from facial transformation matrix
        if not result.facial_transformation_matrixes:
            return None, None, [REASON_FEATURE_INVALID], result

        try:
            pose_deg = matrix_4x4_to_pose_deg(result.facial_transformation_matrixes[0])
        except Exception:
            return None, None, [REASON_FEATURE_INVALID], result

        # Validate feature finiteness and completeness
        val_reasons = validate_extracted_features(blendshapes_dict, pose_deg)
        if val_reasons:
            return None, None, val_reasons, result

        # Check orientation and other quality limits
        quality_reasons = evaluate_face_detection_quality(
            num_faces_detected=num_faces,
            allow_multiple_faces=self.allow_multiple_faces,
            pose=pose_deg,
            thresholds=self.thresholds,
        )
        if quality_reasons:
            return None, None, quality_reasons, result

        return blendshapes_dict, pose_deg, [], result

    def close(self) -> None:
        """Close MediaPipe detector resources."""
        if hasattr(self, "detector") and self.detector is not None:
            self.detector.close()


def render_preview_overlay(
    frame_bgr: np.ndarray,
    detection_result: Any,
    slot_index: int,
    elapsed_s: float,
    status_text: str,
    fps: float,
    mirror: bool = True,
) -> np.ndarray:
    """Render status HUD and facial landmarks on a display frame copy.

    Does NOT modify the input frame.
    """
    display = frame_bgr.copy()
    h, w = display.shape[:2]

    # Draw face landmark dots if detected
    if detection_result and detection_result.face_landmarks:
        primary_face = detection_result.face_landmarks[0]
        # Draw a sparse subset of landmarks for fast and clean visualization
        for lm in primary_face[::8]:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(display, (cx, cy), 1, (0, 255, 0), -1)

    if mirror:
        display = cv2.flip(display, 1)

    # Draw HUD status banner
    cv2.rectangle(display, (0, 0), (w, 40), (20, 20, 20), -1)
    status_color = (0, 255, 0) if "VALID" in status_text else (0, 140, 255)
    hud_line = (
        f"Slot: {slot_index:03d}/450 | Time: {elapsed_s:4.1f}s/30.0s | "
        f"FPS: {fps:4.1f} | [{status_text}]"
    )
    cv2.putText(
        display,
        hud_line,
        (10, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        status_color,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        display,
        "Press 'q' or ESC to stop session",
        (10, h - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (200, 200, 200),
        1,
        cv2.LINE_AA,
    )

    return display
