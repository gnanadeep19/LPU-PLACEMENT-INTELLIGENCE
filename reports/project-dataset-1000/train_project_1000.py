"""Research-only 1,000-row benchmark from the project's engineering CSV."""
import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURES = ['Age', 'Stream', 'Internships', 'CGPA', 'Hostel', 'HistoryOfBacklogs']
NUMERIC = ['Age', 'Internships', 'CGPA', 'Hostel', 'HistoryOfBacklogs']
TARGET = 'PlacedOrNot'
SEED = 42


def preprocess():
    return ColumnTransformer([
        ('num', Pipeline([('imputer', SimpleImputer(strategy='median')), ('scale', StandardScaler())]), NUMERIC),
        ('stream', Pipeline([('imputer', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore'))]), ['Stream'])])


def score(model, x, y):
    pred = model.predict(x)
    prob = model.predict_proba(x)[:, 1]
    n = len(y)
    p = float(accuracy_score(y, pred))
    z = 1.959963984540054
    den = 1 + z*z/n
    center = (p + z*z/(2*n))/den
    radius = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return {'accuracy': p, 'accuracy_wilson_95_interval': [max(0, center-radius), min(1, center+radius)],
            'balanced_accuracy': float(balanced_accuracy_score(y, pred)),
            'precision': float(precision_score(y, pred, zero_division=0)),
            'recall': float(recall_score(y, pred, zero_division=0)),
            'f1': float(f1_score(y, pred, zero_division=0)),
            'roc_auc': float(roc_auc_score(y, prob)),
            'confusion_matrix_rows_actual_0_1_columns_predicted_0_1': confusion_matrix(y, pred, labels=[0, 1]).tolist()}


def grouped_split(frame, fraction, seed):
    groups = pd.util.hash_pandas_object(frame[FEATURES], index=False)
    split = GroupShuffleSplit(n_splits=1, test_size=fraction, random_state=seed)
    train, test = next(split.split(frame[FEATURES], frame[TARGET], groups))
    return frame.iloc[train], frame.iloc[test]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data = pd.read_csv(args.data)
    if not set(FEATURES + ['Gender', TARGET]).issubset(data.columns) or not data[TARGET].isin([0, 1]).all():
        raise ValueError('Unexpected dataset schema or target')
    original = len(data)
    duplicates = int(data.duplicated().sum())
    data = data.drop_duplicates().reset_index(drop=True)
    if len(data) < 1000:
        raise ValueError('Fewer than 1,000 distinct full records')
    _, sample = train_test_split(data, test_size=1000, random_state=SEED, stratify=data[TARGET])
    train, test = grouped_split(sample, 0.2, SEED)
    fit, validation = grouped_split(train, 0.2, SEED + 1)
    for part in [fit, validation, test]:
        if part[TARGET].nunique() != 2:
            raise ValueError('A split has only one class; evaluation is not meaningful')
    xfit, yfit = fit[FEATURES], fit[TARGET].astype(int)
    xv, yv = validation[FEATURES], validation[TARGET].astype(int)
    xt, yt = test[FEATURES], test[TARGET].astype(int)
    models = {
        'majority_baseline': DummyClassifier(strategy='most_frequent'),
        'logistic_regression': Pipeline([('preprocess', preprocess()), ('model', LogisticRegression(max_iter=2000, random_state=SEED))]),
        'random_forest': Pipeline([('preprocess', preprocess()), ('model', RandomForestClassifier(n_estimators=200, min_samples_leaf=2, max_depth=14, random_state=SEED, n_jobs=2))]),
    }
    validation_metrics = {}
    for name, model in models.items():
        model.fit(xfit, yfit)
        validation_metrics[name] = score(model, xv, yv)
    winner = max((n for n in models if n != 'majority_baseline'), key=lambda n: validation_metrics[n]['balanced_accuracy'])
    models[winner].fit(train[FEATURES], train[TARGET].astype(int))
    models['majority_baseline'].fit(train[FEATURES], train[TARGET].astype(int))
    train_groups = set(pd.util.hash_pandas_object(train[FEATURES], index=False))
    test_groups = set(pd.util.hash_pandas_object(test[FEATURES], index=False))
    report = {
        'dataset': 'dataset/college_placement_engineering.csv',
        'dataset_sha256': hashlib.sha256(args.data.read_bytes()).hexdigest(),
        'provenance': 'Dataset origin, license, label construction and real versus synthetic status are not independently verified.',
        'target': 'PlacedOrNot (definition and observation horizon unverified)',
        'original_rows': original, 'exact_duplicate_rows_removed': duplicates, 'distinct_full_rows': len(data),
        'sample_rows': len(sample), 'training_rows_after_refit': len(train), 'test_rows': len(test),
        'selection_fit_rows': len(fit), 'selection_validation_rows': len(validation),
        'features': FEATURES, 'excluded': ['Gender'],
        'split': 'Stratified sample, then grouped holdout by identical input values; validation grouped in the same way.',
        'group_overlap_train_test': len(train_groups & test_groups),
        'sample_class_counts': {str(k): int(v) for k, v in sample[TARGET].value_counts().items()},
        'test_class_counts': {str(k): int(v) for k, v in test[TARGET].value_counts().items()},
        'seed': SEED, 'model_selection': 'Highest validation balanced accuracy; final model refitted on training split.',
        'validation_metrics': validation_metrics, 'selected_model': winner,
        'test_metrics': {winner: score(models[winner], xt, yt), 'majority_baseline': score(models['majority_baseline'], xt, yt)},
        'limitations': ['The website readiness model uses a different outcome and nine features; this model is incompatible.',
                        'The data may be synthetic; provenance and label definition require verification.',
                        'Exact distinct rows are not verified unique individuals.',
                        'Test records are from the same dataset, not a verified independent LPU cohort.',
                        'Age and hostel status may introduce bias; performance and fairness were not validated for individual use.'],
        'python_version': platform.python_version(), 'scikit_learn_version': sklearn.__version__}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    joblib.dump(models[winner], args.out/'research_placement_model.joblib')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
