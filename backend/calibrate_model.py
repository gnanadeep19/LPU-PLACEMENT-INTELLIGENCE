"""Evaluate and build calibrated readiness probabilities.

This command requires explicit duplicate approval because it uses the
canonical primary dataset. It writes a calibration report and a separate
calibrated artifact; it does not replace the deployed artifact implicitly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, log_loss, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_pipeline import load_primary_dataset
from model import FEATURE_METADATA, FEATURE_NAMES, TARGET_THRESHOLDS

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "model-evaluation"
MODEL_PATH = Path(__file__).resolve().parent / "placement_model_calibrated.joblib"
SEED = 42


def build_base_model() -> GradientBoostingClassifier:
    return GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5,
        random_state=SEED,
    )


def _metrics(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    predicted = (probability >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, predicted)),
        "f1_score": float(f1_score(y_true, predicted, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "log_loss": float(log_loss(y_true, probability, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(y_true, probability)),
    }


def evaluate_calibration(frame: Any, folds: int = 5, repeats: int = 3) -> dict[str, Any]:
    X = frame[FEATURE_NAMES]
    y = frame["placement_ready"].to_numpy()
    splitter = RepeatedStratifiedKFold(n_splits=folds, n_repeats=repeats, random_state=SEED)
    raw_probabilities: list[float] = []
    calibrated_probabilities: list[float] = []
    observed: list[int] = []

    for train_indices, test_indices in splitter.split(X, y):
        raw_model = build_base_model().fit(X.iloc[train_indices], y[train_indices])
        calibrated_model = CalibratedClassifierCV(
            estimator=build_base_model(), method="sigmoid", cv=3
        ).fit(X.iloc[train_indices], y[train_indices])
        raw_probabilities.extend(raw_model.predict_proba(X.iloc[test_indices])[:, 1])
        calibrated_probabilities.extend(calibrated_model.predict_proba(X.iloc[test_indices])[:, 1])
        observed.extend(y[test_indices])

    y_true = np.asarray(observed)
    raw = np.asarray(raw_probabilities)
    calibrated = np.asarray(calibrated_probabilities)
    fraction_raw, mean_raw = calibration_curve(y_true, raw, n_bins=10, strategy="quantile")
    fraction_calibrated, mean_calibrated = calibration_curve(
        y_true, calibrated, n_bins=10, strategy="quantile"
    )

    return {
        "evaluation": {
            "seed": SEED,
            "folds": folds,
            "repeats": repeats,
            "method": "sigmoid",
            "calibration_cv_folds": 3,
        },
        "raw": _metrics(y_true, raw),
        "calibrated": _metrics(y_true, calibrated),
        "calibration_curve": {
            "raw": [
                {
                    "mean_predicted_probability": float(predicted),
                    "fraction_positive": float(observed),
                }
                for predicted, observed in zip(mean_raw, fraction_raw, strict=True)
            ],
            "calibrated": [
                {
                    "mean_predicted_probability": float(predicted),
                    "fraction_positive": float(observed),
                }
                for predicted, observed in zip(mean_calibrated, fraction_calibrated, strict=True)
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deduplicate-exact", action="store_true")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    frame, metadata = load_primary_dataset(deduplicate_exact=args.deduplicate_exact)
    report = {
        "dataset": metadata,
        **evaluate_calibration(frame, folds=args.folds, repeats=args.repeats),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "calibration_evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    markdown = f"""# Probability calibration evaluation

This report evaluates raw Gradient Boosting probabilities against sigmoid-calibrated
probabilities using repeated out-of-fold predictions. It is not production approval.

- Dataset: `{metadata["path"]}`
- SHA-256: `{metadata["sha256"]}`
- Rows evaluated: {metadata["rows"]}
- Exact duplicates removed explicitly: {metadata["duplicate_rows_removed"]}
- Calibration method: sigmoid with {args.folds} x {args.repeats} outer evaluation and 3 inner folds

| Output | Brier score | Log loss | ROC-AUC |
|---|---:|---:|---:|
| Raw model probability | {report["raw"]["brier_score"]:.4f} | {report["raw"]["log_loss"]:.4f} | {report["raw"]["roc_auc"]:.4f} |
| Calibrated probability | {report["calibrated"]["brier_score"]:.4f} | {report["calibrated"]["log_loss"]:.4f} | {report["calibrated"]["roc_auc"]:.4f} |

The calibrated output improves probability quality on this prototype dataset,
while the small, unverified dataset still limits generalization claims.
"""
    (REPORT_DIR / "calibration_evaluation.md").write_text(markdown, encoding="utf-8")

    base_model = build_base_model().fit(frame[FEATURE_NAMES], frame["placement_ready"])
    calibrated_model = CalibratedClassifierCV(
        estimator=build_base_model(), method="sigmoid", cv=5
    ).fit(frame[FEATURE_NAMES], frame["placement_ready"])
    total_importance = float(base_model.feature_importances_.sum())
    feature_importance = {
        feature: round(float(importance / total_importance * 100), 2)
        for feature, importance in zip(FEATURE_NAMES, base_model.feature_importances_, strict=True)
    }
    joblib.dump(
        {
            "model": calibrated_model,
            "algorithm": "Calibrated Gradient Boosting Classifier",
            "feature_names": FEATURE_NAMES,
            "feature_metadata": FEATURE_METADATA,
            "target_thresholds": TARGET_THRESHOLDS,
            "feature_importance": dict(
                sorted(feature_importance.items(), key=lambda item: item[1], reverse=True)
            ),
            "metrics": report["calibrated"],
            "dataset_metadata": metadata,
            "calibration": report["evaluation"],
            "calibration_metrics": report["calibrated"],
            "model_version": "2.0.0-calibrated-gb",
        },
        MODEL_PATH,
    )
    print(json.dumps(report, indent=2))
    print("Calibrated artifact was written successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
