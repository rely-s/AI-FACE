"""Tests for SlotScheduler timing math and slot allocation."""

import numpy as np

from ai_face.scheduler import SlotScheduler


def test_30s_session_produces_450_unique_and_ordered_slots():
    """Verify that a 30s session at 15 Hz produces exactly 450 unique slots ordered 0..449."""
    scheduler = SlotScheduler(duration_s=30.0, target_fps=15.0)
    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)

    emitted_indices = []

    # Simulate 30 fps stream: frame arrives every 33.33 ms
    for frame_idx in range(900):
        t_ms = int(round(frame_idx * 1000.0 / 30.0))
        slots = scheduler.process_frame(dummy_frame, t_ms)
        for s in slots:
            emitted_indices.append(s.slot_index)

    # Finalize any remainder
    slots = scheduler.finalize()
    for s in slots:
        emitted_indices.append(s.slot_index)

    assert len(emitted_indices) == 450
    assert emitted_indices == list(range(450))
    # All slots should be unique and strictly monotonically increasing
    assert len(set(emitted_indices)) == 450


def test_duplicate_and_burst_timestamps_do_not_duplicate_features():
    """Verify that multiple frames inside the same slot do not cause feature duplication."""
    scheduler = SlotScheduler(duration_s=1.0, target_fps=15.0)  # 15 nominal slots
    frame1 = np.ones((10, 10, 3), dtype=np.uint8)
    frame2 = np.ones((10, 10, 3), dtype=np.uint8) * 2

    # Slot 0 interval is [0, 66.67) ms. Send frames at 0 ms, 10 ms, 20 ms
    slots_0a = scheduler.process_frame(frame1, 0)
    slots_0b = scheduler.process_frame(frame2, 10)
    slots_0c = scheduler.process_frame(frame2, 20)

    # Only first frame should be accepted for slot 0
    assert len(slots_0a) == 1
    assert slots_0a[0].slot_index == 0
    assert slots_0a[0].frame is frame1

    # Later frames within the same slot must be dropped
    assert len(slots_0b) == 0
    assert len(slots_0c) == 0


def test_dropped_frames_emit_missed_slots_without_copying():
    """Verify that large time gaps emit explicit missed slots without copying previous frames."""
    scheduler = SlotScheduler(duration_s=2.0, target_fps=15.0)  # 30 slots
    frame0 = np.ones((10, 10, 3), dtype=np.uint8)
    frameN = np.ones((10, 10, 3), dtype=np.uint8) * 5

    # First frame at 0 ms (slot 0)
    slots1 = scheduler.process_frame(frame0, 0)
    assert len(slots1) == 1
    assert slots1[0].slot_index == 0
    assert slots1[0].frame is not None

    # Jump to 200 ms (slot 3: 200 // 66.67 = 3)
    # Slots 1 and 2 were missed!
    slots2 = scheduler.process_frame(frameN, 200)
    assert len(slots2) == 3  # Slot 1 (missed), Slot 2 (missed), Slot 3 (filled)

    # Verify slot 1 and 2 are missed
    assert slots2[0].slot_index == 1
    assert slots2[0].frame is None
    assert slots2[0].frame_ms is None

    assert slots2[1].slot_index == 2
    assert slots2[1].frame is None
    assert slots2[1].frame_ms is None

    # Verify slot 3 is filled with frameN (not a copy of frame0)
    assert slots2[2].slot_index == 3
    assert slots2[2].frame is frameN


def test_target_ms_formula_prevents_cumulative_drift():
    """Verify that target_ms is computed directly from index to avoid cumulative drift."""
    scheduler = SlotScheduler(duration_s=30.0, target_fps=15.0)
    # Target timestamps for slot 0, 1, 2, ..., 449
    assert scheduler.get_target_ms(0) == 0
    assert scheduler.get_target_ms(1) == 67
    assert scheduler.get_target_ms(2) == 133
    assert scheduler.get_target_ms(15) == 1000
    assert scheduler.get_target_ms(449) == 29933
