"""
Kaggle Campus Recruitment Dataset — Training & Comparative Analysis
====================================================================
Dataset: dataset/campus_recruitment_kaggle.csv (215 records)
Source: Kaggle (Benison Sunil / Shubham Jain)
URL: https://www.kaggle.com/datasets/benisonsunil/campus-recruitment

This script provides:
1. Exploratory Data Analysis (EDA) of the Kaggle placement dataset
2. Machine Learning training (Random Forest Classifier) on real historical placement data
3. Feature importance analysis (which academic and experience factors drive placements)
4. Comparative analysis with the LPU Student Readiness Competency model (students.csv)
"""

import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset", "campus_recruitment_kaggle.csv")


def load_and_preprocess(filepath: str) -> pd.DataFrame:
    """Loads and encodes the Kaggle dataset for classification."""
    df = pd.read_csv(filepath)

    # Convert binary categoricals
    df["workex_binary"] = (df["workex"].str.strip().str.lower() == "yes").astype(int)
    df["gender_binary"] = (df["gender"].str.strip().str.upper() == "M").astype(int)
    df["target"] = (df["status"].str.strip() == "Placed").astype(int)

    return df


def run_eda(df: pd.DataFrame):
    """Prints exploratory data analysis on the Kaggle records."""
    total = len(df)
    placed = df["target"].sum()
    not_placed = total - placed

    print("=" * 75)
    print("   KAGGLE CAMPUS RECRUITMENT DATASET — EXPLORATORY DATA ANALYSIS")
    print("=" * 75)
    print(f"Total Student Records : {total}")
    print(f"Placed Students       : {placed} ({placed / total * 100:.1f}%)")
    print(f"Not Placed Students   : {not_placed} ({not_placed / total * 100:.1f}%)")

    # Work experience impact
    with_workex = df[df["workex_binary"] == 1]
    no_workex = df[df["workex_binary"] == 0]
    p_with = with_workex["target"].mean() * 100 if len(with_workex) > 0 else 0
    p_no = no_workex["target"].mean() * 100 if len(no_workex) > 0 else 0

    print("\n--- Work Experience Impact ---")
    print(
        f"Students with prior work experience    : {len(with_workex)} (Placement Rate: {p_with:.1f}%)"
    )
    print(
        f"Students without prior work experience : {len(no_workex)} (Placement Rate: {p_no:.1f}%)"
    )

    print("\n--- Average Academic Percentages by Placement Status ---")
    grouped = df.groupby("status")[["ssc_p", "hsc_p", "degree_p", "etest_p", "mba_p"]].mean()
    print(grouped.round(2).to_string())
    print("-" * 75)


def train_and_evaluate(df: pd.DataFrame):
    """Trains a Random Forest classifier on the Kaggle dataset."""
    features = ["ssc_p", "hsc_p", "degree_p", "etest_p", "mba_p", "workex_binary", "gender_binary"]
    feature_labels = [
        "10th Grade % (ssc_p)",
        "12th Grade % (hsc_p)",
        "Undergrad Degree % (degree_p)",
        "Employability Test % (etest_p)",
        "MBA / Postgrad % (mba_p)",
        "Work Experience (Yes/No)",
        "Gender (M/F)",
    ]

    X = df[features]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        class_weight="balanced",
        random_state=42,
    )
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    y_prob = rf.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "=" * 75)
    print("      MACHINE LEARNING PERFORMANCE (Random Forest on Kaggle Data)")
    print("=" * 75)
    print(f"Training Set Size : {len(X_train)} students")
    print(f"Testing Set Size  : {len(X_test)} students (20% holdout)")
    print("-" * 75)
    print(f"Accuracy          : {acc * 100:.2f}%")
    print(f"Precision         : {prec * 100:.2f}%")
    print(f"Recall            : {rec * 100:.2f}%")
    print(f"F1-Score          : {f1 * 100:.2f}%")
    print(f"ROC-AUC           : {auc:.4f}")
    print(f"Confusion Matrix  : [[True Neg: {cm[0,0]}, False Pos: {cm[0,1]}],")
    print(f"                     [False Neg: {cm[1,0]}, True Pos: {cm[1,1]}]]")
    print("-" * 75)

    # Feature Importance
    importances = rf.feature_importances_ * 100
    sorted_idx = np.argsort(importances)[::-1]

    print("\nFeature Importance Breakdown:")
    for rank, idx in enumerate(sorted_idx, start=1):
        bar = "#" * int(importances[idx] / 2)
        print(f"  {rank}. {feature_labels[idx]:<32} {bar:<25} {importances[idx]:5.2f}%")

    print("\n" + "=" * 75)
    print("     COMPARISON: KAGGLE DATASET vs. LPU STUDENTS.CSV DATASET")
    print("=" * 75)
    print("""
  Dimension               Kaggle Dataset (215 records)       LPU students.csv (253 records)
  ---------------------   -------------------------------    -------------------------------
  Primary Focus           Historical MBA Campus Placement    Engineering / CS Technical Readiness
  Key Predictors          Degree % (25%), 10th/12th marks    CGPA (25%), Technical (19%), Coding (17%)
  Practical Skills        Generic Employability Test         Hands-on Projects, Internships, Certs
  Risk Factor Modeled     Not Placed in Company Drive        Active Academic Backlogs (Blocking)
  Actionable Feedback     High-level percentage cutoffs      8-Dimension Specific Skill Gap Matrix
    """)
    print("=" * 75)


def main():
    if not os.path.exists(CSV_PATH):
        print(f"Error: Kaggle CSV not found at {CSV_PATH}")
        return

    df = load_and_preprocess(CSV_PATH)
    run_eda(df)
    train_and_evaluate(df)


if __name__ == "__main__":
    main()
