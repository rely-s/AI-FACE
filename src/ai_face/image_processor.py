"""Single-image and batch photo dataset processor for emotion and distress classification."""

import csv
import json
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from ai_face.constants import DEFAULT_MODEL_PATH
from ai_face.facs_dass import DASSResult, map_blendshapes_to_facs_aus, predict_dass_from_aus
from ai_face.single_frame_classifier import FrameEmotionResult, evaluate_frame_emotions
from ai_face.visualizer import render_shore_style_overlay

ImageProcessTuple = tuple[
    dict[str, float] | None,
    FrameEmotionResult | None,
    DASSResult | None,
    dict[str, float] | None,
    Any,
]


class ImageDistressProcessor:
    """Processes static face photos to extract features and classify distress/emotions."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Model file not found at: {self.model_path}")

        base_options = python.BaseOptions(model_asset_path=str(self.model_path))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

    def process_image(
        self,
        img_bgr: cv2.typing.MatLike,
        subject_id: str = "Subject",
    ) -> ImageProcessTuple:
        """Extract features, emotions, FACS AUs, and DASS assessment from a single BGR image."""
        rgb_img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)

        result = self.detector.detect(mp_image)

        if not result.face_landmarks or not result.face_blendshapes:
            return None, None, None, None, result

        blendshapes_dict = {b.category_name: float(b.score) for b in result.face_blendshapes[0]}
        emotions = evaluate_frame_emotions(blendshapes_dict)
        facs_aus = map_blendshapes_to_facs_aus(blendshapes_dict)
        dass = predict_dass_from_aus(facs_aus)

        return blendshapes_dict, emotions, dass, facs_aus, result

    def process_file(
        self,
        image_path: str | Path,
        output_dir: str | Path | None = None,
        save_annotated: bool = True,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a local image file and optionally save annotated visual feedback."""
        img_path = Path(image_path)
        if not img_path.is_file():
            raise FileNotFoundError(f"Image not found: {img_path}")

        img = cv2.imread(str(img_path))
        if img is None:
            raise RuntimeError(f"Could not decode image at {img_path}")

        sub_id = subject_id or img_path.stem
        blendshapes, emotions, dass, facs_aus, result = self.process_image(img, subject_id=sub_id)

        response: dict[str, Any] = {
            "image_name": img_path.name,
            "face_detected": emotions is not None,
            "distress_level": emotions.distress_level if emotions else "NO_FACE",
            "distress_score": emotions.distress_score if emotions else None,
            "emotions": {
                "happy": emotions.happy,
                "sad": emotions.sad,
                "angry": emotions.angry,
                "surprised": emotions.surprised,
                "neutral": emotions.neutral,
                "valence": emotions.valence,
            }
            if emotions
            else None,
            "dass_clinical_assessment": {
                "depression": {"score": dass.depression.score, "level": dass.depression.level},
                "anxiety": {"score": dass.anxiety.score, "level": dass.anxiety.level},
                "stress": {"score": dass.stress.score, "level": dass.stress.level},
            }
            if dass
            else None,
            "facs_action_units": facs_aus,
        }

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            # Save JSON result
            json_path = out_dir / f"{img_path.stem}_result.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2)

            # Save annotated image
            if save_annotated:
                annotated = render_shore_style_overlay(
                    frame_bgr=img,
                    detection_result=result,
                    emotions=emotions,
                    dass=dass,
                    subject_id=sub_id,
                )
                annotated_path = out_dir / f"annotated_{img_path.stem}.jpg"
                cv2.imwrite(str(annotated_path), annotated)
                response["annotated_image_path"] = str(annotated_path)

        return response

    def process_directory(
        self,
        directory_path: str | Path,
        output_dir: str | Path,
        save_annotated: bool = True,
    ) -> list[dict[str, Any]]:
        """Process all images in a folder and compile a dataset report."""
        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")
        files = []
        for ext in extensions:
            files.extend(dir_path.glob(ext))
            files.extend(dir_path.glob(ext.upper()))
        files = sorted(list(set(files)))

        results = []
        print(f"[AI-FACE] Processing {len(files)} photos in {dir_path.resolve()}...")
        for f in files:
            res = self.process_file(
                image_path=f,
                output_dir=output_dir,
                save_annotated=save_annotated,
            )
            results.append(res)
            dist_txt = res.get("distress_level", "UNKNOWN")
            print(f"  -> {f.name}: {dist_txt}")

        # Save summary JSON
        summary_path = Path(output_dir) / "batch_image_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[AI-FACE] Batch dataset summary saved to {summary_path.resolve()}")

        # Save clinical DASS summary CSV
        csv_path = Path(output_dir) / "batch_dass_summary.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "image_name",
                    "face_detected",
                    "distress_level",
                    "distress_score",
                    "depression_level",
                    "depression_score",
                    "anxiety_level",
                    "anxiety_score",
                    "stress_level",
                    "stress_score",
                    "valence",
                ]
            )
            for r in results:
                dass_data = r.get("dass_clinical_assessment") or {}
                dep = dass_data.get("depression", {})
                anx = dass_data.get("anxiety", {})
                str_ = dass_data.get("stress", {})
                emo = r.get("emotions") or {}
                writer.writerow(
                    [
                        r["image_name"],
                        r["face_detected"],
                        r.get("distress_level", "NO_FACE"),
                        r.get("distress_score") if r.get("distress_score") is not None else "",
                        dep.get("level", ""),
                        f"{dep.get('score', 0.0):.3f}" if "score" in dep else "",
                        anx.get("level", ""),
                        f"{anx.get('score', 0.0):.3f}" if "score" in anx else "",
                        str_.get("level", ""),
                        f"{str_.get('score', 0.0):.3f}" if "score" in str_ else "",
                        f"{emo.get('valence', 0.0):.3f}" if "valence" in emo else "",
                    ]
                )
        print(f"[AI-FACE] Batch DASS CSV summary saved to {csv_path.resolve()}")

        return results

    def close(self) -> None:
        if hasattr(self, "detector") and self.detector is not None:
            self.detector.close()
