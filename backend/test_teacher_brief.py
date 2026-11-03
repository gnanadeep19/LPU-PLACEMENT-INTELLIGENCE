"""Checks for authenticated SHAP explanations and the optional ASGI entry point."""
import math

import pytest

import app as app_module
import shap_explanations
from test_app import SAMPLE_STUDENT, client, csrf_headers, login  # noqa: F401


def test_shap_explanation_is_protected_and_validates_version(client, monkeypatch):
    body = {'student': SAMPLE_STUDENT, 'model_version': 'old'}
    assert client.post('/api/explain/shap', json=body).status_code == 401
    token = login(client, 'student.a')
    assert client.post('/api/explain/shap', json=body).status_code == 403
    monkeypatch.setattr(app_module, 'get_model', lambda: {'model_version': 'new'})
    assert client.post('/api/explain/shap', json=body, headers=csrf_headers(token)).status_code == 409
    body['student'] = {'cgpa': 7}
    assert client.post('/api/explain/shap', json=body, headers=csrf_headers(token)).status_code == 400


def test_shap_real_model_explanation_adds_up_and_handles_calibration(client):
    pytest.importorskip('shap')
    payload = app_module.get_model()
    result = shap_explanations.explain_tree_prediction(payload, SAMPLE_STUDENT)
    assert result['scale'] == 'raw log-odds'
    assert len(result['factors']) == len(payload['feature_names'])
    assert math.isclose(result['baseline_log_odds'] + sum(row['impact_log_odds'] for row in result['factors']),
                        result['model_log_odds'], abs_tol=0.001)
    with pytest.raises(shap_explanations.ShapExplanationUnavailable):
        shap_explanations.explain_tree_prediction({**payload, 'calibration': {'method': 'sigmoid'}}, SAMPLE_STUDENT)
    token = login(client, 'student.a')
    response = client.post('/api/explain/shap', headers=csrf_headers(token),
                           json={'student': SAMPLE_STUDENT, 'model_version': payload['model_version']})
    assert response.status_code == 200
    assert response.get_json()['data']['method'] == 'SHAP TreeExplainer'


def test_asgi_routes_keep_existing_auth_boundaries(client):
    pytest.importorskip('fastapi')
    from fastapi.testclient import TestClient
    from asgi import app
    with TestClient(app) as asgi_client:
        assert asgi_client.get('/api/health').status_code == 200
        assert asgi_client.get('/api/mentor/students').status_code == 401
