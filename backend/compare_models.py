"""Canonical, reproducible model evaluation for the primary readiness dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import AdaBoostClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_pipeline import load_primary_dataset  # noqa: E402
from model import FEATURE_NAMES, TARGET_THRESHOLDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "model-evaluation"
SEED = 42


def build_models() -> dict[str, Any]:
    return {
        "majority_baseline": None,
        "threshold_baseline": None,
        "random_forest": RandomForestClassifier(
            n_estimators=250,
            max_depth=12,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=SEED,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=SEED,
        ),
        "decision_tree": DecisionTreeClassifier(max_depth=8, random_state=SEED),
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=SEED),
        "knn": KNeighborsClassifier(n_neighbors=5),
        "svm": SVC(probability=True, kernel="rbf", random_state=SEED),
        "naive_bayes": GaussianNB(),
        "adaboost": AdaBoostClassifier(n_estimators=100, random_state=SEED),
    }


def _threshold_predictions(frame: pd.DataFrame) -> np.ndarray:
    met = np.ones(len(frame), dtype=bool)
    for feature, threshold in TARGET_THRESHOLDS.items():
        if feature == "backlogs":
            met &= frame[feature].to_numpy() <= threshold
        else:
            met &= frame[feature].to_numpy() >= threshold
    return met.astype(int)


def _record_metrics(y_true: pd.Series, y_pred: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
    }


def evaluate(frame: pd.DataFrame, repeats: int = 3, folds: int = 5) -> dict[str, Any]:
    X = frame[FEATURE_NAMES]
    y = frame["placement_ready"]
    splitter = RepeatedStratifiedKFold(n_splits=folds, n_repeats=repeats, random_state=SEED)
    fold_results: dict[str, list[dict[str, float]]] = {name: [] for name in build_models()}

    for train_indices, test_indices in splitter.split(X, y):
        X_train, X_test = X.iloc[train_indices], X.iloc[test_indices]
        y_train, y_test = y.iloc[train_indices], y.iloc[test_indices]

        majority_probability = float(y_train.mean())
        majority_prediction = np.full(len(test_indices), int(majority_probability >= 0.5))
        fold_results["majority_baseline"].append(
            _record_metrics(
                y_test,
                majority_prediction,
                np.full(len(test_indices), majority_probability),
            )
        )

        threshold_prediction = _threshold_predictions(X_test)
        fold_results["threshold_baseline"].append(
            _record_metrics(y_test, threshold_prediction, threshold_prediction.astype(float))
        )

        for name, estimator in build_models().items():
            if estimator is None:
                continue
            fitted = clone(estimator).fit(X_train, y_train)
            prediction = fitted.predict(X_test)
            probability = fitted.predict_proba(X_test)[:, 1]
            fold_results[name].append(_record_metrics(y_test, prediction, probability))

    summary: dict[str, Any] = {}
    for name, metrics in fold_results.items():
        summary[name] = {
            "folds": len(metrics),
            "mean": {
                metric: float(np.mean([row[metric] for row in metrics])) for metric in metrics[0]
            },
            "std": {
                metric: float(np.std([row[metric] for row in metrics], ddof=1))
                for metric in metrics[0]
            },
        }

    winner = max(
        summary, key=lambda name: (summary[name]["mean"]["f1"], summary[name]["mean"]["roc_auc"])
    )
    return {
        "evaluation": {
            "seed": SEED,
            "folds": folds,
            "repeats": repeats,
            "total_splits": folds * repeats,
            "selection_rule": "highest mean F1, then ROC-AUC",
        },
        "models": summary,
        "winner": winner,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Canonical model evaluation",
        "",
        "This report uses the same primary dataset pipeline intended for readiness-model training.",
        "It is not production approval: the dataset label and provenance remain unverified.",
        "",
        f"- Dataset: `{report['dataset']['path']}`",
        f"- SHA-256: `{report['dataset']['sha256']}`",
        f"- Rows evaluated: {report['dataset']['rows']}",
        f"- Exact duplicates removed explicitly: {report['dataset']['duplicate_rows_removed']}",
        f"- Repeated stratified evaluation: {report['evaluation']['repeats']} x {report['evaluation']['folds']} folds",
        f"- Winner: `{report['winner']}`",
        "",
        "| Model | Accuracy | Balanced accuracy | Precision | Recall | F1 | ROC-AUC |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in report["models"].items():
        mean = result["mean"]
        std = result["std"]
        lines.append(
            f"| `{name}` | {mean['accuracy']:.3f} ± {std['accuracy']:.3f} | "
            f"{mean['balanced_accuracy']:.3f} ± {std['balanced_accuracy']:.3f} | "
            f"{mean['precision']:.3f} ± {std['precision']:.3f} | "
            f"{mean['recall']:.3f} ± {std['recall']:.3f} | "
            f"{mean['f1']:.3f} ± {std['f1']:.3f} | "
            f"{mean['roc_auc']:.3f} ± {std['roc_auc']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The current dataset is a prototype source with unverified provenance and label construction.",
            "- Exact duplicate rows were removed only because the evaluator was invoked with an explicit flag.",
            "- Cross-validation uncertainty reflects split variability, not real-world generalization.",
            "- These results must not be described as actual placement-outcome accuracy.",
            "- Calibration, subgroup fairness, external validation, and local explanations are Phase 4+ work.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deduplicate-exact",
        action="store_true",
        help="Explicitly remove exact duplicate rows after recording their count.",
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    frame, dataset_metadata = load_primary_dataset(deduplicate_exact=args.deduplicate_exact)
    report = {
        "dataset": dataset_metadata,
        **evaluate(frame, repeats=args.repeats, folds=args.folds),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "canonical_evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "canonical_evaluation.md").write_text(_markdown(report), encoding="utf-8")
    print(_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
