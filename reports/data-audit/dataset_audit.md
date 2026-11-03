# Dataset audit report

Generated from `C:\Users\Gnanadeep Charan\OneDrive\문서\LPU-Placement-Intelligence-master\LPU-Placement-Intelligence-master`.

This report is an evidence snapshot, not provenance approval. External source, license, consent, and label claims remain unverified until documented by the data owner.

**Datasets:** 7  
**Rows:** 4048  
**Blocking findings:** 3

| Dataset | Rows | Missing | Duplicates | Target | Status | Permitted use |
|---|---:|---:|---:|---|---|---|
| `campus_recruitment_kaggle.csv` | 215 | 67 | 0 | `status` | blocked | external_validation_only_until_license_and_provenance_review |
| `college_placement_engineering.csv` | 2966 | 0 | 1829 | `PlacedOrNot` | blocked | external_validation_only_until_license_and_provenance_review |
| `engineering_skills_placement.csv` | 99 | 0 | 0 | `placed` | review_required | external_validation_only_until_license_and_provenance_review |
| `job_placement_features.csv` | 215 | 0 | 0 | `status` | review_required | external_validation_only_until_license_and_provenance_review |
| `placement_iq_academic.csv` | 100 | 0 | 0 | `placement` | review_required | external_validation_only_until_license_and_provenance_review |
| `placement_package_salary.csv` | 200 | 0 | 0 | `package` | review_required | salary_research_only_not_readiness_training |
| `students.csv` | 253 | 0 | 2 | `placement_ready` | blocked | prototype_only_until_provenance_and_label_review |

## Blocking findings

- campus_recruitment_kaggle.csv: 67 missing values require a documented treatment.
- college_placement_engineering.csv: 1829 duplicate rows require investigation.
- students.csv: 2 duplicate rows require investigation.

## Required human review

- Verify source, license, collection date, owner, and permitted use for every dataset.
- Document how every target label was collected or generated.
- Confirm that duplicate rows are expected or remove/deduplicate through an approved process.
- Investigate missing values before imputation or exclusion.
- Review every potential leakage finding before model training.
- Do not combine datasets with different populations, feature meanings, or target definitions without a documented mapping.
