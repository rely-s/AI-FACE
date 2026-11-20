"""Training and evaluation pipeline for StressID Facial Video models.

Trains facial Action Unit distress classifiers using author-defined binary labels,
30-second windows, and strict Leave-Subjects-Out (GroupKFold) cross-validation.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ai_face.training.stressid_dataset import StressIDDataset, build_stressid_dataset


@dataclass
class FoldMetrics:
    """Evaluation metrics for a single Leave-Subjects-Out fold."""

    fold: int
    n_train_samples: int
    n_test_samples: int
    n_test_subjects: int
    accuracy: float
    balanced_accuracy: float
    f1_macro: float
    f1_binary: float
    precision: float
    recall: float
    roc_auc: float
    confusion_matrix: list[list[int]]


@dataclass
class StressIDTrainingReport:
    """Comprehensive training report across all Leave-Subjects-Out folds."""

    model_name: str
    n_splits: int
    total_windows: int
    total_subjects: int
    total_tasks: int
    class_distribution: dict[str, int]
    mean_accuracy: float
    std_accuracy: float
    mean_balanced_accuracy: float
    std_balanced_accuracy: float
    mean_f1_macro: float
    std_f1_macro: float
    mean_f1_binary: float
    std_f1_binary: float
    mean_roc_auc: float
    fold_details: list[FoldMetrics]
    top_facial_features: list[dict[str, Any]]


def create_classifier(model_type: str = "xgboost", random_state: int = 42) -> Any:
    """Instantiate a classification model."""
    m_type = model_type.lower()
    if m_type == "xgboost":
        return XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            eval_metric="logloss",
        )
    elif m_type in ("random_forest", "rf"):
        return RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_split=4,
            random_state=random_state,
        )
    elif m_type in ("logistic_regression", "lr"):
        return LogisticRegression(
            max_iter=1000,
            C=0.1,
            penalty="l2",
            random_state=random_state,
        )
    else:
        raise ValueError(
            f"Unsupported model_type: '{model_type}'. "
            "Choose 'xgboost', 'random_forest', or 'logistic_regression'."
        )


def evaluate_stressid_cv(
    dataset: StressIDDataset,
    model_type: str = "xgboost",
    n_splits: int = 5,
    random_state: int = 42,
) -> tuple[StressIDTrainingReport, Any, Any]:
    """Perform Leave-Subjects-Out cross validation and train final model."""
    splits = dataset.get_splits(n_splits=n_splits)

    fold_metrics_list: list[FoldMetrics] = []

    for fold_i, (train_idx, test_idx) in enumerate(splits, start=1):
        X_train, X_test = dataset.X[train_idx], dataset.X[test_idx]
        y_train, y_test = dataset.y[train_idx], dataset.y[test_idx]

        scaler = None
        if model_type.lower() in ("logistic_regression", "lr"):
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)

        clf = create_classifier(model_type=model_type, random_state=random_state)
        clf.fit(X_train, y_train)

        preds = clf.predict(X_test)

        # ROC-AUC computation
        roc_auc = 0.5
        try:
            if hasattr(clf, "predict_proba"):
                probs = clf.predict_proba(X_test)[:, 1]
                roc_auc = float(roc_auc_score(y_test, probs))
        except Exception:
            roc_auc = float(balanced_accuracy_score(y_test, preds))

        cm = confusion_matrix(y_test, preds, labels=[0, 1]).tolist()
        test_subjs = len(np.unique(dataset.groups[test_idx]))

        fold_metrics_list.append(
            FoldMetrics(
                fold=fold_i,
                n_train_samples=len(train_idx),
                n_test_samples=len(test_idx),
                n_test_subjects=test_subjs,
                accuracy=float(accuracy_score(y_test, preds)),
                balanced_accuracy=float(balanced_accuracy_score(y_test, preds)),
                f1_macro=float(f1_score(y_test, preds, average="macro", zero_division=0)),
                f1_binary=float(f1_score(y_test, preds, average="binary", zero_division=0)),
                precision=float(precision_score(y_test, preds, zero_division=0)),
                recall=float(recall_score(y_test, preds, zero_division=0)),
                roc_auc=roc_auc,
                confusion_matrix=cm,
            )
        )

    # Train final production model on all data
    final_scaler = None
    X_all = dataset.X
    if model_type.lower() in ("logistic_regression", "lr"):
        final_scaler = StandardScaler()
        X_all = final_scaler.fit_transform(X_all)

    final_model = create_classifier(model_type=model_type, random_state=random_state)
    final_model.fit(X_all, dataset.y)

    # Extract feature importances
    top_features: list[dict[str, Any]] = []
    if hasattr(final_model, "feature_importances_"):
        importances = final_model.feature_importances_
        sorted_indices = np.argsort(importances)[::-1][:20]
        for rank, idx in enumerate(sorted_indices, start=1):
            if idx < len(dataset.feature_names):
                feat_name = dataset.feature_names[idx]
            else:
                feat_name = f"Feat_{idx}"
            top_features.append(
                {
                    "rank": rank,
                    "feature": feat_name,
                    "importance": float(importances[idx]),
                }
            )

    c0 = int(np.sum(dataset.y == 0))
    c1 = int(np.sum(dataset.y == 1))

    report = StressIDTrainingReport(
        model_name=model_type,
        n_splits=len(splits),
        total_windows=len(dataset.X),
        total_subjects=len(dataset.subject_ids),
        total_tasks=len(dataset.task_ids),
        class_distribution={"0_not_stressed": c0, "1_stressed": c1},
        mean_accuracy=float(np.mean([m.accuracy for m in fold_metrics_list])),
        std_accuracy=float(np.std([m.accuracy for m in fold_metrics_list])),
        mean_balanced_accuracy=float(np.mean([m.balanced_accuracy for m in fold_metrics_list])),
        std_balanced_accuracy=float(np.std([m.balanced_accuracy for m in fold_metrics_list])),
        mean_f1_macro=float(np.mean([m.f1_macro for m in fold_metrics_list])),
        std_f1_macro=float(np.std([m.f1_macro for m in fold_metrics_list])),
        mean_f1_binary=float(np.mean([m.f1_binary for m in fold_metrics_list])),
        std_f1_binary=float(np.std([m.f1_binary for m in fold_metrics_list])),
        mean_roc_auc=float(np.mean([m.roc_auc for m in fold_metrics_list])),
        fold_details=fold_metrics_list,
        top_facial_features=top_features,
    )

    return report, final_model, final_scaler


def train_and_save_stressid_model(
    features_csv: str | Path,
    protocol_txt: str | Path | None = None,
    model_type: str = "xgboost",
    n_splits: int = 5,
    output_model_path: str | Path = "models/stressid_face_model.joblib",
    output_report_path: str | Path = "output/stressid_evaluation_report.json",
) -> StressIDTrainingReport:
    """High-level runner: build dataset, train, evaluate, and save artifacts."""
    dataset = build_stressid_dataset(
        features_csv=features_csv,
        protocol_txt=protocol_txt,
        window_sec=30.0,
    )

    report, model, scaler = evaluate_stressid_cv(
        dataset=dataset,
        model_type=model_type,
        n_splits=n_splits,
    )

    # Save model bundle
    out_model_p = Path(output_model_path)
    out_model_p.parent.mkdir(parents=True, exist_ok=True)

    bundle = {
        "model": model,
        "scaler": scaler,
        "model_type": model_type,
        "feature_names": dataset.feature_names,
        "n_features": len(dataset.feature_names),
        "top_features": report.top_facial_features,
        "performance": {
            "mean_accuracy": report.mean_accuracy,
            "mean_balanced_accuracy": report.mean_balanced_accuracy,
            "mean_f1_macro": report.mean_f1_macro,
            "mean_f1_binary": report.mean_f1_binary,
            "mean_roc_auc": report.mean_roc_auc,
        },
    }
    joblib.dump(bundle, out_model_p)

    # Save JSON report
    out_report_p = Path(output_report_path)
    out_report_p.parent.mkdir(parents=True, exist_ok=True)
    with out_report_p.open("w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2)

    return report
