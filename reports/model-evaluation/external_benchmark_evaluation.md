# External placement benchmark evaluation

This report is separate from the live nine-feature readiness model.

- Dataset: `dataset\college_placement_engineering.csv`
- Original rows: 2966
- Exact duplicates removed: 1829
- Rows evaluated: 1137
- Cross-validation: RepeatedStratifiedKFold: 5 folds x 3 repeats
- Benchmark artifact: `backend\external_placement_benchmark.joblib`

| Model | Accuracy | Balanced accuracy | F1 | ROC-AUC |
|---|---:|---:|---:|---:|
| `logistic_regression` | 0.728 +/- 0.027 | 0.728 +/- 0.030 | 0.756 +/- 0.023 | 0.832 +/- 0.017 |
| `random_forest` | 0.792 +/- 0.023 | 0.802 +/- 0.022 | 0.804 +/- 0.023 | 0.852 +/- 0.024 |

## Compatibility

This dataset must not replace the live model without a schema migration.
The benchmark lacks technical_score, aptitude_score, communication_score, coding_score, projects, and certifications.
