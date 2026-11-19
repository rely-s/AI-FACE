"""Unit tests for single-image and batch photo dataset processor."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from ai_face.image_processor import ImageDistressProcessor


def test_missing_image_file_raises_error(tmp_path: Path) -> None:
    processor = ImageDistressProcessor()
    try:
        with pytest.raises(FileNotFoundError):
            processor.process_file(tmp_path / "non_existent.jpg")
    finally:
        processor.close()


def test_missing_directory_raises_error(tmp_path: Path) -> None:
    processor = ImageDistressProcessor()
    try:
        with pytest.raises(NotADirectoryError):
            processor.process_directory(tmp_path / "non_existent_dir", tmp_path / "out")
    finally:
        processor.close()


def test_blank_image_returns_no_face(tmp_path: Path) -> None:
    processor = ImageDistressProcessor()
    blank_img_path = tmp_path / "blank.png"
    # Create black image 640x480
    black_img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.imwrite(str(blank_img_path), black_img)

    try:
        res = processor.process_file(blank_img_path, output_dir=tmp_path / "out")
        assert res["image_name"] == "blank.png"
        assert res["face_detected"] is False
        assert res["distress_level"] == "NO_FACE"
        assert res["dass_clinical_assessment"] is None
        assert res["facs_action_units"] is None
        assert (tmp_path / "out" / "blank_result.json").is_file()
    finally:
        processor.close()


def test_batch_directory_processing_generates_json_and_csv(tmp_path: Path) -> None:
    processor = ImageDistressProcessor()
    input_dir = tmp_path / "photos"
    input_dir.mkdir()
    out_dir = tmp_path / "batch_out"

    # Create 2 blank photos
    for i in range(2):
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.imwrite(str(input_dir / f"test_{i}.png"), img)

    try:
        results = processor.process_directory(
            directory_path=input_dir,
            output_dir=out_dir,
            save_annotated=False,
        )
        assert len(results) == 2
        assert (out_dir / "batch_image_summary.json").is_file()
        assert (out_dir / "batch_dass_summary.csv").is_file()

        # Verify CSV content
        with open(out_dir / "batch_dass_summary.csv", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3  # Header + 2 rows
            assert "image_name" in lines[0]
            assert "depression_level" in lines[0]
    finally:
        processor.close()
