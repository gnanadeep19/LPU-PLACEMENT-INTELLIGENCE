"""Tests for model artifact contract validation."""

from model import FEATURE_METADATA, FEATURE_NAMES, TARGET_THRESHOLDS
from model_registry import validate_payload


def valid_payload():
    return {
        "model": type("TestModel", (), {"predict_proba": lambda self, values: values})(),
        "algorithm": "Test classifier",
        "feature_names": FEATURE_NAMES,
        "feature_metadata": FEATURE_METADATA,
        "target_thresholds": TARGET_THRESHOLDS,
        "metrics": {"accuracy": 0.9, "f1_score": 0.8, "roc_auc": 0.95},
        "model_version": "test-1",
    }


def test_valid_payload_passes():
    assert validate_payload(valid_payload()) == []


def test_missing_and_mismatched_contracts_are_reported():
    payload = valid_payload()
    payload.pop("metrics")
    payload["feature_names"] = ["cgpa"]
    payload["model_version"] = ""

    errors = validate_payload(payload)

    assert "Missing payload keys: metrics." in errors
    assert any("feature_names" in error for error in errors)
    assert "Artifact model_version must be a non-empty string." in errors


def test_invalid_metrics_and_model_are_reported():
    payload = valid_payload()
    payload["model"] = object()
    payload["metrics"]["roc_auc"] = 2

    errors = validate_payload(payload)

    assert "Artifact model must expose predict_proba." in errors
    assert "Metric 'roc_auc' must be a number between 0 and 1." in errors
