"""Train and evaluate the larger external placement benchmark."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "dataset" / "college_placement_engineering.csv"
REPORT_DIR = ROOT / "reports" / "model-evaluation"
REPORT_JSON = REPORT_DIR / "external_benchmark_evaluation.json"
REPORT_MARKDOWN = REPORT_DIR / "external_benchmark_evaluation.md"
ARTIFACT_PATH = ROOT / "backend" / "external_placement_benchmark.joblib"
TARGET = "PlacedOrNot"
SEED = 42


def build_pipeline(model, numeric_features, categorical_features):
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def main():
    frame = pd.read_csv(DATASET_PATH)
    original_rows = len(frame)
    duplicate_rows = int(frame.duplicated().sum())
    frame = frame.drop_duplicates().reset_index(drop=True)
    X = frame.drop(columns=[TARGET])
    y = frame[TARGET].astype(int)
    categorical_features = X.select_dtypes(include=["object", "string"]).columns.tolist()
    numeric_features = [column for column in X.columns if column not in categorical_features]
    models = {
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=SEED
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=14,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=SEED,
            n_jobs=-1,
        ),
    }
    scoring = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "f1": "f1",
        "roc_auc": "roc_auc",
    }
    cross_validator = RepeatedStratifiedKFold(
        n_splits=5, n_repeats=3, random_state=SEED
    )
    results = {}
    for name, model in models.items():
        evaluation = cross_validate(
            build_pipeline(model, numeric_features, categorical_features),
            X,
            y,
            cv=cross_validator,
            scoring=scoring,
            n_jobs=-1,
        )
        results[name] = {
            metric: {
                "mean": float(evaluation[f"test_{metric}"].mean()),
                "std": float(evaluation[f"test_{metric}"].std()),
            }
            for metric in scoring
        }

    selected_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
    )
    selected_pipeline = build_pipeline(
        selected_model, numeric_features, categorical_features
    )
    selected_pipeline.fit(X, y)

    report = {
        "dataset": str(DATASET_PATH.relative_to(ROOT)),
        "target": TARGET,
        "original_rows": original_rows,
        "duplicate_rows_removed": duplicate_rows,
        "rows_evaluated": len(frame),
        "features": list(X.columns),
        "class_counts": {str(key): int(value) for key, value in y.value_counts().items()},
        "cross_validation": "RepeatedStratifiedKFold: 5 folds x 3 repeats",
        "models": results,
        "live_model_compatibility": False,
        "compatibility_note": (
            "The benchmark lacks technical_score, aptitude_score, "
            "communication_score, coding_score, projects, and certifications."
        ),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": selected_pipeline,
        "model_version": "external-rf-placement-v1",
        "algorithm": "Random Forest with preprocessing pipeline",
        "feature_names": list(X.columns),
        "target": TARGET,
        "metrics": results["random_forest"],
        "dataset_metadata": {
            "path": str(DATASET_PATH.relative_to(ROOT)),
            "original_rows": original_rows,
            "duplicate_rows_removed": duplicate_rows,
            "rows_evaluated": len(frame),
            "source_note": "External Kaggle benchmark; provenance and license require owner confirmation.",
        },
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "activation_status": "benchmark_only_not_loaded_by_api",
    }
    joblib.dump(artifact, ARTIFACT_PATH)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# External placement benchmark evaluation",
        "",
        "This report is separate from the live nine-feature readiness model.",
        "",
        f"- Dataset: `{report['dataset']}`",
        f"- Original rows: {original_rows}",
        f"- Exact duplicates removed: {duplicate_rows}",
        f"- Rows evaluated: {len(frame)}",
        f"- Cross-validation: {report['cross_validation']}",
        f"- Benchmark artifact: `{ARTIFACT_PATH.relative_to(ROOT)}`",
        "",
        "| Model | Accuracy | Balanced accuracy | F1 | ROC-AUC |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, metrics in results.items():
        lines.append(
            f"| `{name}` | {metrics['accuracy']['mean']:.3f} +/- {metrics['accuracy']['std']:.3f} | "
            f"{metrics['balanced_accuracy']['mean']:.3f} +/- {metrics['balanced_accuracy']['std']:.3f} | "
            f"{metrics['f1']['mean']:.3f} +/- {metrics['f1']['std']:.3f} | "
            f"{metrics['roc_auc']['mean']:.3f} +/- {metrics['roc_auc']['std']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Compatibility",
            "",
            "This dataset must not replace the live model without a schema migration.",
            report["compatibility_note"],
        ]
    )
    REPORT_MARKDOWN.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"JSON report: {REPORT_JSON}")
    print(f"Markdown report: {REPORT_MARKDOWN}")


if __name__ == "__main__":
    main()
