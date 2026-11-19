"""Integration smoke test using the real MediaPipe Face Landmarker model on a test video."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from ai_face.config import SessionConfig
from ai_face.constants import DEFAULT_MODEL_PATH, REASON_NO_FACE, STATUS_COMPLETED
from ai_face.extractor import FaceLandmarkerExtractor
from ai_face.session_runner import SessionRunner
from ai_face.source import VideoFileSource


@pytest.fixture
def face_test_video(tmp_path: Path) -> Path:
    """Create a 2-second (30 frames at 15 fps) test video with face and non-face sections."""
    video_path = tmp_path / "smoke_test_video.mp4"
    fps = 15.0
    width, height = 640, 480

    # Load Grace Hopper sample image from matplotlib
    img_sample = Path(".venv/Lib/site-packages/matplotlib/mpl-data/sample_data/grace_hopper.jpg")
    if not img_sample.is_file():
        pytest.skip("Sample face image not found.")

    face_img = cv2.imread(str(img_sample))
    face_img = cv2.resize(face_img, (width, height))
    blank_img = np.zeros((height, width, 3), dtype=np.uint8)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

    # First 15 frames: real face (Grace Hopper)
    for _ in range(15):
        out.write(face_img)

    # Next 15 frames: blank black frames (no face)
    for _ in range(15):
        out.write(blank_img)

    out.release()
    return video_path


def test_real_mediapipe_video_extraction(tmp_path: Path, face_test_video: Path):
    """End-to-end smoke test verifying feature extraction with real MediaPipe model."""
    model_path = Path(DEFAULT_MODEL_PATH)
    if not model_path.is_file():
        pytest.skip(f"Model file not found at {model_path}")

    config = SessionConfig(
        duration_s=2.0,  # 30 slots
        target_fps=15.0,
        output_dir=tmp_path / "output",
        model_path=model_path,
        preview=False,
    )

    source = VideoFileSource(face_test_video)
    extractor = FaceLandmarkerExtractor(model_path=model_path)

    session_id = "smoke-test-session-001"
    runner = SessionRunner(
        config=config,
        source=source,
        extractor=extractor,
        session_id=session_id,
    )

    summary = runner.run()

    assert summary.status == STATUS_COMPLETED
    assert summary.nominal_slots == 30
    assert summary.processed_slots == 30
    assert summary.valid_slots > 0
    assert summary.invalid_slots > 0
    assert summary.reasons_count.get(REASON_NO_FACE, 0) > 0

    # Verify features.jsonl contents
    session_dir = tmp_path / "output" / session_id
    features_file = session_dir / "features.jsonl"
    assert features_file.is_file()

    with open(features_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    assert len(records) == 30

    # First record should be valid face
    rec0 = records[0]
    assert rec0["valid"] is True
    assert rec0["reasons"] == []
    assert len(rec0["blendshapes"]) == 52
    assert "yaw" in rec0["pose_deg"]
    assert "pitch" in rec0["pose_deg"]
    assert "roll" in rec0["pose_deg"]

    # One of the later records should be invalid with NO_FACE
    rec25 = records[25]
    assert rec25["valid"] is False
    assert REASON_NO_FACE in rec25["reasons"]
    assert rec25["blendshapes"] is None
    assert rec25["pose_deg"] is None

    extractor.close()
