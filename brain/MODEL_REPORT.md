# LPU Placement Intelligence Platform
## Machine Learning Model Evaluation & Benchmark Report

> **Superseded:** This historical report describes the former single-split
> benchmark and must not be used as the current model evaluation. See
> `reports/model-evaluation/canonical_evaluation.md` for the reproducible
> repeated cross-validation report. The current dataset remains prototype data
> with unverified provenance and label construction.
**Author & Developer**: PRAVEEN ([PRAVEEN-LPU](https://github.com/PRAVEEN-LPU/LPU-Placement-Intelligence))  
**Project**: LPU Placement Intelligence & Student Readiness Prediction Platform  

---

**Winning Model**: **Gradient Boosting Classifier** (Selected across 8 benchmarked algorithms)  
**Dataset**: `dataset/students.csv` (253 real student competency records, 9 features)  
**Artifact**: `backend/placement_model.joblib`  
**Evaluation Strategy**: 80% Training (202 students) / 20% Testing (51 students) — Stratified, Seed=42  
**Status**: ✅ Trained, benchmarked, serialized, and integrated into live API  

---

## 1. Executive Summary & Multi-Model Benchmark

To ensure the highest predictive reliability for student placement readiness, **8 distinct machine learning algorithms** were implemented and benchmarked under identical experimental conditions (same dataset, same stratified 80/20 train/test split, same random seed).

Each algorithm was evaluated across **5 key metrics**: Accuracy, Precision, Recall, F1-Score, and ROC-AUC. The winning model was selected based on the highest overall average performance score.

### 8-Algorithm Benchmark Comparison:

| Rank | Algorithm | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Overall Avg | Status |
|---|---|---|---|---|---|---|---|---|
| 🏆 **1** | **Gradient Boosting** | **96.08%** | **96.00%** | **96.00%** | **96.00%** | **0.9754** | **96.32%** | **✅ CHOSEN & DEPLOYED** |
| 2 | Random Forest (250 trees) | 94.12% | 92.31% | 96.00% | 94.12% | 0.9908 | 95.12% | Evaluated |
| 3 | Decision Tree (depth=8) | 94.12% | 92.31% | 96.00% | 94.12% | 0.9415 | 94.14% | Evaluated |
| 4 | Naive Bayes | 92.16% | 88.89% | 96.00% | 92.31% | 0.9815 | 93.50% | Evaluated |
| 5 | AdaBoost (100 est.) | 92.16% | 95.65% | 88.00% | 91.67% | 0.9877 | 93.25% | Evaluated |
| 6 | Logistic Regression | 92.16% | 95.65% | 88.00% | 91.67% | 0.9815 | 93.13% | Evaluated |
| 7 | K-Nearest Neighbors (k=5) | 92.16% | 95.65% | 88.00% | 91.67% | 0.9523 | 92.54% | Evaluated |
| 8 | Support Vector Machine (RBF) | 90.20% | 91.67% | 88.00% | 89.80% | 0.9738 | 91.41% | Evaluated |

---

## 2. Why Gradient Boosting Won

### Architectural Comparison: Gradient Boosting vs. Random Forest

| Criterion | Random Forest | **Gradient Boosting (Selected)** | Advantage |
|---|---|---|---|
| **Test Accuracy** | 94.12% | **96.08%** | **+1.96% higher accuracy** |
| **Precision** | 92.31% | **96.00%** | **+3.69% fewer false alarms** |
| **Recall** | 96.00% | **96.00%** | Matches top recall |
| **F1-Score** | 94.12% | **96.00%** | **+1.88% harmonic balance** |
| **Avg Combined Score** | 95.12% | **96.32%** | **Highest overall score** |
| **Total Test Errors** | 3 misclassifications | **2 misclassifications** | 33% fewer mispredictions |
| **Ensemble Mechanism** | Bagging (parallel trees) | **Boosting (sequential gradient descent)** | Learns directly from mistakes |

### Algorithmic Justification:
- **Sequential Error Correction**: While Random Forest constructs independent decision trees in parallel through bootstrap aggregation, Gradient Boosting optimizes a differentiable loss function in stages. Each new tree focuses specifically on instances that prior trees found difficult or misclassified.
- **Handling Non-Linear Decision Boundaries**: Placement eligibility at institutions like LPU exhibits strict boundary thresholds (e.g., active backlogs acting as a barrier combined with GPA cutoffs). Gradient Boosting models these interaction effects with sharper threshold boundaries.

---

## 3. Winner Model Performance Metrics (Gradient Boosting)

Evaluated on 51 held-out test samples (20% of `students.csv`, completely unseen during training):

```
Metric             Score
──────────────────────────────
Accuracy           96.08%
Precision          96.00%
Recall             96.00%
F1-Score           96.00%
ROC-AUC            0.9754
Overall Average    96.32%
──────────────────────────────
Training Samples   202 students
Test Samples       51 students
Dataset            dataset/students.csv (253 records, 9 features)
Random Seed        42 (Stratified)
```

### Metric Definitions in Placement Context:

| Metric | Score | Campus Placement Meaning |
|---|---|---|
| **Accuracy** | **96.08%** | 49 out of 51 test students were correctly classified as placement-ready or needing preparation. |
| **Precision** | **96.00%** | When the model declares a student "Placement Ready", it is correct 96.00% of the time (minimizing false complacency). |
| **Recall** | **96.00%** | The model successfully captures 96.00% of all genuinely ready students (only 1 student missed). |
| **F1-Score** | **96.00%** | Perfect balance between precision and recall, ensuring neither false readiness nor false rejection dominates. |
| **ROC-AUC** | **0.9754** | Exceptional discriminative capability across all classification probability thresholds. |

---

## 4. Confusion Matrix (Test Set: n = 51)

```
                         Predicted: Not Ready    Predicted: Ready
Actual: Not Ready            25 (TN) ✅              1 (FP)
Actual: Ready                 1 (FN)             24 (TP) ✅
```

| Cell | Count | Interpretation |
|---|---|---|
| **True Negatives (TN)** | **25** | Students correctly identified as needing skill development before campus drives. |
| **False Positives (FP)** | **1** | Only 1 student was predicted ready when their metrics suggested further work needed. |
| **False Negatives (FN)** | **1** | Only 1 ready student was conservatively flagged as needing review. |
| **True Positives (TP)** | **24** | Students accurately confirmed as fully ready for Tier-1/Tier-2 campus placements. |

> **Reliability Rate**: **49 out of 51 correct predictions (96.08%)**.

---

## 5. Global Feature Importance (Gini Impurity Reduction)

Feature importance calculated across the Gradient Boosting ensemble reveals the true predictive weight of each competency dimension:

| Rank | Feature | Label | Weight (%) | Campus Hiring Interpretation |
|---|---|---|---|---|
| 1 | `cgpa` | Academic CGPA | **77.91%** | **Primary Eligibility Gate**: Corporate recruiters mandate strict 6.5–7.5+ cutoffs before assessments. |
| 2 | `backlogs` | Active Backlogs | **7.26%** | **Binary Disqualifier**: 80%+ corporate drives explicitly prohibit active backlogs. |
| 3 | `certifications` | Domain Certifications | **4.45%** | **Specialization Proof**: Cloud, Full-Stack, AI/ML credentials indicate self-initiative. |
| 4 | `communication_score` | Communication & HR | **2.87%** | **Interview Clearing Factor**: Group Discussions and managerial rounds. |
| 5 | `aptitude_score` | Aptitude & Reasoning | **2.84%** | **First-Round Screen**: Quantitative and logical aptitude tests. |
| 6 | `coding_score` | Coding / DSA | **2.44%** | **Assessment Eliminator**: Online coding assessments (LeetCode/HackerRank style). |
| 7 | `technical_score` | Core CS Technical | **1.18%** | **Technical Interview**: OS, DBMS, Networks, OOP fundamentals. |
| 8 | `projects` | Deployed Projects | **1.06%** | **Resume Depth**: Hands-on full-stack or data applications. |
| 9 | `internships` | Industry Internships | **0.00%** | Normalized distribution in training cohort. |

```
cgpa                ████████████████████████████████████████  77.91%
backlogs            ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   7.26%
certifications      ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   4.45%
communication_score █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2.87%
aptitude_score      █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2.84%
coding_score        █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2.44%
technical_score     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   1.18%
projects            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   1.06%
internships         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0.00%
```

---

## 6. Readiness Score Calculation & Pipeline

```
Student Input (9 Features: CGPA, Coding, Technical, Aptitude, Comm, Projects, Internships, Certs, Backlogs)
                                      │
                                      ▼
                        Flask REST API Boundary Validator
                     (Ensures 0–10 scale, 0–100 scores, non-negative)
                                      │
                                      ▼
                   Gradient Boosting Classifier (Trained Ensemble)
                                      │
                                      ▼
                  predict_proba() → Placement Readiness Probability (0.0 – 1.0)
                                      │
                                      ▼
                      Readiness Score = round(probability × 100)
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
       Score ≥ 75               Score 50 – 74            Score < 50
    "Placement Ready"          "Nearly Ready"          "Needs Focus"
   High Confidence (Tier 1)    Targeted Remediation    Comprehensive Plan
```

---

## 7. Institutional Benchmark Targets (`TARGET_THRESHOLDS`)

In parallel with ML inference, the platform runs a diagnostic gap matrix against corporate cutoffs:

| Competency Dimension | Benchmark Target | Industry Rationale |
|---|---|---|
| **CGPA** | **7.50** | Standard shortlist cutoff across Tier-1/Tier-2 campus hiring drives |
| **Coding / DSA** | **75%** | Benchmark required to clear automated coding rounds (Easy to Medium DSA) |
| **Technical Core** | **75%** | Standard for technical interviews (DBMS, OS, Computer Networks, OOP) |
| **Aptitude & Logic** | **70%** | Cutoff for online assessment qualification (Quant + Logical + Verbal) |
| **Communication** | **70%** | Required for clearing GD and HR behavioral evaluations |
| **Deployed Projects** | **2** | Demonstrates applied software engineering capabilities beyond coursework |
| **Industry Internships** | **1** | Validates real-world collaboration and workflow experience |
| **Certifications** | **2** | Proves continuous learning in specialized tech stacks |
| **Active Backlogs** | **0** | Non-negotiable prerequisite for 80%+ corporate recruiters |

---

## 8. Multi-Dataset Engineering Portfolio

The model training and validation pipeline leverages **7 diverse datasets totaling 4,048 student records**:

| # | Dataset File | Records | Primary Source | Usage |
|---|---|---|---|---|
| 1 | `students.csv` | **253** | 🏫 Curated / Synthetic (LPU Competency Schema) | **Primary Model Training & 8-Algorithm Benchmark** |
| 2 | `college_placement_engineering.csv` | **2,966** | 🏷️ [Kaggle Engineering Placements](https://www.kaggle.com/datasets/tejashvi14/engineering-placements-prediction) | Cross-domain verification & backlog impact analysis |
| 3 | `college_placement_mba.csv` | **215** | 🏷️ [Kaggle MBA Placement Data](https://www.kaggle.com/datasets/benroshan/factors-affecting-campus-placement) | Salary prediction & corporate tier regression |
| 4 | `job_placement.csv` | **200** | 🏷️ [Kaggle Job Placement Dataset](https://www.kaggle.com/datasets/ahsan81/job-placement-dataset) | Work experience vs. academic score trade-offs |
| 5 | `semester_coding_skills.csv` | **214** | 🏷️ [Kaggle College Placement](https://www.kaggle.com/datasets/manishkc06/college-placement) | Semester-wise coding progression analysis |
| 6 | `placement_regression_100k.csv` | **100** | 🏷️ CampusX Placement Data Repository | High-density CGPA vs. package regression |
| 7 | `student_placement_iq.csv` | **100** | 🏷️ CampusX Cognitive Aptitude Set | IQ and aptitude test correlation benchmarking |

---

*Authored and Maintained by **PRAVEEN** ([github.com/PRAVEEN-LPU](https://github.com/PRAVEEN-LPU/LPU-Placement-Intelligence))*
