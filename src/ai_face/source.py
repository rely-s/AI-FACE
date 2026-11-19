"""Frame source abstractions for Webcam, Video files, and Synthetic test sources."""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self

import cv2
import numpy as np

from ai_face.models import DeviceMetadata


class FrameSource(ABC):
    """Abstract base class for frame providers."""

    @abstractmethod
    def read_frame(self) -> tuple[np.ndarray, int] | None:
        """Read the next available frame.

        Returns:
            (frame_bgr, relative_timestamp_ms) or None if source has ended.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> DeviceMetadata:
        """Return device and stream metadata."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release all underlying capture resources cleanly."""
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class WebcamSource(FrameSource):
    """Webcam frame source using monotonic clock timestamps."""

    def __init__(
        self,
        camera_index: int = 0,
        requested_width: int = 1920,
        requested_height: int = 1080,
        requested_fps: float = 30.0,
    ) -> None:
        self.camera_index = camera_index
        self.requested_width = requested_width
        self.requested_height = requested_height
        self.requested_fps = requested_fps

        # DirectShow backend on Windows is faster and avoids delay
        backend = cv2.CAP_DSHOW if cv2.CAP_DSHOW else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(camera_index, backend)
        if not self.cap.isOpened():
            # Fallback to default backend
            self.cap = cv2.VideoCapture(camera_index)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open webcam with index {camera_index}. "
                "Ensure camera is connected and not in use by another application."
            )

        # Set requested properties
        if requested_width and requested_height:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, requested_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, requested_height)
        if requested_fps:
            self.cap.set(cv2.CAP_PROP_FPS, requested_fps)

        # Query reported properties
        self.reported_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        self.reported_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        self.reported_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)

        self._t0: float | None = None
        self._frame_count: int = 0
        self._last_frame_time: float = 0.0

    def read_frame(self) -> tuple[np.ndarray, int] | None:
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None

        now = time.monotonic()
        if self._t0 is None:
            self._t0 = now

        rel_ms = int(round((now - self._t0) * 1000.0))
        self._frame_count += 1
        self._last_frame_time = now

        return frame, rel_ms

    def get_metadata(self) -> DeviceMetadata:
        measured_fps = None
        if self._t0 is not None and self._frame_count > 1:
            duration = self._last_frame_time - self._t0
            if duration > 0:
                measured_fps = round(self._frame_count / duration, 2)

        return DeviceMetadata(
            source_type="webcam",
            source_identifier=f"webcam_{self.camera_index}",
            requested_fps=self.requested_fps,
            reported_fps=self.reported_fps if self.reported_fps > 0 else None,
            measured_fps=measured_fps,
            requested_width=self.requested_width,
            requested_height=self.requested_height,
            actual_width=self.reported_width,
            actual_height=self.reported_height,
        )

    def close(self) -> None:
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()


class VideoFileSource(FrameSource):
    """Local video file frame source with monotonic timestamp enforcement."""

    def __init__(self, video_path: str | Path) -> None:
        self.video_path = Path(video_path)
        if not self.video_path.is_file():
            raise FileNotFoundError(
                f"Video file does not exist: {self.video_path}. "
                "Please verify path and file permissions."
            )

        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Failed to open video file: {self.video_path}. "
                "Ensure file is a valid readable video container (e.g. MP4, AVI, MKV)."
            )

        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if self.fps <= 0.0:
            # Fallback default if video container lacks valid FPS header
            self.fps = 30.0

        self._frame_index: int = 0
        self._last_timestamp_ms: int = -1

    def read_frame(self) -> tuple[np.ndarray, int] | None:
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None

        # Attempt to read media timestamp from container
        pos_msec = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        if pos_msec > 0 and pos_msec > self._last_timestamp_ms:
            rel_ms = int(round(pos_msec))
        else:
            # Deterministic fallback based on frame index and source FPS
            rel_ms = int(round(self._frame_index * 1000.0 / self.fps))

        # Enforce strict monotonicity
        if rel_ms <= self._last_timestamp_ms:
            rel_ms = self._last_timestamp_ms + 1

        self._last_timestamp_ms = rel_ms
        self._frame_index += 1

        return frame, rel_ms

    def get_metadata(self) -> DeviceMetadata:
        return DeviceMetadata(
            source_type="video",
            source_identifier=str(self.video_path.name),
            requested_fps=None,
            reported_fps=self.fps,
            measured_fps=self.fps,
            requested_width=None,
            requested_height=None,
            actual_width=self.width,
            actual_height=self.height,
        )

    def close(self) -> None:
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()


class SyntheticFrameSource(FrameSource):
    """Deterministic synthetic frame source for unit and integration testing."""

    def __init__(
        self,
        frames: list[tuple[np.ndarray, int]],
        width: int = 640,
        height: int = 480,
        fps: float = 30.0,
    ) -> None:
        self.frames = frames
        self.width = width
        self.height = height
        self.fps = fps
        self._index: int = 0

    def read_frame(self) -> tuple[np.ndarray, int] | None:
        if self._index >= len(self.frames):
            return None
        item = self.frames[self._index]
        self._index += 1
        return item

    def get_metadata(self) -> DeviceMetadata:
        return DeviceMetadata(
            source_type="synthetic",
            source_identifier="synthetic_test_source",
            requested_fps=self.fps,
            reported_fps=self.fps,
            measured_fps=self.fps,
            requested_width=self.width,
            requested_height=self.height,
            actual_width=self.width,
            actual_height=self.height,
        )

    def close(self) -> None:
        self.frames = []
