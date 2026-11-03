"""On-demand SHAP explanations for the active uncalibrated tree model."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


class ShapExplanationUnavailable(RuntimeError):
    """The installed model or runtime cannot safely provide this explanation."""


def explain_tree_prediction(payload: dict, student: dict) -> dict:
    """Explain raw model log-odds; never describe them as probability points."""
    if payload.get('probability_model') is not None or payload.get('calibration') or payload.get('calibration_metrics'):
        raise ShapExplanationUnavailable('SHAP is not available for this calibrated model.')
    try:
        import shap
        features = payload['feature_names']
        model = payload['model']
        frame = pd.DataFrame([student])[features]
        explainer = shap.TreeExplainer(model, feature_perturbation='tree_path_dependent', model_output='raw')
        values = np.asarray(explainer.shap_values(frame), dtype=float)
        expected = np.asarray(explainer.expected_value, dtype=float).reshape(-1)
        if values.shape != (1, len(features)) or expected.size != 1:
            raise ValueError('Unsupported explanation shape')
        base = float(expected[0])
        raw_score = float(np.asarray(model.decision_function(frame)).reshape(-1)[0])
        if not math.isfinite(base) or not math.isfinite(raw_score) or not np.isfinite(values).all():
            raise ValueError('Non-finite explanation')
        if not math.isclose(base + float(values.sum()), raw_score, rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError('Explanation does not match the model score')
        metadata = payload.get('feature_metadata', {})
        factors = [{'feature': name, 'label': metadata.get(name, {}).get('label', name),
                    'value': student[name], 'impact_log_odds': round(float(value), 4)}
                   for name, value in zip(features, values[0], strict=True)]
        return {'method': 'SHAP TreeExplainer', 'model_version': payload.get('model_version', 'unversioned'),
                'scale': 'raw log-odds', 'baseline_log_odds': round(base, 4),
                'model_log_odds': round(raw_score, 4),
                'factors': sorted(factors, key=lambda factor: abs(factor['impact_log_odds']), reverse=True),
                'note': 'SHAP describes how this model uses inputs relative to its training baseline. It is not a causal effect or a placement guarantee.'}
    except ShapExplanationUnavailable:
        raise
    except Exception as exc:
        raise ShapExplanationUnavailable('SHAP explanation is unavailable for this model.') from exc
