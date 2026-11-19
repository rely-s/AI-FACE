"""Train distress and emotion classifiers directly from labeled face photo datasets.

Supports directory-per-class layout:
  dataset_dir/
    normal/
      img1.jpg, img2.png ...
    mild/
      ...
    moderate/
      ...
    severe/
      ...
    extremely_severe/
      ...
Or manifest CSV:
  image_path,label
"""

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import xgboost as xgb
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold

from ai_face.constants import FROZEN_BLENDSHAPE_NAMES
from ai_face.facs_dass import FACS_31_AUS
from ai_face.image_processor import ImageDistressProcessor

DEFAULT_PHOTO_MODEL_PATH = "models/photo_distress_classifier.joblib"
DEFAULT_PHOTO_META_PATH = "models/photo_distress_classifier_meta.json"


def get_photo_feature_names() -> list[str]:
    """Return feature vector schema for photo classification: 52 blendshapes + 31 FACS AUs."""
    names = [f"bs_{b}" for b in FROZEN_BLENDSHAPE_NAMES]
    names.extend([f"facs_{au}" for au in sorted(FACS_31_AUS)])
    return names


def extract_features_from_image(
    processor: ImageDistressProcessor,
    img_path: Path,
) -> np.ndarray | None:
    """Extract 83-dimensional feature vector from a single photo."""
    blendshapes, _, _, facs_aus, _ = processor.process_image(
        img_bgr=cv2_imread(img_path),
        subject_id=img_path.stem,
    )
    if blendshapes is None or facs_aus is None:
        return None

    vec = []
    # 52 blendshapes
    for b in FROZEN_BLENDSHAPE_NAMES:
        vec.append(blendshapes.get(b, 0.0))
    # 31 FACS AUs
    for au in sorted(FACS_31_AUS):
        vec.append(facs_aus.get(au, 0.0))

    return np.array(vec, dtype=np.float32)


def cv2_imread(path: Path) -> Any:
    import cv2

    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not load image: {path}")
    return img


def load_dataset_from_directory(
    dataset_dir: str | Path,
    processor: ImageDistressProcessor,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Scan directory structure for class folders and extract features from images.

    Returns:
      (X, y, class_names, valid_image_paths)
    """
    root = Path(dataset_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"Dataset root directory not found: {root}")

    # Discover classes as subdirectories
    classes = sorted([d.name for d in root.iterdir() if d.is_dir()])
    if not classes:
        raise ValueError(f"No class subdirectories found in: {root}")

    class_to_idx = {cls_name: i for i, cls_name in enumerate(classes)}
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")

    x_list = []
    y_list = []
    valid_paths = []

    print(f"[AI-FACE] Discovered {len(classes)} classes: {classes}")

    for cls_name in classes:
        cls_dir = root / cls_name
        cls_idx = class_to_idx[cls_name]
        files = []
        for ext in extensions:
            files.extend(cls_dir.glob(ext))
            files.extend(cls_dir.glob(ext.upper()))
        files = sorted(list(set(files)))
        print(f"  Class '{cls_name}': {len(files)} candidate photos")

        for f in files:
            try:
                feat = extract_features_from_image(processor, f)
                if feat is not None:
                    x_list.append(feat)
                    y_list.append(cls_idx)
                    valid_paths.append(str(f))
                else:
                    print(f"    [SKIP - No Face] {f.name}")
            except Exception as e:
                print(f"    [SKIP - Error] {f.name}: {e}")

    if not x_list:
        raise ValueError(f"No valid face images found in dataset: {root}")

    X = np.vstack(x_list)
    y = np.array(y_list, dtype=np.int32)
    return X, y, classes, valid_paths


def train_photo_classifier(
    dataset_dir: str | Path,
    output_model_path: str | Path = DEFAULT_PHOTO_MODEL_PATH,
    output_meta_path: str | Path = DEFAULT_PHOTO_META_PATH,
    random_state: int = 42,
) -> dict[str, Any]:
    """Train XGBoost classifier from photo dataset with cross-validation."""
    processor = ImageDistressProcessor()
    try:
        X, y, classes, image_paths = load_dataset_from_directory(dataset_dir, processor)
    finally:
        processor.close()

    n_samples, n_features = X.shape
    unique_classes, counts = np.unique(y, return_counts=True)
    print(f"[AI-FACE] Training dataset shape: {X.shape}")
    print(f"[AI-FACE] Class distribution: {dict(zip(classes, counts.tolist(), strict=False))}")

    # Stratified K-Fold CV (or train/test split if few samples)
    min_class_samples = int(np.min(counts))
    n_splits = min(5, min_class_samples) if min_class_samples >= 2 else 2

    cv_scores = []
    if min_class_samples >= 2:
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            x_train, y_train = X[train_idx], y[train_idx]
            x_val, y_val = X[val_idx], y[val_idx]

            clf = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=random_state + fold,
                eval_metric="mlogloss" if len(classes) > 2 else "logloss",
            )
            clf.fit(x_train, y_train)
            acc = float(np.mean(clf.predict(x_val) == y_val))
            cv_scores.append(acc)
            print(f"  Fold {fold + 1}/{n_splits} Balanced Accuracy: {acc:.3f}")

    # Train final model on all data
    final_model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=random_state,
        eval_metric="mlogloss" if len(classes) > 2 else "logloss",
    )
    final_model.fit(X, y)

    y_pred = final_model.predict(X)
    report = classification_report(y, y_pred, target_names=classes, output_dict=True)

    # Save model and metadata
    out_model = Path(output_model_path)
    out_model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, out_model)

    metadata: dict[str, Any] = {
        "model_type": "xgboost_photo_distress_classifier",
        "num_samples": n_samples,
        "num_features": n_features,
        "classes": classes,
        "features": get_photo_feature_names(),
        "cv_accuracy_mean": float(np.mean(cv_scores)) if cv_scores else None,
        "cv_accuracy_std": float(np.std(cv_scores)) if cv_scores else None,
        "classification_report": report,
    }

    out_meta = Path(output_meta_path)
    with open(out_meta, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"[AI-FACE] Final Photo Model saved to {out_model.resolve()}")
    print(f"[AI-FACE] Model metadata saved to {out_meta.resolve()}")

    return metadata
