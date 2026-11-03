r"""
Model Training Script — LPU Placement Intelligence Platform

Priority order for training data:
  1. dataset/students.csv  (manually curated records, preferred)
  2. No fallback: missing or invalid canonical data is an error.

Run from the backend/ directory:
  .venv\Scripts\python.exe train_model.py
"""

import argparse
import os

import pandas as pd

from data_pipeline import load_primary_dataset
from model import FEATURE_NAMES, train_placement_model

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset", "students.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "placement_model.joblib")


def load_dataset(deduplicate_exact: bool = False) -> tuple[pd.DataFrame, str]:
    """Load the canonical primary dataset without silent fallback."""
    df, metadata = load_primary_dataset(deduplicate_exact=deduplicate_exact)
    return df, f"{metadata['path']} ({metadata['rows']} records, SHA-256 {metadata['sha256']})"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deduplicate-exact",
        action="store_true",
        help="Explicitly remove exact duplicate rows after recording the count.",
    )
    args = parser.parse_args()
    print("=" * 70)
    print("  LPU Placement Intelligence Platform — Model Training Pipeline   ")
    print("=" * 70)

    # ── Step 1: Load data ──────────────────────────────────────────────────
    print("\nStep 1 — Loading training data ...")
    data_df, source_label = load_dataset(deduplicate_exact=args.deduplicate_exact)
    print(f"         Source  : {source_label}")
    print(f"         Shape   : {data_df.shape[0]} rows × {data_df.shape[1]} columns")
    print(f"         Features: {', '.join(FEATURE_NAMES)}")
    print("         Label   : placement_ready")
    print(
        f"         Class split: "
        f"{int(data_df['placement_ready'].sum())} ready "
        f"/ {int((data_df['placement_ready'] == 0).sum())} not ready"
    )

    # ── Step 2: Train ─────────────────────────────────────────────────────
    print("\nStep 2 — Splitting dataset (80% train / 20% test, stratified) ...")
    print(
        "Step 3 — Training Gradient Boosting Classifier (200 estimators, max_depth=5, lr=0.1) ..."
    )

    payload = train_placement_model(data_df=data_df, save_path=MODEL_PATH)
    metrics = payload["metrics"]

    # ── Step 3: Report ────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("                   MODEL PERFORMANCE EVALUATION                     ")
    print("-" * 70)
    print(f"  Accuracy   : {metrics['accuracy'] * 100:.2f}%")
    print(f"  Precision  : {metrics['precision'] * 100:.2f}%")
    print(f"  Recall     : {metrics['recall'] * 100:.2f}%")
    print(f"  F1-Score   : {metrics['f1_score'] * 100:.2f}%")
    print(f"  ROC-AUC    : {metrics['roc_auc']:.4f}")
    print(f"  Train rows : {metrics['train_rows']}")
    print(f"  Test rows  : {metrics['test_rows']}")
    print(f"  Confusion  : {metrics['confusion_matrix']}")
    print("-" * 70)

    print("\n  Top Feature Importance (Gini, normalized):")
    for rank, (feat, imp) in enumerate(list(payload["feature_importance"].items())[:9], start=1):
        bar = "#" * int(imp / 2)
        print(f"  {rank:>2}. {feat:<22} {bar:<25} {imp:5.2f}%")

    print(f"\n  Artifact saved: {os.path.abspath(MODEL_PATH)}")
    print(f"\n  [NOTE] {metrics['data_note']}")
    print("=" * 70)
    print("  Training completed. Run 'python app.py' to start the API server.")
    print("=" * 70)


if __name__ == "__main__":
    main()
