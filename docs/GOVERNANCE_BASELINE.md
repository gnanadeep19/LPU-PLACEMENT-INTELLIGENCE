# Governance and risk baseline

## 1. Current product status

The repository currently contains an educational prototype:

- A Flask API loads a serialized Gradient Boosting model using the nine-feature
  schema in `dataset/students.csv`.
- The source dataset has 253 rows, including two exact duplicate rows, and the
  source/label provenance needs review before real institutional use.
- The frontend includes local model explanations, role workspaces, owned
  assessment history, cohort-scoped mentor access, shared coaching records,
  target-role comparisons, and a manually maintained placement pipeline.
- Local credential authentication, CSRF-protected sessions, access checks,
  minimum cohort-size suppression, and a basic audit table are implemented.
- The system is not connected to LPU SSO/MFA, institutional data verification,
  consent management, or a retention/deletion workflow. Target-role requirements
  are project-defined and not official placement criteria.

These limitations are release-blocking for institutional production use.

## 2. Data classification

| Data class | Examples | Required handling |
|---|---|---|
| Public reference data | Public dataset documentation and aggregate benchmark results | Track source and license |
| De-identified academic data | Scores, skills, projects, internships, certifications | Restrict access, encrypt, retain only as needed |
| Account data | Email, role, authentication identifiers | Encrypt and apply least privilege |
| Assessment data | Predictions, explanations, recommendations, mentor notes | Restrict by role, audit access |
| Model governance data | Model artifacts, metrics, training metadata | Version, checksum, approval workflow |

## 3. Decision safeguards

Predictions are advisory. A mentor or placement officer must be able to review the input, criteria, and explanation before taking action.

The platform must:

- Display the selected readiness profile and its version.
- Display the model version used.
- Allow students to correct inaccurate profile data.
- Provide a route for human review of unexpected results.
- Avoid automatic exclusion based only on a model score.
- Record model and criteria changes in an audit log.

## 4. Fairness and inclusion

Before production:

- Identify protected or sensitive attributes that must be excluded from model features.
- Measure performance across approved subgroups where legally and ethically appropriate.
- Compare false-positive and false-negative rates.
- Document any material disparity and mitigation.
- Review recommendations for accessibility and socioeconomic bias.

Sensitive attributes must not be silently used as proxies for exclusion.

## 5. Model risk statements

The following statements must appear in user-facing documentation:

- A readiness estimate is not a placement guarantee.
- Model explanations describe associations used by the model and do not prove causation.
- Counterfactual results are estimates, not promises.
- Company and drive requirements can change; the published drive notice remains authoritative.
- Results depend on the accuracy and completeness of the student's inputs.

## 6. Ownership

| Area | Owner before production assignment | Required production owner |
|---|---|---|
| Product scope | Project team | Product owner |
| Data provenance and consent | Project team | Institutional data owner |
| Model quality | ML developer | ML owner/reviewer |
| Security and privacy | Project team | Security/privacy reviewer |
| Placement criteria | Project team | Placement office |
| Operations | Project team | Platform/SRE owner |

Production rollout requires named owners for every row.

## 7. Phase 2 audit status

The current repository audit is recorded in
`reports/data-audit/dataset_audit.md` and
`reports/data-audit/dataset_audit.json`.

The audit found three blocking data-quality findings:

- `students.csv` contains 2 exact duplicate rows.
- `college_placement_engineering.csv` contains 1,829 exact duplicate rows.
- `campus_recruitment_kaggle.csv` contains 67 missing `salary` values.

The audit also flags unverified provenance and possible identifier or leakage
fields. No source file was modified, deduplicated, imputed, or approved by the
audit. These findings must be resolved by the data owner before production
training or external validation.
