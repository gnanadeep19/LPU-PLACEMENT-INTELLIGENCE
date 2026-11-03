"""Reproducible, non-production benchmark on Stutern's 2018 graduate survey.

Usage: python train_real_graduate_survey.py --data SURVEY.csv --out DIR
The resulting artifact is NOT compatible with the LPU readiness dashboard.
"""
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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

COURSE = 'Title of course studied'
YEAR = 'Year of graduation'
JOBS = 'How many jobs have you had since graduation including your current one?'
LABEL = 'Employed'


def interval(correct, n):
    z = 1.959963984540054
    p = correct / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [center-radius, center+radius]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    data = pd.read_csv(args.data, low_memory=False)
    required = {COURSE, YEAR, JOBS, LABEL}
    if not required.issubset(data.columns):
        raise ValueError('The expected cleaned survey columns are missing.')
    raw_count = len(data)
    comparison = data.drop(columns=[c for c in ['Unnamed: 0', 'Timestamp'] if c in data])
    duplicate_mask = comparison.duplicated()
    duplicate_count = int(duplicate_mask.sum())
    data = data.loc[~duplicate_mask].copy()
    data = data.loc[data[LABEL].isin(['Yes', 'No'])].copy()
    jobs = pd.to_numeric(data[JOBS], errors='coerce')
    if jobs.isna().any() or not ((jobs > 0) == (data[LABEL] == 'Yes')).all():
        raise ValueError('The mirror target does not consistently match job count.')
    X = data[[COURSE, YEAR]].copy()
    X[COURSE] = X[COURSE].fillna('Unknown').astype(str)
    X[YEAR] = X[YEAR].astype(str)
    y = (data[LABEL] == 'Yes').astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    def pipeline(model):
        return Pipeline([('encoding', ColumnTransformer([
            ('categories', OneHotEncoder(handle_unknown='ignore'), [COURSE, YEAR])])),
            ('model', model)])
    models = {
        'majority_baseline': DummyClassifier(strategy='most_frequent'),
        'logistic_regression': pipeline(LogisticRegression(max_iter=1000)),
        'random_forest': pipeline(RandomForestClassifier(n_estimators=150, min_samples_leaf=10, random_state=42, n_jobs=2)),
    }
    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        proba = model.predict_proba(X_test)[:, 1]
        results[name] = {
            'accuracy': accuracy_score(y_test, pred),
            'accuracy_wilson_95_interval': interval(int((pred == y_test).sum()), len(y_test)),
            'balanced_accuracy': balanced_accuracy_score(y_test, pred),
            'precision_ever_employed': precision_score(y_test, pred, zero_division=0),
            'recall_ever_employed': recall_score(y_test, pred, zero_division=0),
            'f1_ever_employed': f1_score(y_test, pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, proba),
            'confusion_matrix_rows_actual_no_yes_columns_predicted_no_yes': confusion_matrix(y_test, pred, labels=[0, 1]).tolist(),
        }
    args.out.mkdir(parents=True, exist_ok=True)
    report = {
        'dataset': 'Stutern Nigerian Graduate Report 2018, third-party cleaned mirror',
        'source': 'https://www.kaggle.com/datasets/stutern/nigerian-gradaute-report-2018',
        'mirror': 'https://github.com/EJmpa/Stat-Solver/blob/main/Data_Cleaning/Nigerian_Graduates_Destination_Survey.csv',
        'license': 'CC BY-SA 4.0 (Kaggle source)',
        'sha256': hashlib.sha256(args.data.read_bytes()).hexdigest(),
        'rows_original': raw_count, 'identical_responses_excluded': duplicate_count,
        'rows_after_duplicate_exclusion': len(data), 'training_rows': len(X_train), 'test_rows': len(X_test),
        'label_counts': {'ever_employed': int(y.sum()), 'zero_jobs_reported': int((1-y).sum())},
        'features': [COURSE, YEAR], 'test_fraction': 0.2, 'random_seed': 42,
        'target': 'Self-reported at least one job since graduation; not current employment or campus placement.',
        'limitations': ['Nigerian respondents surveyed in 2018, not validated on LPU students.',
                        'Graduation year changes time available to find work; this is not a fixed-horizon outcome.',
                        'Course and graduation year do not match the nine inputs in the existing dashboard.',
                        'Stratified random split estimates same-survey performance, not later-year generalization.',
                        'Identical responses may be genuine distinct respondents; the exclusion is conservative.',
                        'Post-graduation information, including job count used to derive the target, is excluded from the predictors.'],
        'python_version': platform.python_version(), 'scikit_learn_version': sklearn.__version__, 'results': results,
    }
    (args.out / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    # A research-only artifact: no automatic deployment and no changes to the app's model.
    joblib.dump(models['logistic_regression'], args.out / 'research_logistic_regression.joblib')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
