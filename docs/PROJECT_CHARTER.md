# LPU Placement Intelligence & Student Readiness Prediction Platform

## Phase 0 project charter

**Status:** Approved baseline for production development  
**Scope version:** 0.1  
**Last updated:** 2026-10-28

## 1. Product purpose

The platform is a decision-support system for students and placement mentors. It estimates a student's readiness for a defined placement profile, explains the factors that influenced the estimate, identifies measurable competency gaps, and recommends an improvement plan.

The system is not an admissions, employment, eligibility, or placement guarantee system. A prediction must never be used as the sole basis for rejecting a student, denying access to training, or making a legally or institutionally binding decision.

## 2. Canonical prediction target

The production platform will use the following canonical concept:

> **Readiness probability:** the estimated probability that a student meets the readiness criteria for a selected placement profile at the time of assessment.

A placement profile may represent an institution-wide readiness baseline, a job role, or a placement drive. The profile must identify its criteria and version.

The following concepts are separate and must not be conflated:

| Concept | Meaning |
|---|---|
| Readiness probability | Model-estimated likelihood of meeting a configured readiness profile |
| Readiness score | Display-friendly 0–100 representation of the calibrated probability |
| Eligibility | Deterministic check against published company or drive criteria |
| Placement outcome | Historical outcome such as assessment progression or offer received |
| Salary estimate | Separate regression problem and separate model |

Until verified outcome data is available, the current prototype must be described as a **diagnostic readiness assessment**, not an actual placement predictor.

## 3. In-scope capabilities

### Student capabilities

- Create and maintain a competency profile.
- Submit an assessment against a named readiness profile.
- View calibrated readiness probability and category.
- See student-specific positive and negative model factors.
- Review threshold-based skill gaps, including certifications.
- Explore bounded what-if improvement scenarios.
- Receive measurable recommendations.
- Track assessments and progress over time.
- Export a diagnostic report.

### Mentor capabilities

- View assigned students.
- Review assessment history and explanations.
- Identify urgent and common gaps.
- Assign or adjust improvement plans.
- Add mentor notes.
- Compare cohort-level trends without exposing unnecessary personal data.
- Export student and cohort reports.

### Placement officer capabilities

- Create and version placement-drive profiles.
- Configure published criteria.
- Generate eligibility lists from deterministic rules.
- Review anonymized cohort analytics.
- Compare readiness estimates with later placement outcomes.

### Administrator and ML administrator capabilities

- Manage users, roles, and access.
- Manage data imports and validation.
- Register, evaluate, approve, deploy, and roll back model versions.
- Review audit logs, monitoring, and data-quality alerts.

## 4. Out-of-scope decisions

The system will not:

- Guarantee campus placement or salary.
- Automatically reject or exclude a student from a placement drive.
- Infer protected characteristics or use them as hidden scoring inputs.
- Treat global feature importance as an explanation for an individual student.
- Claim that external datasets are part of the live model unless they are explicitly integrated and validated.
- Present uncalibrated `predict_proba` output as confidence.

## 5. Readiness categories

The initial product categories are:

| Score range | Category | Intended interpretation |
|---:|---|---|
| 0–39 | Needs substantial preparation | Multiple high-priority gaps require intervention |
| 40–59 | Developing | Foundational readiness is incomplete |
| 60–74 | Nearly ready | Targeted preparation is recommended before the selected profile |
| 75–89 | Placement ready | Meets the configured diagnostic readiness level |
| 90–100 | Strongly prepared | Strong diagnostic alignment; continue role-specific preparation |

These are product defaults, not universal hiring rules. They must be configurable and validated during the pilot.

## 6. Required explanation contract

Every prediction response must eventually include:

- Model version and readiness-profile version.
- Calibrated probability and score category.
- Positive factors for this student.
- Negative factors for this student.
- Current value, target value, direction, and contribution for each displayed factor.
- Skill gaps and their severity.
- Bounded counterfactual scenarios.
- A statement that model explanations describe model behavior, not causation.

Global feature importance may be shown separately as model education, but it must be labelled **global**.

## 7. Data and label principles

- Every training dataset must have a documented owner, source, license, collection date, schema, and permitted use.
- The label-generation process must be documented before model claims are made.
- Synthetic, curated, and verified outcome data must be explicitly distinguished.
- The current `students.csv` dataset is a prototype training source until its provenance and label construction are verified.
- No personal identifiers are required by the model and must not be included in training data.
- Data leakage, duplicate students, post-outcome features, and derived labels must be checked before training.

## 8. Success criteria

Phase 0 is complete when:

- Product terminology is consistent.
- The target and non-goals are documented.
- Roles and access boundaries are documented.
- Readiness categories and score semantics are documented.
- Data/model risk limitations are explicit.
- Production release gates are defined.
- README wording matches the current prototype scope.

Later phases are not allowed to promote the platform to production based on accuracy alone. The model must also pass data-quality, calibration, fairness, explainability, security, and operational gates.
