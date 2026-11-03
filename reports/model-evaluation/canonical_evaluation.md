# Canonical model evaluation

This report uses the same primary dataset pipeline intended for readiness-model training.
It is not production approval: the dataset label and provenance remain unverified.

- Dataset: `dataset\students.csv`
- SHA-256: `e9fe3511c1ef3777e871e0bd97bd2b93efb002998ae3f29d4be152f6e4dc5e8f`
- Rows evaluated: 251
- Exact duplicates removed explicitly: 2
- Repeated stratified evaluation: 3 x 5 folds
- Winner: `adaboost`

| Model | Accuracy | Balanced accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| `majority_baseline` | 0.514 ± 0.008 | 0.500 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.500 ± 0.000 |
| `threshold_baseline` | 0.769 ± 0.054 | 0.763 ± 0.052 | 1.000 ± 0.000 | 0.526 ± 0.103 | 0.683 ± 0.095 | 0.763 ± 0.052 |
| `random_forest` | 0.939 ± 0.023 | 0.939 ± 0.023 | 0.923 ± 0.039 | 0.956 ± 0.046 | 0.938 ± 0.025 | 0.991 ± 0.007 |
| `gradient_boosting` | 0.947 ± 0.030 | 0.947 ± 0.030 | 0.946 ± 0.035 | 0.945 ± 0.046 | 0.945 ± 0.031 | 0.985 ± 0.021 |
| `decision_tree` | 0.950 ± 0.032 | 0.949 ± 0.032 | 0.952 ± 0.037 | 0.945 ± 0.054 | 0.947 ± 0.035 | 0.949 ± 0.032 |
| `logistic_regression` | 0.940 ± 0.026 | 0.940 ± 0.026 | 0.948 ± 0.039 | 0.929 ± 0.033 | 0.938 ± 0.027 | 0.988 ± 0.011 |
| `knn` | 0.900 ± 0.036 | 0.900 ± 0.036 | 0.914 ± 0.046 | 0.880 ± 0.066 | 0.895 ± 0.039 | 0.960 ± 0.019 |
| `svm` | 0.880 ± 0.034 | 0.880 ± 0.034 | 0.896 ± 0.057 | 0.858 ± 0.059 | 0.874 ± 0.036 | 0.955 ± 0.020 |
| `naive_bayes` | 0.928 ± 0.028 | 0.930 ± 0.027 | 0.878 ± 0.043 | 0.992 ± 0.017 | 0.931 ± 0.027 | 0.991 ± 0.006 |
| `adaboost` | 0.959 ± 0.022 | 0.959 ± 0.022 | 0.958 ± 0.035 | 0.959 ± 0.038 | 0.958 ± 0.023 | 0.995 ± 0.003 |

## Limitations

- The current dataset is a prototype source with unverified provenance and label construction.
- Exact duplicate rows were removed only because the evaluator was invoked with an explicit flag.
- Cross-validation uncertainty reflects split variability, not real-world generalization.
- These results must not be described as actual placement-outcome accuracy.
- Calibration, subgroup fairness, external validation, and local explanations are Phase 4+ work.
