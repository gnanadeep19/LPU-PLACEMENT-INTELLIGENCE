"""Train an isolated placement-outcome benchmark on the supplied CSV files.

This research artifact is not compatible with the existing dashboard model.
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
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             brier_score_loss, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

FEATURES = ['CGPA', 'Internships', 'Projects', 'Coding_Skills',
            'Communication_Skills', 'Aptitude_Test_Score', 'Certifications', 'Backlogs']
TARGET = 'Placement_Status'
SEED = 42


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(df, label):
    missing = set(FEATURES + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f'{label} missing required fields: {sorted(missing)}')
    if not df[TARGET].isin(['Placed', 'Not Placed']).all():
        raise ValueError(f'{label} contains missing or unrecognized placement labels')
    for feature in FEATURES:
        df[feature] = pd.to_numeric(df[feature], errors='raise')
    if df[FEATURES].isna().all().any():
        raise ValueError(f'{label} has a completely missing model feature')


def metrics(model, x, y):
    pred = model.predict(x)
    prob = model.predict_proba(x)[:, 1]
    n = len(y)
    accuracy = accuracy_score(y, pred)
    z = 1.959963984540054
    den = 1 + z*z/n
    center = (accuracy + z*z/(2*n)) / den
    radius = z * math.sqrt(accuracy*(1-accuracy)/n + z*z/(4*n*n)) / den
    return {'accuracy': accuracy, 'accuracy_wilson_95_interval': [max(0, center-radius), min(1, center+radius)],
            'balanced_accuracy': balanced_accuracy_score(y, pred),
            'precision_placed': precision_score(y, pred, zero_division=0),
            'recall_placed': recall_score(y, pred, zero_division=0),
            'f1_placed': f1_score(y, pred, zero_division=0),
            'roc_auc': roc_auc_score(y, prob), 'brier_score': brier_score_loss(y, prob),
            'confusion_matrix_actual_not_placed_placed_predicted_not_placed_placed':
                confusion_matrix(y, pred, labels=[0, 1]).tolist()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', required=True, type=Path)
    parser.add_argument('--test', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    train, test = pd.read_csv(args.train), pd.read_csv(args.test)
    validate(train, 'train')
    validate(test, 'test')
    train_id = set(train['Student_ID']) if 'Student_ID' in train else set()
    test_id = set(test['Student_ID']) if 'Student_ID' in test else set()
    overlap = len(train[FEATURES].drop_duplicates().merge(test[FEATURES].drop_duplicates(), on=FEATURES))
    if train_id & test_id:
        raise ValueError('Train/test IDs overlap; audit before evaluation')
    if train[TARGET].nunique() != 2 or test[TARGET].nunique() != 2:
        raise ValueError('Both placement classes must be present in train and test')
    original_train_rows = len(train)
    train_duplicate_rows = int(train.duplicated(FEATURES).sum())
    if (train.groupby(FEATURES, dropna=False)[TARGET].nunique() > 1).any():
        raise ValueError('Training examples with identical inputs have conflicting labels')
    test_keys = test[FEATURES].drop_duplicates().assign(_in_test=True)
    marked = train.merge(test_keys, on=FEATURES, how='left', validate='many_to_one')
    matching_train_rows = int(marked['_in_test'].notna().sum())
    clean = marked.loc[marked['_in_test'].isna()].drop(columns=['_in_test']).drop_duplicates(FEATURES)
    x, y = clean[FEATURES], (clean[TARGET] == 'Placed').astype(int)
    xt, yt = test[FEATURES], (test[TARGET] == 'Placed').astype(int)
    xa, xv, ya, yv = train_test_split(x, y, test_size=0.2, random_state=SEED, stratify=y)
    models = {
        'majority_baseline': DummyClassifier(strategy='most_frequent'),
        'logistic_regression': make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEED)),
        'hist_gradient_boosting': make_pipeline(SimpleImputer(strategy='median'), HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=1.0, random_state=SEED)),
    }
    validation = {}
    for name, model in models.items():
        model.fit(xa, ya)
        validation[name] = metrics(model, xv, yv)
    diagnostic_tree = DecisionTreeClassifier(max_depth=6, random_state=SEED).fit(xa, ya)
    winner = max((n for n in models if n != 'majority_baseline'), key=lambda n: validation[n]['balanced_accuracy'])
    models[winner].fit(x, y)
    models['majority_baseline'].fit(x, y)
    report = {
        'dataset_source': 'User-supplied CSV files; collection method, provenance, and license are not documented in the supplied files.',
        'dataset_reality': 'Unknown: real-world origin versus synthetic generation has not been verified.',
        'outcome': 'Placement_Status: Placed versus Not Placed; definition and observation period not provided.',
        'input_features': FEATURES,
        'scale_note': 'Coding_Skills and Communication_Skills appear on a 1-10 scale in the supplied files. Their relationship to dashboard percentages is unverified.',
        'excluded_features': ['Student_ID', 'Age', 'Gender', 'Degree', 'Branch', 'Soft_Skills_Rating'],
        'excluded_note': 'Identifiers, demographics, and fields with no direct current-dashboard equivalent were not used.',
        'train_sha256': checksum(args.train), 'test_sha256': checksum(args.test),
        'train_rows_original': original_train_rows, 'train_rows_removed_for_test_feature_overlap': matching_train_rows,
        'train_rows_used_after_overlap_and_duplicate_removal': len(clean),
        'validation_rows': len(xv), 'fit_rows_for_selection': len(xa), 'test_rows': len(test),
        'train_label_counts': train[TARGET].value_counts().to_dict(), 'test_label_counts': test[TARGET].value_counts().to_dict(),
        'train_test_id_overlap': len(train_id & test_id), 'train_test_model_feature_overlap': overlap,
        'train_duplicate_feature_rows_original': train_duplicate_rows,
        'test_duplicate_feature_rows': int(test.duplicated(FEATURES).sum()),
        'random_seed': SEED, 'selection_rule': 'Highest validation balanced accuracy among non-baseline models; refit on deduplicated training rows with test-input overlaps removed.',
        'validation_metrics': validation, 'selected_model': winner,
        'label_rule_diagnostic': {'model': 'Decision tree, max depth 6, 8 input features',
                                  'leaves': int(diagnostic_tree.get_n_leaves()),
                                  'training_accuracy': accuracy_score(ya, diagnostic_tree.predict(xa)),
                                  'validation_accuracy': accuracy_score(yv, diagnostic_tree.predict(xv)),
                                  'interpretation': 'Near-perfect agreement with a small rule tree is a warning sign; it does not prove the data are synthetic.'},
        'test_metrics': {winner: metrics(models[winner], xt, yt), 'majority_baseline': metrics(models['majority_baseline'], xt, yt)},
        'limitations': ['Provenance, consent, outcome definition, and real-versus-synthetic origin are unverified.',
                        'The supplied split may come from one source, so test performance is not external validation.',
                        'Duplicate feature vectors may represent distinct students; conservative deduplication discards some valid observations.',
                        'No independent technical assessment score is provided; current readiness model expects one.',
                        'Placement outcome and current readiness label are not interchangeable.',
                        'High test scores would not establish accuracy or fairness at LPU.',
                        'Probabilities are not calibrated or validated for individual placement decisions.'],
        'python_version': platform.python_version(), 'scikit_learn_version': sklearn.__version__,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    joblib.dump(models[winner], args.out/'research_placement_model.joblib')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
