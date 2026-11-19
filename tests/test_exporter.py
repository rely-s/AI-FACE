"""Tests for SessionExporter atomic folder handling and JSONL formatting."""

import json
from pathlib import Path

from ai_face.constants import FROZEN_BLENDSHAPE_NAMES, STATUS_COMPLETED
from ai_face.exporter import SessionExporter
from ai_face.models import DeviceMetadata, ModelMetadata, PoseDeg, SessionSummary, SlotRecord


def test_atomic_export_promotion(tmp_path: Path):
    """Verify exporter creates .tmp staging directory and atomically renames to final."""
    session_id = "test-atomic-1234"
    exporter = SessionExporter(base_output_dir=tmp_path, session_id=session_id)

    exporter.open()
    staging_dir = tmp_path / f"{session_id}.tmp"
    final_dir = tmp_path / session_id

    assert staging_dir.exists()
    assert not final_dir.exists()

    # Write a slot
    slot = SlotRecord(
        session_id=session_id,
        slot_index=0,
        target_ms=0,
        frame_ms=5,
        valid=True,
        blendshapes={name: 0.1 for name in FROZEN_BLENDSHAPE_NAMES},
        pose_deg=PoseDeg(yaw=0.0, pitch=0.0, roll=0.0),
    )
    exporter.write_slot(slot)

    # Finalize with summary
    summary = SessionSummary(
        config_version="1.0.0",
        session_id=session_id,
        status=STATUS_COMPLETED,
        source_type="synthetic",
        source_identifier="test",
        created_at_utc="2026-11-19T00:00:00Z",
        completed_at_utc="2026-11-19T00:00:30Z",
        target_duration_s=30.0,
        actual_duration_s=30.0,
        nominal_slots=450,
        processed_slots=1,
        valid_slots=1,
        invalid_slots=0,
        valid_ratio=1 / 450,
        effective_rate_hz=1 / 30.0,
        reasons_count={},
        device_metadata=DeviceMetadata(source_type="test", source_identifier="test"),
        model_metadata=ModelMetadata(model_path="test.task"),
    )

    result_dir = exporter.finalize(summary)

    # Staging dir must no longer exist, final dir must exist
    assert not staging_dir.exists()
    assert final_dir.exists()
    assert result_dir == final_dir

    # Check files exist inside final_dir
    features_file = final_dir / "features.jsonl"
    summary_file = final_dir / "session_summary.json"
    assert features_file.is_file()
    assert summary_file.is_file()

    # Verify JSONL lines
    with open(features_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["slot_index"] == 0
        assert data["valid"] is True
        assert len(data["blendshapes"]) == 52

    # Verify summary JSON
    with open(summary_file, "r", encoding="utf-8") as f:
        sum_data = json.load(f)
        assert sum_data["session_id"] == session_id
        assert sum_data["status"] == STATUS_COMPLETED


def test_exporter_discard_cleans_up_staging(tmp_path: Path):
    """Verify discard cleans up staging directory on error."""
    session_id = "test-discard-5678"
    exporter = SessionExporter(base_output_dir=tmp_path, session_id=session_id)

    exporter.open()
    staging_dir = tmp_path / f"{session_id}.tmp"
    final_dir = tmp_path / session_id

    assert staging_dir.exists()

    exporter.discard()

    assert not staging_dir.exists()
    assert not final_dir.exists()
