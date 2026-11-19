"""Distress classifier inference engine for session-level predictions."""

import json
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np

from ai_face.features import aggregate_session_features
from ai_face.models import EstimationStatus, SlotRecord

DEFAULT_DISTRESS_MODEL_PATH = "models/distress_classifier.joblib"
DEFAULT_DISTRESS_META_PATH = "models/distress_classifier_meta.json"

DISTRESS_LABELS = {
    0: "low_distress",
    1: "moderate_distress",
    2: "high_distress",
}


class DistressClassifier:
    """Predicts distress level from session facial movement features."""

    def __init__(
        self,
        model_path: str | Path = DEFAULT_DISTRESS_MODEL_PATH,
        meta_path: str | Path = DEFAULT_DISTRESS_META_PATH,
    ) -> None:
        self.model_path = Path(model_path)
        self.meta_path = Path(meta_path)

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Distress classifier model not found at '{self.model_path.resolve()}'. "
                "Please run training first: 'python -m ai_face.training.train_distress'."
            )

        self.model = joblib.load(self.model_path)
        self.metadata = {}
        if self.meta_path.is_file():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

        self.version = self.metadata.get("version", "distress_xgb_v1")

    def predict_session(
        self,
        slots: Sequence[SlotRecord],
        nominal_slots: int = 450,
        min_valid_ratio: float = 0.70,
    ) -> EstimationStatus:
        """Run distress inference on session slot records.

        Enforces quality gate: if valid ratio is below min_valid_ratio, output is withheld.
        """
        valid_slots = [s for s in slots if s.valid]
        valid_ratio = len(valid_slots) / max(nominal_slots, 1)

        if valid_ratio < min_valid_ratio:
            pct_valid = valid_ratio * 100.0
            pct_req = min_valid_ratio * 100.0
            return EstimationStatus(
                status="withheld",
                level=None,
                confidence=None,
                probabilities=None,
                model_version=self.version,
                reason=(
                    f"Insufficient valid slots ({len(valid_slots)}/{nominal_slots} = "
                    f"{pct_valid:.1f}% < {pct_req:.0f}% required). Prediction withheld for safety."
                ),
            )

        features = aggregate_session_features(slots)
        if features is None:
            return EstimationStatus(
                status="withheld",
                level=None,
                confidence=None,
                probabilities=None,
                model_version=self.version,
                reason="Feature extraction failed due to sparse observations.",
            )

        x_input = features.reshape(1, -1)
        probas = self.model.predict_proba(x_input)[0]
        pred_idx = int(np.argmax(probas))
        confidence = float(probas[pred_idx])

        pred_label = DISTRESS_LABELS.get(pred_idx, f"level_{pred_idx}")
        prob_dict = {
            DISTRESS_LABELS.get(i, f"level_{i}"): round(float(p), 4) for i, p in enumerate(probas)
        }

        return EstimationStatus(
            status="available",
            level=pred_label,
            confidence=round(confidence, 4),
            probabilities=prob_dict,
            model_version=self.version,
            reason=None,
        )
