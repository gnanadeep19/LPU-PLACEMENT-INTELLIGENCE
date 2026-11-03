# LPU Placement Intelligence Platform
## System Architecture & API Technical Reference

---

**Document Purpose**: Technical specification covering system component design, inter-service communication, REST API contracts, data schemas, and institutional governance policies.  
**Last Updated**: After Phase 3 (Flask API) completion  

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     REACT + VITE FRONTEND                       │
│                     http://localhost:5173                        │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Student Input  │  │  Readiness   │  │  Tabbed Diagnostic │  │
│  │  9 Parameters   │  │  Gauge 0-100 │  │  Panel (3 tabs)    │  │
│  │  Sliders + Nums │  │  SVG Gauge   │  │  Gaps / Roadmap /  │  │
│  └────────┬────────┘  └──────────────┘  │  Factors Chart     │  │
│           │  POST /api/predict (JSON)   └────────────────────┘  │
└───────────┼─────────────────────────────────────────────────────┘
            │  Vite Proxy: /api → http://127.0.0.1:5000
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FLASK REST API ENGINE                        │
│                     http://127.0.0.1:5000                        │
│                                                                  │
│  GET  /api/health       ─── Liveness + model availability        │
│  GET  /api/model-info   ─── Metrics, thresholds, metadata        │
│  POST /api/predict      ─── Validate → Infer → Gap → Recommend   │
│                                                                  │
│  Flask-CORS enabled · Structured JSON error responses            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MACHINE LEARNING ENGINE                        │
│                   backend/model.py                               │
│                                                                  │
│  Training Data    : 2,500 synthetic student records              │
│  Algorithm        : Random Forest (250 trees, Gini, balanced)    │
│  Inference        : predict_proba() → readiness score 0-100      │
│  Explainability   : Global Gini feature importance               │
│  Gap Analysis     : Rule-based vs. institutional cutoffs         │
│  Recommendations  : Priority-ranked prescriptive roadmap         │
│  Artifact         : placement_model.joblib (Joblib serialization)│
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Student Feature Schema

Nine input features define the student competency profile. These are the only inputs to the model; no personally identifying information is used.

| # | Field | Python Type | Input Range | Institutional Cutoff | Hiring Stage |
|---|---|---|---|---|---|
| 1 | `cgpa` | float | 0.0 – 10.0 | **≥ 7.50** | Eligibility screening |
| 2 | `coding_score` | int | 0 – 100 | **≥ 75%** | Coding assessment round |
| 3 | `technical_score` | int | 0 – 100 | **≥ 75%** | Technical interview round |
| 4 | `aptitude_score` | int | 0 – 100 | **≥ 70%** | Aptitude / online assessment |
| 5 | `communication_score` | int | 0 – 100 | **≥ 70%** | HR interview / GD round |
| 6 | `projects` | int | 0 – 30 | **≥ 2** | Resume and technical depth |
| 7 | `internships` | int | 0 – 15 | **≥ 1** | Industry exposure |
| 8 | `certifications` | int | 0 – 30 | **≥ 2** | Domain specialization |
| 9 | `backlogs` | int | 0 – 20 | **= 0** | Company eligibility filter |

---

## 3. REST API Specification

### 3.1 `GET /api/health`

**Purpose**: Liveness check; confirms the Flask process is up and the model artifact is loaded.

**Response (200 OK)**
```json
{
  "status": "ok",
  "service": "LPU Placement Intelligence API",
  "model_loaded": true
}
```

---

### 3.2 `GET /api/model-info`

**Purpose**: Returns training performance metrics, feature importance weights, and institutional thresholds.

**Response (200 OK)**
```json
{
  "status": "success",
  "model_version": "1.0.0-rf-demo",
  "trained_at": "2026-10-21T21:25:48",
  "features": ["cgpa", "technical_score", "aptitude_score", "communication_score",
               "coding_score", "projects", "internships", "certifications", "backlogs"],
  "metrics": {
    "accuracy": 0.91,
    "precision": 0.9064,
    "recall": 0.9237,
    "f1_score": 0.9149,
    "roc_auc": 0.9724,
    "confusion_matrix": [[213, 25], [20, 242]],
    "test_rows": 500,
    "train_rows": 2000,
    "data_note": "Synthetic demonstration dataset..."
  },
  "feature_importance": {
    "cgpa": 25.18,
    "technical_score": 18.82,
    "coding_score": 16.76,
    "backlogs": 12.57,
    "aptitude_score": 6.67
  }
}
```

---

### 3.3 `POST /api/predict`

**Purpose**: Accepts a student profile, validates all 9 fields, runs ML inference, and returns a structured diagnostic report.

**Request Body**
```json
{
  "cgpa": 7.8,
  "technical_score": 74,
  "aptitude_score": 68,
  "communication_score": 72,
  "coding_score": 65,
  "projects": 2,
  "internships": 1,
  "certifications": 2,
  "backlogs": 0
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "readiness_score": 72,
    "readiness_category": "Nearly Ready",
    "readiness_description": "Solid foundation with identifiable gaps...",
    "badge_variant": "warning",
    "model_probability": 0.7241,
    "probability_note": "Uncalibrated Random Forest predict_proba output.",
    "top_factors": [
      { "feature": "cgpa", "label": "Academic CGPA", "importance": 25.18 },
      { "feature": "technical_score", "label": "Technical Knowledge", "importance": 18.82 },
      { "feature": "coding_score", "label": "Coding Proficiency", "importance": 16.76 }
    ],
    "skill_gaps": [
      {
        "skill": "Coding Proficiency",
        "current": 65,
        "target": 75,
        "unit": "%",
        "status": "Moderate Gap",
        "severity": "warning",
        "action": "Complete 2 medium DSA problems daily on LeetCode/HackerRank."
      }
    ],
    "recommendations": [
      {
        "category": "Technical Assessment",
        "priority": "Medium",
        "badge": "DSA & Problem Solving",
        "title": "Structured 45-Day DSA Sprint",
        "details": "First-round coding eliminator assessments require DSA fluency.",
        "action_items": [
          "Solve Blind 75 LeetCode problems focusing on Trees and Dynamic Programming.",
          "Practice under timed 45-minute constraints on HackerRank.",
          "Master C++ STL or Java Collections for efficient implementations."
        ]
      }
    ],
    "disclaimer": "Educational demonstration model trained on synthetic data..."
  }
}
```

**Error Responses**

| HTTP Code | Trigger Condition | Example Message |
|---|---|---|
| 400 | Missing required field | `"Missing required field: 'cgpa'."` |
| 400 | Value out of bounds | `"CGPA must be a number between 0.0 and 10.0"` |
| 400 | Wrong content type | `"Request content-type must be application/json."` |
| 500 | Internal model error | `"An error occurred during prediction: ..."` |

---

## 4. Readiness Score Classification

The readiness score is derived from the model's `predict_proba()` output multiplied by 100.

| Score Range | Category | Badge | Description |
|---|---|---|---|
| 75 – 100 | Placement Ready | 🟢 Success | Strong profile. Focus on interview polish and dream offers. |
| 50 – 74 | Nearly Ready | 🟡 Warning | Solid foundation with identifiable gaps. 4-week targeted prep recommended. |
| 0 – 49 | Needs Focus | 🔴 Critical | Significant academic or skill gaps. Immediate intervention required. |

---

## 5. Skill Gap Severity Levels

| Severity | Label | Visual Treatment | Interpretation |
|---|---|---|---|
| `met` | Target Met | Green left border | Score meets or exceeds the institutional cutoff |
| `warning` | Moderate Gap | Amber left border | Score is below cutoff but within recoverable range |
| `critical` | Critical Gap | Red left border | Score significantly below cutoff; urgent action needed |

A special case: any `backlogs > 0` is always classified as `critical` regardless of other scores, because most corporate recruiters enforce a zero-backlog eligibility criterion.

---

## 6. Data Generation Methodology

The synthetic dataset is generated in `model.py → generate_synthetic_student_data()` using the following design:

| Feature | Generation Method | Rationale |
|---|---|---|
| `cgpa` | Normal(μ=7.2, σ=1.1), clipped [5.0, 9.9] | Reflects realistic university GPA distribution |
| `coding_score` | Linear function of CGPA + Gaussian noise | Moderate positive correlation with academic performance |
| `technical_score` | Linear function of coding + CGPA + noise | Shared knowledge base with coding |
| `aptitude_score` | Normal(μ=65, σ=14), clipped [25, 98] | More independent of GPA; test-taking aptitude varies |
| `communication_score` | Normal(μ=67, σ=13), clipped [30, 98] | Largely independent of technical scores |
| `projects` | Categorical weights [0.10, 0.25, 0.35, 0.20, 0.08, 0.02] | Most students have 1-2 projects |
| `internships` | Categorical weights [0.50, 0.35, 0.12, 0.03] | Majority have zero internships |
| `certifications` | Categorical weights [0.20, 0.35, 0.25, 0.15, 0.05] | Mixed distribution |
| `backlogs` | Categorical weights [0.78, 0.14, 0.06, 0.02] | Small minority have standing backlogs |
| `placement_ready` | Logistic function of all features + noise | Non-linear label generation mimicking real selection |

---

## 7. Privacy, Ethics & Institutional Governance

### Data Privacy
- The model feature vector contains **zero personally identifying information**. Student names, registration numbers, phone numbers, email addresses, date of birth, and gender are intentionally excluded to prevent algorithmic bias and comply with data protection principles.

### Synthetic Data Policy
- All model training, evaluation, and dashboard demonstrations use fully synthetic data generated from documented statistical distributions. No actual student records were used.
- For institutional deployment, the following additional steps are required:
  1. Formal approval from LPU Ethics Committee and Placement Division.
  2. Data sharing agreements with appropriate consent mechanisms.
  3. Probability calibration (Platt scaling or isotonic regression).
  4. Regular disparate impact audits across student sub-groups.
  5. Human mentor oversight before any placement advisory decisions.

### Disclaimer
The readiness score is a diagnostic indicator for educational guidance. It is not a contractual guarantee of placement, a ranking instrument, or a substitute for qualified career advisory from placement coordinators.

---

*This document is maintained in `brain/MODULE_ARCHITECTURE.md` and updated after every architectural change or API modification.*
