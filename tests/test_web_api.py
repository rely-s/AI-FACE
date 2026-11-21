"""Unit and integration tests for AI-FACE FastAPI Web Platform."""

import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ai_face.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["facs_aus_count"] == 31
    assert "depression" in data["dass_dimensions"]


def test_clinical_info_endpoint(client: TestClient) -> None:
    res = client.get("/api/v1/clinical/info")
    assert res.status_code == 200
    data = res.json()
    assert "AU1" in data["facs_metadata"]
    assert "AU4" in data["facs_metadata"]
    assert "AU15" in data["facs_metadata"]
    assert "Normal" in data["dass_thresholds"]
    assert len(data["intensity_levels"]) == 6


def test_index_html_served(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "AI-FACE" in res.text
    assert "DASS-3" in res.text


def test_analyze_photo_endpoint(client: TestClient, tmp_path: Path) -> None:
    # Create synthetic test image
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    _, buffer = cv2.imencode(".jpg", img)
    file_bytes = io.BytesIO(buffer.tobytes())

    res = client.post(
        "/api/v1/analyze/photo",
        files={"file": ("test_face.jpg", file_bytes, "image/jpeg")},
        data={"show_emotions": "false"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["image_name"] == "test_face.jpg"
    assert "face_detected" in data
    assert "distress_level" in data
    assert "annotated_image_base64" in data


def test_analyze_frame_endpoint(client: TestClient) -> None:
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    _, buffer = cv2.imencode(".jpg", img)
    file_bytes = io.BytesIO(buffer.tobytes())

    res = client.post(
        "/api/v1/analyze/frame",
        files={"file": ("live_frame.jpg", file_bytes, "image/jpeg")},
        data={"show_emotions": "true", "subject_id": "TEST_SUBJ", "mirror": "true"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["image_name"] == "live_frame.jpg"
    assert "annotated_image_base64" in data
