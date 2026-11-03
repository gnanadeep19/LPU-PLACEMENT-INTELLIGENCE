# Explainability contract

The readiness API exposes two complementary explanation surfaces:

## Local explanations

`local_explanations` estimates how each input feature changes the current
prediction relative to the institutional reference target for that feature.
The calculation replaces one feature at a time and measures the probability
difference. Each item includes:

- Current and reference values
- Direction (`supports readiness`, `reduces readiness`, or neutral)
- Probability-point contribution
- The explanation method name

These are local sensitivity estimates. They are not causal effects, do not
prove that a factor caused the prediction, and do not necessarily sum to the
predicted probability.

## Counterfactual scenarios

`counterfactual_scenarios` contains up to five bounded, one-feature scenarios.
Each scenario moves one value toward its institutional target while respecting
the API input bounds. The response includes the projected probability change.

Counterfactuals are planning aids, not placement guarantees. They must not be
used to promise a student a placement outcome or to override company-specific
eligibility rules.

## Global importance

`top_factors` remains available for model-level feature importance. It describes
the fitted ensemble overall and must not be presented as the explanation for a
specific student's prediction.

## On-demand SHAP

The student factors panel can request `POST /api/explain/shap` for the displayed
assessment. The endpoint requires an authenticated session and the same CSRF
protection as predictions, validates the profile, and rejects a model-version
mismatch. Inputs are not saved by this endpoint.

The active uncalibrated tree model is explained with SHAP TreeExplainer, using
the model's path-dependent training baseline. Contributions and the baseline
are in **raw log-odds**, not probability points; positive values raise the raw
score and negative values lower it. This describes model behavior, not a causal
relationship or placement guarantee. Calibrated models and unsupported model
shapes are explicitly rejected rather than explained on the wrong scale. The
existing one-feature sensitivity explanation remains available if SHAP fails.
