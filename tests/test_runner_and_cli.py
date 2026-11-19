"""Tests for SessionRunner orchestration and CLI argument validation."""

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from ai_face.cli import parse_arguments
from ai_face.config import SessionConfig
from ai_face.constants import (
    FROZEN_BLENDSHAPE_NAMES,
    REASON_FRAME_MISSED,
    REASON_NO_FACE,
    STATUS_COMPLETED,
)
from ai_face.extractor import FaceLandmarkerExtractor
from ai_face.models import ModelMetadata, PoseDeg
from ai_face.session_runner import SessionRunner
from ai_face.source import SyntheticFrameSource


def test_cli_requires_input_source():
    """Verify CLI requires either --camera-index or --video."""
    args = parse_arguments([])
    assert args.camera_index is None
    assert args.video is None


def test_cli_mutually_exclusive_inputs():
    """Verify passing both --camera-index and --video raises an error."""
    with pytest.raises(SystemExit):
        parse_arguments(["--camera-index", "0", "--video", "test.mp4"])


def test_cli_custom_duration_and_output(tmp_path: Path):
    """Verify CLI parses duration, fps, and output directory correctly."""
    args = parse_arguments(
        [
            "--video",
            str(tmp_path / "vid.mp4"),
            "--duration",
            "15.0",
            "--fps",
            "10.0",
            "--output-dir",
            str(tmp_path / "custom_out"),
            "--headless",
        ]
    )
    assert args.video == tmp_path / "vid.mp4"
    assert args.duration == 15.0
    assert args.fps == 10.0
    assert args.output_dir == tmp_path / "custom_out"
    assert args.headless is True


def test_session_runner_with_synthetic_source(tmp_path: Path):
    """Verify SessionRunner executes full 30s session producing 450 slots."""
    # Create 30 frames at 15 Hz for a 2.0s session (30 slots)
    duration_s = 2.0
    fps = 15.0
    nominal_slots = 30

    frames = []
    for i in range(nominal_slots):
        t_ms = int(round(i * 1000.0 / fps))
        frames.append((np.zeros((480, 640, 3), dtype=np.uint8), t_ms))

    source = SyntheticFrameSource(frames=frames, fps=fps)

    # Mock extractor so this test runs purely offline without model binary
    mock_extractor = MagicMock(spec=FaceLandmarkerExtractor)
    mock_extractor.get_metadata.return_value = ModelMetadata(
        model_path="mock.task", sha256="123", version="v1"
    )
    # Return valid detection
    valid_blendshapes = {name: 0.0 for name in FROZEN_BLENDSHAPE_NAMES}
    mock_extractor.extract.return_value = (
        valid_blendshapes,
        PoseDeg(yaw=0.0, pitch=0.0, roll=0.0),
        [],
        None,
    )

    config = SessionConfig(
        duration_s=duration_s,
        target_fps=fps,
        output_dir=tmp_path,
        preview=False,
    )

    runner = SessionRunner(
        config=config,
        source=source,
        extractor=mock_extractor,
        session_id="test-synthetic-runner",
    )

    summary = runner.run()

    assert summary.status == STATUS_COMPLETED
    assert summary.nominal_slots == nominal_slots
    assert summary.processed_slots == nominal_slots
    assert summary.valid_slots == nominal_slots
    assert summary.valid_ratio == 1.0


def test_session_runner_short_video_emits_missed_slots(tmp_path: Path):
    """Verify that a video shorter than target duration marks remaining slots as FRAME_MISSED."""
    duration_s = 2.0  # 30 slots
    fps = 15.0

    # Provide only 10 frames (approx 0.67 seconds)
    frames = []
    for i in range(10):
        t_ms = int(round(i * 1000.0 / fps))
        frames.append((np.zeros((100, 100, 3), dtype=np.uint8), t_ms))

    source = SyntheticFrameSource(frames=frames, fps=fps)

    mock_extractor = MagicMock(spec=FaceLandmarkerExtractor)
    mock_extractor.get_metadata.return_value = ModelMetadata(
        model_path="mock.task", sha256="123", version="v1"
    )
    mock_extractor.extract.return_value = (None, None, [REASON_NO_FACE], None)

    config = SessionConfig(
        duration_s=duration_s,
        target_fps=fps,
        output_dir=tmp_path,
        preview=False,
    )

    runner = SessionRunner(
        config=config,
        source=source,
        extractor=mock_extractor,
        session_id="test-short-video",
    )

    summary = runner.run()

    assert summary.status == STATUS_COMPLETED
    assert summary.nominal_slots == 30
    assert summary.processed_slots == 30
    assert summary.invalid_slots == 30
    assert summary.valid_slots == 0
    # Remaining 20 slots must be FRAME_MISSED
    assert summary.reasons_count.get(REASON_FRAME_MISSED, 0) == 20
