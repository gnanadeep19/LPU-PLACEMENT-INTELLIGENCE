"""Validate model artifacts before they are activated by the API."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib

from model import FEATURE_METADATA, FEATURE_NAMES, TARGET_THRESHOLDS

REQUIRED_PAYLOAD_KEYS = {
    "model",
    "algorithm",
    "feature_names",
    "feature_metadata",
    "target_thresholds",
    "metrics",
    "model_version",
}
REQUIRED_METRICS = {"accuracy", "f1_score", "roc_auc"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_payload(payload: Any) -> list[str]:
    """Return all contract violations found in a serialized artifact payload."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["Artifact payload must be a dictionary."]

    missing = sorted(REQUIRED_PAYLOAD_KEYS - payload.keys())
    if missing:
        errors.append(f"Missing payload keys: {', '.join(missing)}.")

    if payload.get("feature_names") != FEATURE_NAMES:
        errors.append("Artifact feature_names do not match the canonical feature contract.")
    if payload.get("feature_metadata") != FEATURE_METADATA:
        errors.append("Artifact feature_metadata do not match the canonical feature contract.")
    if payload.get("target_thresholds") != TARGET_THRESHOLDS:
        errors.append("Artifact target_thresholds do not match the approved thresholds.")

    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("Artifact metrics must be a dictionary.")
    else:
        missing_metrics = sorted(REQUIRED_METRICS - metrics.keys())
        if missing_metrics:
            errors.append(f"Missing required metrics: {', '.join(missing_metrics)}.")
        for metric in REQUIRED_METRICS:
            value = metrics.get(metric)
            if value is not None and (not isinstance(value, (int, float)) or not 0 <= value <= 1):
                errors.append(f"Metric '{metric}' must be a number between 0 and 1.")

    model = payload.get("model")
    if model is not None and not hasattr(model, "predict_proba"):
        errors.append("Artifact model must expose predict_proba.")
    if not isinstance(payload.get("model_version"), str) or not payload["model_version"].strip():
        errors.append("Artifact model_version must be a non-empty string.")
    return errors


def inspect_artifact(path: str | Path) -> dict[str, Any]:
    """Load and validate an artifact, returning safe metadata for operations."""
    artifact_path = Path(path).resolve()
    if not artifact_path.is_file():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}")
    payload = joblib.load(artifact_path)
    errors = validate_payload(payload)
    return {
        "path": str(artifact_path),
        "sha256": sha256_file(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
        "valid": not errors,
        "errors": errors,
        "model_version": payload.get("model_version") if isinstance(payload, dict) else None,
        "algorithm": payload.get("algorithm") if isinstance(payload, dict) else None,
        "trained_at": payload.get("trained_at") if isinstance(payload, dict) else None,
        "dataset_metadata": payload.get("dataset_metadata") if isinstance(payload, dict) else None,
        "metrics": payload.get("metrics") if isinstance(payload, dict) else None,
        "calibration": payload.get("calibration") if isinstance(payload, dict) else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    result = inspect_artifact(args.artifact)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
