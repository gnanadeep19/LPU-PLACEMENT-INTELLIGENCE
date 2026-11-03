"""Canonical evaluation and controlled retraining entry point.

The evaluator and training command both use ``dataset/students.csv``. Exact
duplicates must be explicitly approved with ``--deduplicate-exact``; no
synthetic fallback is permitted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_models import evaluate
from data_pipeline import load_primary_dataset
from model import train_placement_model

MODEL_PATH = Path(__file__).resolve().parent / "placement_model.joblib"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deduplicate-exact",
        action="store_true",
        help="Explicitly remove exact duplicate rows after recording the count.",
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    frame, metadata = load_primary_dataset(deduplicate_exact=args.deduplicate_exact)
    evaluation = evaluate(frame, repeats=args.repeats, folds=args.folds)
    winner = evaluation["winner"]

    print(f"Canonical dataset: {metadata['path']}")
    print(f"Dataset SHA-256: {metadata['sha256']}")
    print(f"Rows used: {metadata['rows']}")
    print(f"Exact duplicates removed: {metadata['duplicate_rows_removed']}")
    print(f"Cross-validation winner: {winner}")
    print(
        "Training the deployed artifact with the approved Gradient Boosting "
        "configuration from model.py."
    )
    payload = train_placement_model(data_df=frame, save_path=str(MODEL_PATH))
    payload["dataset_metadata"] = metadata
    payload["evaluation_summary"] = {
        "winner": winner,
        "folds": args.folds,
        "repeats": args.repeats,
    }

    import joblib

    joblib.dump(payload, MODEL_PATH)
    print(f"Artifact saved: {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
