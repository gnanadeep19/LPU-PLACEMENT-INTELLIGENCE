"""Offline XGBoost tuning against the prototype readiness label.

This script never overwrites the active model. Its test split evaluates only
the project's small, unverified dataset and is not an institutional validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import xgboost
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split

from data_pipeline import load_primary_dataset
from model import FEATURE_NAMES

ROOT = Path(__file__).resolve().parents[1]
SEED = 42


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[FEATURE_NAMES].copy()
    result['coding_technical_mean'] = (result['coding_score'] + result['technical_score']) / 2.0
    result['experience_count'] = result['projects'] + result['internships']
    return result


def evaluate(estimator, x, y):
    prediction = estimator.predict(x)
    probability = estimator.predict_proba(x)[:, 1]
    return {'accuracy': float(accuracy_score(y, prediction)),
            'balanced_accuracy': float(balanced_accuracy_score(y, prediction)),
            'f1': float(f1_score(y, prediction, zero_division=0)),
            'roc_auc': float(roc_auc_score(y, probability)),
            'confusion_matrix': confusion_matrix(y, prediction, labels=[0, 1]).tolist()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'reports' / 'teacher-brief-xgboost')
    args = parser.parse_args()
    frame, metadata = load_primary_dataset(deduplicate_exact=True)
    x = engineer_features(frame)
    y = frame['placement_ready'].astype(int)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, stratify=y, random_state=SEED)
    model = xgboost.XGBClassifier(objective='binary:logistic', eval_metric='logloss',
                                 n_jobs=2, random_state=SEED)
    grid = {'n_estimators': [80, 160], 'max_depth': [2, 3], 'learning_rate': [0.05, 0.1]}
    search = GridSearchCV(model, grid, scoring='balanced_accuracy',
                          cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED),
                          n_jobs=1, refit=True, error_score='raise')
    search.fit(x_train, y_train)
    baseline = DummyClassifier(strategy='most_frequent').fit(x_train, y_train)
    test_metrics = evaluate(search.best_estimator_, x_test, y_test)
    report = {'dataset': metadata, 'target': 'placement_ready; source meaning unverified',
              'seed': SEED, 'training_rows': len(x_train), 'test_rows': len(x_test),
              'features': list(x.columns), 'engineered_features': {
                  'coding_technical_mean': 'mean of coding and technical scores',
                  'experience_count': 'projects plus internships'},
              'tuning': {'method': 'GridSearchCV, stratified 3-fold on training split only',
                         'selection_metric': 'balanced_accuracy', 'parameter_grid': grid,
                         'best_parameters': search.best_params_, 'best_cv_balanced_accuracy': float(search.best_score_)},
              'test_metrics': {'xgboost': test_metrics, 'majority_baseline': evaluate(baseline, x_test, y_test)},
              'limitations': ['Prototype dataset has 251 distinct rows and an unverified label and provenance.',
                              'The held-out split is from the same dataset and is not external LPU validation.',
                              'The model is experimental and is not active on the website.'],
              'xgboost_version': xgboost.__version__}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'evaluation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    joblib.dump({'model': search.best_estimator_, 'features': list(x.columns),
                 'data_sha256': metadata['sha256'], 'activation_status': 'research_only'},
                args.out / 'experimental_xgboost.joblib')
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.heatmap(test_metrics['confusion_matrix'], annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=['Not ready', 'Ready'], yticklabels=['Not ready', 'Ready'], ax=ax)
    ax.set(title='XGBoost: held-out prototype labels', xlabel='Predicted', ylabel='Recorded label')
    fig.tight_layout()
    fig.savefig(args.out / 'holdout_confusion_matrix.png', dpi=140)
    plt.close(fig)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
