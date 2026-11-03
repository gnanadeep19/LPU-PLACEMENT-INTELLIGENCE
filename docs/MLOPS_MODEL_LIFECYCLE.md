# MLOps and Model Lifecycle Baseline

This project now treats serialized models as release artifacts. A model must
pass contract validation before it is activated by the API.

## Artifact contract

The artifact must contain:

- The trained estimator with `predict_proba`.
- The canonical nine-feature order and feature metadata.
- Approved readiness thresholds.
- Accuracy, F1, and ROC-AUC metrics in the range 0 to 1.
- A non-empty model version.
- Dataset metadata when produced by the canonical evaluation/calibration
  workflows.

Validate an artifact before activation:

```powershell
py -3.13 backend\model_registry.py backend\placement_model.joblib
py -3.13 backend\model_registry.py backend\placement_model_calibrated.joblib
```

The command prints the SHA-256 checksum, model version, training metadata,
metrics, calibration metadata, and validation errors. It exits with status 1
when the artifact is invalid.

## Promotion workflow

1. Run the canonical evaluator with explicit duplicate handling approval.
2. Record the dataset SHA-256, row count, duplicate policy, and evaluation
   report.
3. Run calibration evaluation when probability quality is required.
4. Validate the candidate artifact with `model_registry.py`.
5. Obtain data-owner and product-owner approval for the dataset, labels,
   metrics, and intended model version.
6. Activate through `MODEL_PATH`; never overwrite the existing artifact as an
   implicit side effect.
7. Exercise `/api/v1/readiness`, `/api/v1/model-info`, and the API regression
   suite.
8. Retain the previous artifact checksum for rollback.

## Rollback and monitoring

Rollback means restoring the previously approved artifact path and restarting
the API. Keep both artifact checksums and the corresponding dataset/evaluation
reports in the release record.

The current system does not yet collect production labels or feature
distributions. Before institutional rollout, add monitoring for:

- Input range and missing-field rejection rates.
- Feature distribution changes against the approved training dataset.
- Readiness-score and probability distribution changes.
- Calibration drift once outcome labels become available.
- Subgroup performance and fairness metrics where approved demographic data
  exists.
- Artifact version, checksum, and API error rate.

No automatic retraining or promotion is enabled. Small, unresolved provenance
and label-ownership questions remain release blockers.
