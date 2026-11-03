"""Canonical data loading and validation for the primary readiness dataset."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from model import FEATURE_NAMES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_DATASET_PATH = ROOT / "dataset" / "students.csv"
TARGET_NAME = "placement_ready"
REQUIRED_COLUMNS = [*FEATURE_NAMES, TARGET_NAME]


def dataset_sha256(path: Path = PRIMARY_DATASET_PATH) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as dataset_file:
        for chunk in iter(lambda: dataset_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_primary_dataset(*, deduplicate_exact: bool = False) -> tuple[pd.DataFrame, dict]:
    """Load the canonical primary dataset and return data plus audit metadata.

    Duplicate rows are a known Phase 2 blocker. They are rejected by default
    and can only be removed when the caller explicitly requests it.
    """

    if not PRIMARY_DATASET_PATH.exists():
        raise FileNotFoundError(f"Canonical dataset not found: {PRIMARY_DATASET_PATH}")

    frame = pd.read_csv(PRIMARY_DATASET_PATH)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Canonical dataset is missing required columns: {missing_columns}")

    frame = frame[REQUIRED_COLUMNS].copy()
    missing_values = int(frame.isna().sum().sum())
    if missing_values:
        raise ValueError(f"Canonical dataset contains {missing_values} missing values.")

    duplicate_rows = int(frame.duplicated().sum())
    if duplicate_rows and not deduplicate_exact:
        raise ValueError(
            f"Canonical dataset contains {duplicate_rows} exact duplicate rows. "
            "Review them or pass deduplicate_exact=True explicitly."
        )
    if duplicate_rows:
        frame = frame.drop_duplicates(ignore_index=True)

    target_values = set(frame[TARGET_NAME].unique())
    if not target_values.issubset({0, 1}):
        raise ValueError(f"{TARGET_NAME} must contain only 0 and 1, found {target_values}.")

    metadata = {
        "path": str(PRIMARY_DATASET_PATH.relative_to(ROOT)),
        "sha256": dataset_sha256(),
        "original_rows": int(len(pd.read_csv(PRIMARY_DATASET_PATH))),
        "rows": int(len(frame)),
        "duplicate_rows_removed": duplicate_rows if deduplicate_exact else 0,
        "features": FEATURE_NAMES,
        "target": TARGET_NAME,
        "class_distribution": {
            str(label): int(count) for label, count in frame[TARGET_NAME].value_counts().items()
        },
        "data_status": "prototype_unverified_label_and_provenance",
    }
    return frame, metadata
