"""Tests for payload-free operational metrics."""

from observability import record_request, snapshot


def test_metrics_capture_request_shape_without_payloads():
    record_request("POST", "/api/v1/predict", 200, 12.5)
    record_request("POST", "/api/v1/predict", 400, 4.0)

    metrics = snapshot()

    assert metrics["request_count"] >= 2
    assert metrics["status_classes"]["2xx"] >= 1
    assert metrics["status_classes"]["4xx"] >= 1
    assert metrics["endpoints"]["POST /api/v1/predict"] >= 2
    assert "student" not in str(metrics).lower()
