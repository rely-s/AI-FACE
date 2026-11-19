"""Atomic file exporter for session features (JSONL) and summary (JSON)."""

import json
import shutil
from pathlib import Path
from typing import TextIO

from ai_face.models import SessionSummary, SlotRecord


class SessionExporter:
    """Manages atomic writing of session data to output directories."""

    def __init__(self, base_output_dir: Path, session_id: str) -> None:
        self.base_output_dir = Path(base_output_dir)
        self.session_id = session_id

        self.final_dir = self.base_output_dir / self.session_id
        self.staging_dir = self.base_output_dir / f"{self.session_id}.tmp"

        self._features_file: TextIO | None = None
        self._features_path: Path | None = None
        self._summary_path: Path | None = None
        self._is_open: bool = False

    def open(self) -> None:
        """Create staging directory and open streaming features file."""
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

        # Clean any stale staging dir
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self._features_path = self.staging_dir / "features.jsonl"
        self._summary_path = self.staging_dir / "session_summary.json"
        self._features_file = open(self._features_path, "w", encoding="utf-8")
        self._is_open = True

    def write_slot(self, slot: SlotRecord) -> None:
        """Append a slot record to the features JSONL file."""
        if not self._is_open or self._features_file is None:
            raise RuntimeError("Exporter is not open for writing.")

        line = slot.model_dump_json(exclude_none=False)
        self._features_file.write(line + "\n")

    def finalize(self, summary: SessionSummary) -> Path:
        """Flush features, write summary JSON, validate, and atomically move staging to final."""
        if self._features_file is not None and not self._features_file.closed:
            self._features_file.flush()
            self._features_file.close()
            self._is_open = False

        if self._summary_path is None:
            raise RuntimeError("Exporter was never opened.")

        # Write summary JSON
        with open(self._summary_path, "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2)

        # Atomic promotion: rename staging_dir to final_dir
        if self.final_dir.exists():
            shutil.rmtree(self.final_dir)

        self.staging_dir.rename(self.final_dir)
        return self.final_dir

    def discard(self) -> None:
        """Clean up staging directory in case of unrecoverable failure or abort."""
        if self._features_file is not None and not self._features_file.closed:
            self._features_file.close()
            self._is_open = False

        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir, ignore_errors=True)
