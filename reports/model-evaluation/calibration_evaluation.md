# Probability calibration evaluation

This report evaluates raw Gradient Boosting probabilities against sigmoid-calibrated
probabilities using repeated out-of-fold predictions. It is not production approval.

- Dataset: `dataset\students.csv`
- SHA-256: `e9fe3511c1ef3777e871e0bd97bd2b93efb002998ae3f29d4be152f6e4dc5e8f`
- Rows evaluated: 251
- Exact duplicates removed explicitly: 2
- Calibration method: sigmoid with 5 x 3 outer evaluation and 3 inner folds

| Output | Brier score | Log loss | ROC-AUC |
|---|---:|---:|---:|
| Raw model probability | 0.0531 | 0.8161 | 0.9853 |
| Calibrated probability | 0.0460 | 0.1999 | 0.9828 |

The calibrated output improves probability quality on this prototype dataset,
while the small, unverified dataset still limits generalization claims.
