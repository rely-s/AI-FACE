"""Tests for session summary metrics, 420/450 validity fixture, and status handling."""

from datetime import datetime, timezone

import pytest

from ai_face.constants import (
    ESTIMATION_NOT_AVAILABLE,
    REASON_FRAME_MISSED,
    REASON_NO_FACE,
    SCHEMA_VERSION,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from ai_face.models import (
    DeviceMetadata,
    EstimationStatus,
    ModelMetadata,
    SessionSummary,
)


def _make_dummy_summary(
    status: str,
    target_duration_s: float = 30.0,
    actual_duration_s: float = 30.0,
    nominal_slots: int = 450,
    valid_slots: int = 420,
    processed_slots: int = 450,
    reasons_count: dict[str, int] | None = None,
) -> SessionSummary:
    now_iso = datetime.now(timezone.utc).isoformat()
    invalid_slots = processed_slots - valid_slots
    valid_ratio = round(valid_slots / nominal_slots, 4) if nominal_slots > 0 else 0.0
    effective_rate = round(valid_slots / actual_duration_s, 2) if actual_duration_s > 0 else 0.0

    return SessionSummary(
        schema_version=SCHEMA_VERSION,
        config_version=SCHEMA_VERSION,
        session_id="fixture-session-uuid",
        status=status,
        source_type="synthetic",
        source_identifier="test_fixture",
        created_at_utc=now_iso,
        completed_at_utc=now_iso,
        target_duration_s=target_duration_s,
        actual_duration_s=actual_duration_s,
        nominal_slots=nominal_slots,
        processed_slots=processed_slots,
        valid_slots=valid_slots,
        invalid_slots=invalid_slots,
        valid_ratio=valid_ratio,
        effective_rate_hz=effective_rate,
        reasons_count=reasons_count or {REASON_NO_FACE: 30},
        device_metadata=DeviceMetadata(
            source_type="synthetic",
            source_identifier="fixture",
        ),
        model_metadata=ModelMetadata(
            model_path="models/face_landmarker.task",
        ),
        estimation=EstimationStatus(),
    )


def test_420_valid_slots_fixture_metrics():
    """Verify that 420 valid slots in 30s produces 420/450 (~0.9333) ratio and 14.0 Hz rate."""
    summary = _make_dummy_summary(
        status=STATUS_COMPLETED,
        target_duration_s=30.0,
        actual_duration_s=30.0,
        nominal_slots=450,
        valid_slots=420,
        processed_slots=450,
        reasons_count={REASON_NO_FACE: 30},
    )

    # 420 / 450 = 0.933333...
    expected_ratio = round(420 / 450, 4)  # 0.9333
    assert summary.valid_ratio == expected_ratio
    assert pytest.approx(summary.valid_ratio, abs=1e-4) == 0.9333

    # Effective rate: 420 / 30.0s = 14.0 Hz
    assert summary.effective_rate_hz == 14.0
    assert summary.valid_slots == 420
    assert summary.invalid_slots == 30
    assert summary.nominal_slots == 450
    assert summary.status == STATUS_COMPLETED
    assert summary.estimation.status == ESTIMATION_NOT_AVAILABLE


def test_cancelled_session_is_not_marked_completed():
    """Verify cancelled sessions are marked with STATUS_CANCELLED."""
    summary = _make_dummy_summary(
        status=STATUS_CANCELLED,
        target_duration_s=30.0,
        actual_duration_s=12.5,
        nominal_slots=450,
        valid_slots=150,
        processed_slots=180,
    )

    assert summary.status == STATUS_CANCELLED
    assert summary.status != STATUS_COMPLETED
    assert summary.actual_duration_s < summary.target_duration_s


def test_failed_session_is_not_marked_completed():
    """Verify failed session status is preserved and distinct."""
    summary = _make_dummy_summary(
        status=STATUS_FAILED,
        target_duration_s=30.0,
        actual_duration_s=2.1,
        nominal_slots=450,
        valid_slots=10,
        processed_slots=25,
        reasons_count={REASON_FRAME_MISSED: 15},
    )

    assert summary.status == STATUS_FAILED
    assert summary.status != STATUS_COMPLETED
