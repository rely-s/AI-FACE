"""AI-FACE Command-Line Interface (CLI)."""

import argparse
import sys
import urllib.request
from pathlib import Path

from ai_face.classifier import (
    DEFAULT_DISTRESS_MODEL_PATH,
    DistressClassifier,
)
from ai_face.config import SessionConfig
from ai_face.constants import (
    DEFAULT_MODEL_PATH,
    OFFICIAL_MODEL_SHA256,
    OFFICIAL_MODEL_URL,
)
from ai_face.extractor import FaceLandmarkerExtractor, compute_file_sha256
from ai_face.image_processor import ImageDistressProcessor
from ai_face.session_runner import SessionRunner
from ai_face.source import VideoFileSource, WebcamSource


def download_official_model(dest_path: Path) -> None:
    """Download the official Google MediaPipe Face Landmarker model asset."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[AI-FACE] Downloading official model from:\n  {OFFICIAL_MODEL_URL}")
    print(f"[AI-FACE] Saving to: {dest_path.resolve()} ...")

    urllib.request.urlretrieve(OFFICIAL_MODEL_URL, dest_path)
    checksum = compute_file_sha256(dest_path)
    print(f"[AI-FACE] Model downloaded successfully. SHA-256: {checksum}")
    if checksum == OFFICIAL_MODEL_SHA256:
        print("[AI-FACE] Checksum verified: Match official release.")
    else:
        print(f"[AI-FACE] Warning: Checksum differs from expected ({OFFICIAL_MODEL_SHA256}).")


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate command line arguments."""
    parser = argparse.ArgumentParser(
        prog="ai-face",
        description=(
            "AI-FACE: Facial Feature Acquisition & Quality Monitoring for Distress Research.\n"
            "Captures 30-second sessions at 15 Hz nominal rate (450 slots) from webcam or video.\n"
            "Extracts 52 ARKit blendshapes and 3D head pose (yaw, pitch, roll in degrees)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  1. Live acquisition from default webcam:
     ai-face --camera-index 0

  2. Automated headless extraction from a local video file:
     ai-face --video ./sample.mp4 --headless --output-dir ./output

  3. Custom session duration and custom output directory:
     ai-face --camera-index 0 --duration 10.0 --fps 15.0 --output-dir ./sessions

  4. Download the official MediaPipe Face Landmarker task model:
     ai-face --download-model

Keybindings:
  During webcam preview, press 'q' or 'ESC' to gracefully terminate and export session.
  Press Ctrl+C in terminal at any time for graceful shutdown.
""",
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--camera-index",
        type=int,
        default=None,
        metavar="INT",
        help="Webcam device index (e.g. 0 for default integrated webcam / Logitech C922).",
    )
    input_group.add_argument(
        "--video",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to local video file for offline or automated testing.",
    )
    input_group.add_argument(
        "--image",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to a single face photo/image to classify distress and emotions directly.",
    )
    input_group.add_argument(
        "--image-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Path to a folder of face photos for batch dataset processing and classification.",
    )

    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path(DEFAULT_MODEL_PATH),
        metavar="PATH",
        help=f"Path to MediaPipe face_landmarker.task model (default: '{DEFAULT_MODEL_PATH}').",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        metavar="DIR",
        help="Root output directory where session folder will be created (default: 'output').",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        metavar="UUID",
        help="Optional explicit session UUID. If omitted, a fresh UUIDv4 is generated.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="Session target acquisition duration in seconds (default: 30.0).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=15.0,
        metavar="HZ",
        help="Target extraction sampling rate in Hz (default: 15.0).",
    )
    parser.add_argument(
        "--headless",
        "--no-preview",
        action="store_true",
        dest="headless",
        help="Disable GUI preview window. Recommended for automated tests and headless servers.",
    )
    parser.add_argument(
        "--no-mirror",
        action="store_true",
        dest="no_mirror",
        help="Disable horizontal flip in GUI preview window.",
    )
    parser.add_argument(
        "--allow-multiple-faces",
        action="store_true",
        help="Permit processing even if multiple faces are observed in the frame.",
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Run offline distress level classification model on session features.",
    )
    parser.add_argument(
        "--distress-model",
        type=Path,
        default=Path(DEFAULT_DISTRESS_MODEL_PATH),
        metavar="PATH",
        help=f"Path to distress model file (default: {DEFAULT_DISTRESS_MODEL_PATH}).",
    )
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="Download the official Google MediaPipe face_landmarker.task model and exit.",
    )
    parser.add_argument(
        "--train-from-photos",
        type=Path,
        default=None,
        metavar="DIR",
        help="Train an XGBoost classifier from a folder of class subdirectories with face photos.",
    )
    parser.add_argument(
        "--photo-model-out",
        type=Path,
        default=Path("models/photo_distress_classifier.joblib"),
        metavar="PATH",
        help="Output path for trained photo model.",
    )
    parser.add_argument(
        "--train-stressid",
        type=Path,
        default=None,
        metavar="PATH_OR_DIR",
        help="Train an experimental face distress model from the StressID repository/dataset.",
    )
    parser.add_argument(
        "--stressid-protocol",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to StressID protocol.txt with author-defined binary labels.",
    )
    parser.add_argument(
        "--stressid-model-type",
        type=str,
        default="xgboost",
        choices=["xgboost", "random_forest", "logistic_regression"],
        help="Classifier model architecture for StressID (default: 'xgboost').",
    )
    parser.add_argument(
        "--stressid-splits",
        type=int,
        default=5,
        metavar="N",
        help="Number of Leave-Subjects-Out (GroupKFold) cross-validation folds (default: 5).",
    )
    parser.add_argument(
        "--stressid-out",
        type=Path,
        default=Path("models/stressid_face_model.joblib"),
        metavar="PATH",
        help="Output path for trained StressID model bundle.",
    )
    parser.add_argument(
        "--stressid-report-out",
        type=Path,
        default=Path("output/stressid_evaluation_report.json"),
        metavar="PATH",
        help="Output path for StressID Leave-Subjects-Out evaluation report.",
    )
    parser.add_argument(
        "--show-emotions",
        action="store_true",
        help="Display emotion bars and radar dial (default: False, shows clinical FACS only).",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start the interactive AI-FACE Clinical Web Platform in the browser.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        metavar="PORT",
        help="Port to bind the web server (default: 8000).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the web browser on server startup.",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """CLI application entry point."""
    parsed = parse_arguments(args)

    if parsed.download_model:
        download_official_model(parsed.model_path)
        return 0

    if parsed.train_from_photos is not None:
        from ai_face.training.train_photo_classifier import train_photo_classifier

        try:
            train_photo_classifier(
                dataset_dir=parsed.train_from_photos,
                output_model_path=parsed.photo_model_out,
            )
            return 0
        except Exception as e:
            print(f"[AI-FACE] Training failed: {e}", file=sys.stderr)
            return 1

    if parsed.train_stressid is not None:
        from ai_face.training.train_stressid import train_and_save_stressid_model

        try:
            target = parsed.train_stressid
            if target.is_dir():
                feat_dir = target / "Feature Extraction" / "Features"
                features_candidate = feat_dir / "video11tasks_aus_gaze_morestats.csv"
                if not features_candidate.is_file():
                    features_candidate = feat_dir / "video11tasks_aus_gaze_mean_std.csv"
                protocol_candidate = target / "Feature Extraction" / "audio" / "protocol.txt"
            else:
                features_candidate = target
                protocol_candidate = parsed.stressid_protocol

            proto_path = parsed.stressid_protocol or (
                protocol_candidate
                if protocol_candidate and protocol_candidate.is_file()
                else None
            )

            print(f"[AI-FACE] Loading StressID features from: {features_candidate}")
            if proto_path:
                print(f"[AI-FACE] Using verified author labels from: {proto_path}")

            report = train_and_save_stressid_model(
                features_csv=features_candidate,
                protocol_txt=proto_path,
                model_type=parsed.stressid_model_type,
                n_splits=parsed.stressid_splits,
                output_model_path=parsed.stressid_out,
                output_report_path=parsed.stressid_report_out,
            )

            print("\n[AI-FACE] === StressID Unseen-Person Evaluation Report ===")
            print(f"  Model Architecture : {report.model_name.upper()}")
            print(
                f"  Leave-Subjects-Out : {report.n_splits} folds across "
                f"{report.total_subjects} subjects"
            )
            print(
                f"  Total 30s Windows  : {report.total_windows} windows across "
                f"{report.total_tasks} tasks"
            )
            print(f"  Class Distribution : {report.class_distribution}")
            print(
                f"  Mean Accuracy      : {report.mean_accuracy * 100:.2f}% ± "
                f"{report.std_accuracy * 100:.2f}%"
            )
            print(
                f"  Balanced Accuracy  : {report.mean_balanced_accuracy * 100:.2f}% ± "
                f"{report.std_balanced_accuracy * 100:.2f}%"
            )
            print(f"  Macro F1-Score     : {report.mean_f1_macro:.4f} ± {report.std_f1_macro:.4f}")
            print(
                f"  Binary F1-Score    : {report.mean_f1_binary:.4f} ± "
                f"{report.std_f1_binary:.4f}"
            )
            print(f"  Mean ROC-AUC       : {report.mean_roc_auc:.4f}")

            if report.top_facial_features:
                print("\n[AI-FACE] Top 5 Predictive Facial Features (Action Units / Gaze):")
                for item in report.top_facial_features[:5]:
                    print(f"    #{item['rank']} {item['feature']:28s} : {item['importance']:.4f}")

            print(f"\n[AI-FACE] Model bundle saved to: {parsed.stressid_out}")
            print(f"[AI-FACE] Full report saved to : {parsed.stressid_report_out}")
            return 0
        except Exception as e:
            print(f"[AI-FACE] StressID training failed: {e}", file=sys.stderr)
            return 1

    if parsed.web:
        from ai_face.web.server import run_server

        try:
            run_server(
                port=parsed.port,
                model_path=parsed.model_path,
                auto_open=not parsed.no_browser,
            )
            return 0
        except Exception as e:
            print(f"[AI-FACE] Web server error: {e}", file=sys.stderr)
            return 1

    if (
        parsed.camera_index is None
        and parsed.video is None
        and parsed.image is None
        and parsed.image_dir is None
    ):
        print(
            "Error: Specify one of: '--web', '--camera-index', '--video', "
            "'--image', or '--image-dir'.\n"
            "Use 'ai-face --help' to see usage examples.",
            file=sys.stderr,
        )
        return 1

    # Verify model presence
    if not parsed.model_path.is_file():
        print(
            f"Error: Face landmarker model not found at '{parsed.model_path.resolve()}'.\n"
            f"Please download the official model using:\n"
            f"  ai-face --download-model --model-path {parsed.model_path}\n"
            f"Or download directly from:\n  {OFFICIAL_MODEL_URL}\n",
            file=sys.stderr,
        )
        return 1

    # Handle image mode (single photo or photo directory)
    if parsed.image is not None or parsed.image_dir is not None:
        try:
            processor = ImageDistressProcessor(model_path=parsed.model_path)
            if parsed.image is not None:
                res = processor.process_file(
                    image_path=parsed.image,
                    output_dir=parsed.output_dir,
                    save_annotated=True,
                    show_emotions=parsed.show_emotions,
                )
                print(f"[AI-FACE] Image: {res['image_name']}")
                print(f"[AI-FACE] Face Detected: {res['face_detected']}")
                level = res["distress_level"]
                score = res["distress_score"]
                print(f"[AI-FACE] Distress Level: {level} (Score: {score})")
                if res.get("emotions"):
                    print(f"[AI-FACE] Emotions: {res['emotions']}")
                if res.get("dass_clinical_assessment"):
                    dass = res["dass_clinical_assessment"]
                    print("[AI-FACE] Clinical DASS-3 Assessment (Gavrilescu 2019):")
                    dep = dass["depression"]
                    anx = dass["anxiety"]
                    stress = dass["stress"]
                    print(f"  - Depression : {dep['level'].upper()} (Score: {dep['score']:.3f})")
                    print(f"  - Anxiety    : {anx['level'].upper()} (Score: {anx['score']:.3f})")
                    str_score = stress["score"]
                    print(f"  - Stress     : {stress['level'].upper()} (Score: {str_score:.3f})")
                if res.get("annotated_image_path"):
                    print(f"[AI-FACE] Visual Feedback Image: {res['annotated_image_path']}")
            else:
                processor.process_directory(
                    directory_path=parsed.image_dir,
                    output_dir=parsed.output_dir,
                    save_annotated=True,
                    show_emotions=parsed.show_emotions,
                )
            processor.close()
            return 0
        except Exception as e:
            print(f"[AI-FACE] Image processing error: {e}", file=sys.stderr)
            return 1

    # Default preview is disabled in headless mode
    is_preview = not parsed.headless

    config = SessionConfig(
        duration_s=parsed.duration,
        target_fps=parsed.fps,
        allow_multiple_faces=parsed.allow_multiple_faces,
        output_dir=parsed.output_dir,
        model_path=parsed.model_path,
        preview=is_preview,
        preview_mirror=not parsed.no_mirror,
        show_emotions=parsed.show_emotions,
    )

    try:
        if parsed.camera_index is not None:
            source = WebcamSource(camera_index=parsed.camera_index)
        else:
            source = VideoFileSource(video_path=parsed.video)
    except Exception as e:
        print(f"[AI-FACE] Failed to initialize input source: {e}", file=sys.stderr)
        return 1

    try:
        extractor = FaceLandmarkerExtractor(
            model_path=config.model_path,
            thresholds=config.quality,
            allow_multiple_faces=config.allow_multiple_faces,
        )
    except Exception as e:
        source.close()
        print(f"[AI-FACE] Failed to initialize feature extractor: {e}", file=sys.stderr)
        return 1

    distress_classifier = None
    if parsed.classify or (
        parsed.distress_model.is_file()
        and parsed.distress_model != Path(DEFAULT_DISTRESS_MODEL_PATH)
    ):
        try:
            distress_classifier = DistressClassifier(model_path=parsed.distress_model)
        except Exception as e:
            print(
                f"[AI-FACE] Warning: Could not initialize distress classifier: {e}", file=sys.stderr
            )

    try:
        runner = SessionRunner(
            config=config,
            source=source,
            extractor=extractor,
            distress_classifier=distress_classifier,
            session_id=parsed.session_id,
        )
        summary = runner.run()
        return 0 if summary.status in ("completed", "cancelled") else 1
    except Exception as e:
        print(f"[AI-FACE] Execution error: {e}", file=sys.stderr)
        return 1
    finally:
        extractor.close()


if __name__ == "__main__":
    sys.exit(main())
