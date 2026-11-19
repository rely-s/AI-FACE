"""Session execution coordinator for AI-FACE acquisition."""

import signal
import sys
import time
import uuid
from datetime import datetime, timezone

import cv2

from ai_face.classifier import DistressClassifier
from ai_face.config import SessionConfig
from ai_face.constants import (
    REASON_FRAME_MISSED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from ai_face.exporter import SessionExporter
from ai_face.extractor import FaceLandmarkerExtractor, render_preview_overlay
from ai_face.models import EstimationStatus, SessionSummary, SlotRecord
from ai_face.scheduler import SlotScheduler
from ai_face.source import FrameSource


class SessionRunner:
    """Executes a 30-second acquisition session."""

    def __init__(
        self,
        config: SessionConfig,
        source: FrameSource,
        extractor: FaceLandmarkerExtractor,
        distress_classifier: DistressClassifier | None = None,
        session_id: str | None = None,
    ) -> None:
        self.config = config
        self.source = source
        self.extractor = extractor
        self.distress_classifier = distress_classifier
        self.session_id = session_id or str(uuid.uuid4())
        self.scheduler = SlotScheduler(
            duration_s=config.duration_s,
            target_fps=config.target_fps,
        )
        self.exporter = SessionExporter(
            base_output_dir=config.output_dir,
            session_id=self.session_id,
        )

        self._cancelled = False
        self._prev_sigint = None

    def _sigint_handler(self, sig, frame) -> None:
        print(
            "\n[AI-FACE] Cancellation signal received (Ctrl+C). Terminating session gracefully..."
        )
        self._cancelled = True

    def run(self) -> SessionSummary:
        """Run the acquisition session to completion, cancellation, or failure."""
        created_at_dt = datetime.now(timezone.utc)
        created_at_utc = created_at_dt.isoformat()
        t_start = time.monotonic()

        # Register signal handler for graceful Ctrl+C
        self._prev_sigint = signal.signal(signal.SIGINT, self._sigint_handler)

        processed_slots: list[SlotRecord] = []
        reasons_count: dict[str, int] = {}
        status = STATUS_COMPLETED
        window_name = f"AI-FACE Preview: {self.session_id[:8]}"

        self.exporter.open()

        try:
            while not self._cancelled:
                frame_data = self.source.read_frame()
                now = time.monotonic()
                elapsed_s = now - t_start

                if frame_data is None:
                    # Source reached end of stream (e.g. video file ended or camera disconnected)
                    break

                frame_bgr, frame_ms = frame_data

                # Check if session time window exceeded
                if frame_ms >= self.config.duration_s * 1000.0:
                    break

                scheduled_slots = self.scheduler.process_frame(frame_bgr, frame_ms)

                last_result = None
                status_text = "PROCESSING"

                for slot in scheduled_slots:
                    if slot.frame is None:
                        # Missed slot
                        slot_rec = SlotRecord(
                            schema_version=self.config.config_version,
                            session_id=self.session_id,
                            slot_index=slot.slot_index,
                            target_ms=slot.target_ms,
                            frame_ms=None,
                            valid=False,
                            reasons=[REASON_FRAME_MISSED],
                            blendshapes=None,
                            pose_deg=None,
                        )
                        reasons_count[REASON_FRAME_MISSED] = (
                            reasons_count.get(REASON_FRAME_MISSED, 0) + 1
                        )
                        status_text = f"MISSED (Slot {slot.slot_index})"
                    else:
                        blendshapes, pose_deg, reasons, last_result = self.extractor.extract(
                            slot.frame, slot.frame_ms
                        )
                        is_valid = (
                            len(reasons) == 0 and blendshapes is not None and pose_deg is not None
                        )
                        slot_rec = SlotRecord(
                            schema_version=self.config.config_version,
                            session_id=self.session_id,
                            slot_index=slot.slot_index,
                            target_ms=slot.target_ms,
                            frame_ms=slot.frame_ms,
                            valid=is_valid,
                            reasons=reasons,
                            blendshapes=blendshapes if is_valid else None,
                            pose_deg=pose_deg if is_valid else None,
                        )
                        for r in reasons:
                            reasons_count[r] = reasons_count.get(r, 0) + 1
                        status_text = "VALID" if is_valid else f"INVALID ({','.join(reasons)})"

                    self.exporter.write_slot(slot_rec)
                    processed_slots.append(slot_rec)

                # Render GUI preview if enabled
                if self.config.preview:
                    measured_fps = len(processed_slots) / max(elapsed_s, 0.001)
                    current_slot_idx = processed_slots[-1].slot_index if processed_slots else 0
                    hud_frame = render_preview_overlay(
                        frame_bgr=frame_bgr,
                        detection_result=last_result,
                        slot_index=current_slot_idx,
                        elapsed_s=elapsed_s,
                        status_text=status_text,
                        fps=measured_fps,
                        mirror=self.config.preview_mirror,
                    )
                    cv2.imshow(window_name, hud_frame)
                    key = cv2.waitKey(1) & 0xFF
                    # 'q' or ESC (27) to cancel
                    if key in (ord("q"), 27):
                        print("\n[AI-FACE] User terminated session from preview window.")
                        self._cancelled = True
                        break

            # If not cancelled and session finished its duration, emit remaining slots as missed
            if not self._cancelled:
                final_slots = self.scheduler.finalize()
                for slot in final_slots:
                    slot_rec = SlotRecord(
                        schema_version=self.config.config_version,
                        session_id=self.session_id,
                        slot_index=slot.slot_index,
                        target_ms=slot.target_ms,
                        frame_ms=None,
                        valid=False,
                        reasons=[REASON_FRAME_MISSED],
                        blendshapes=None,
                        pose_deg=None,
                    )
                    reasons_count[REASON_FRAME_MISSED] = (
                        reasons_count.get(REASON_FRAME_MISSED, 0) + 1
                    )
                    self.exporter.write_slot(slot_rec)
                    processed_slots.append(slot_rec)

            if self._cancelled:
                status = STATUS_CANCELLED

        except Exception as e:
            print(f"\n[AI-FACE] Session encountered an error: {e}", file=sys.stderr)
            status = STATUS_FAILED
            raise
        finally:
            if self._prev_sigint is not None:
                signal.signal(signal.SIGINT, self._prev_sigint)

            if self.config.preview:
                cv2.destroyAllWindows()

            self.source.close()

        completed_at_dt = datetime.now(timezone.utc)
        actual_duration_s = max(time.monotonic() - t_start, 0.001)

        valid_count = sum(1 for s in processed_slots if s.valid)
        invalid_count = len(processed_slots) - valid_count
        nominal_slots = self.config.nominal_slots
        valid_ratio = round(valid_count / nominal_slots, 4) if nominal_slots > 0 else 0.0
        effective_rate_hz = round(valid_count / actual_duration_s, 2)

        # Run distress classification if classifier is configured
        estimation = EstimationStatus()
        if self.distress_classifier is not None:
            if status == STATUS_COMPLETED:
                estimation = self.distress_classifier.predict_session(
                    slots=processed_slots,
                    nominal_slots=nominal_slots,
                )
            else:
                estimation = EstimationStatus(
                    status="withheld",
                    reason=f"Session incomplete (status: '{status}')",
                )

        summary = SessionSummary(
            schema_version=self.config.config_version,
            config_version=self.config.config_version,
            session_id=self.session_id,
            status=status,
            source_type=self.source.get_metadata().source_type,
            source_identifier=self.source.get_metadata().source_identifier,
            created_at_utc=created_at_utc,
            completed_at_utc=completed_at_dt.isoformat(),
            target_duration_s=self.config.duration_s,
            actual_duration_s=round(actual_duration_s, 3),
            nominal_slots=nominal_slots,
            processed_slots=len(processed_slots),
            valid_slots=valid_count,
            invalid_slots=invalid_count,
            valid_ratio=valid_ratio,
            effective_rate_hz=effective_rate_hz,
            reasons_count=reasons_count,
            device_metadata=self.source.get_metadata(),
            model_metadata=self.extractor.get_metadata(),
            estimation=estimation,
        )

        final_path = self.exporter.finalize(summary)
        print(f"[AI-FACE] Session {self.session_id} finalized with status: '{status}'.")
        print(f"[AI-FACE] Output directory: {final_path.resolve()}")
        print(
            f"[AI-FACE] Slots: {valid_count}/{nominal_slots} valid "
            f"({valid_ratio * 100:.1f}%), Effective rate: {effective_rate_hz:.1f} Hz."
        )
        if estimation.status == "available":
            print(
                f"[AI-FACE] Distress Level: {estimation.level.upper()} "
                f"(Confidence: {estimation.confidence * 100:.1f}%)"
            )
            print(f"[AI-FACE] Class Probabilities: {estimation.probabilities}")
        elif estimation.status == "withheld":
            print(f"[AI-FACE] Distress Estimation: WITHHELD ({estimation.reason})")

        return summary
