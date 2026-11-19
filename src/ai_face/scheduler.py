"""Slot scheduler enforcing nominal 15 Hz slots over 30-second acquisition window."""

from dataclasses import dataclass

import numpy as np


@dataclass
class ScheduledSlot:
    """A slot to be processed by the extractor."""

    slot_index: int
    target_ms: int
    frame: np.ndarray | None
    frame_ms: int | None


class SlotScheduler:
    """Manages the mapping of frames to nominal time slots.

    Guarantees:
    1. Exactly nominal_slots (e.g. 450) slots are emitted in ascending order (0..N-1).
    2. At most one frame is accepted per slot.
    3. Gaps or missed slots are explicitly emitted with frame=None.
    4. Frames that arrive late or duplicate an already-filled slot are dropped.
    """

    def __init__(self, duration_s: float = 30.0, target_fps: float = 15.0) -> None:
        self.duration_s = duration_s
        self.target_fps = target_fps
        self.nominal_slots = int(round(duration_s * target_fps))
        self.slot_interval_ms = 1000.0 / target_fps
        self.total_duration_ms = duration_s * 1000.0

        self.next_slot_index: int = 0
        self.filled_slots: set[int] = set()

    def get_target_ms(self, slot_index: int) -> int:
        """Calculate target timestamp directly from index to avoid cumulative error."""
        return int(round(slot_index * 1000.0 / self.target_fps))

    def timestamp_to_slot(self, timestamp_ms: int) -> int:
        """Map a millisecond timestamp to its nearest corresponding nominal slot index."""
        if timestamp_ms < 0:
            return 0
        return int(round(timestamp_ms * self.target_fps / 1000.0))

    def process_frame(self, frame: np.ndarray, frame_ms: int) -> list[ScheduledSlot]:
        """Process an incoming frame and return slots to record.

        May return multiple ScheduledSlot instances if intermediate slots were missed.
        Returns an empty list if the frame falls into an already filled slot.
        """
        slots_to_emit: list[ScheduledSlot] = []

        if frame_ms >= self.total_duration_ms:
            # Frame is beyond the 30-second window
            return slots_to_emit

        target_slot = self.timestamp_to_slot(frame_ms)
        if target_slot >= self.nominal_slots:
            return slots_to_emit

        # If incoming frame is ahead of next_slot_index, emit intervening missed slots
        while self.next_slot_index < target_slot and self.next_slot_index < self.nominal_slots:
            slots_to_emit.append(
                ScheduledSlot(
                    slot_index=self.next_slot_index,
                    target_ms=self.get_target_ms(self.next_slot_index),
                    frame=None,
                    frame_ms=None,
                )
            )
            self.next_slot_index += 1

        # Now check target_slot
        if target_slot == self.next_slot_index and target_slot not in self.filled_slots:
            slots_to_emit.append(
                ScheduledSlot(
                    slot_index=target_slot,
                    target_ms=self.get_target_ms(target_slot),
                    frame=frame,
                    frame_ms=frame_ms,
                )
            )
            self.filled_slots.add(target_slot)
            self.next_slot_index = target_slot + 1

        return slots_to_emit

    def finalize(self) -> list[ScheduledSlot]:
        """Emit any remaining unfilled slots up to nominal_slots as missed."""
        remaining_slots: list[ScheduledSlot] = []
        while self.next_slot_index < self.nominal_slots:
            remaining_slots.append(
                ScheduledSlot(
                    slot_index=self.next_slot_index,
                    target_ms=self.get_target_ms(self.next_slot_index),
                    frame=None,
                    frame_ms=None,
                )
            )
            self.next_slot_index += 1
        return remaining_slots
