# Teacher brief: requirement check

This review compares the implemented project with the teacher-provided brief. A local implementation or a model evaluation does not by itself establish institutional validity or a public deployment.

| Requirement | Status and evidence |
| --- | --- |
| Project title and student-readiness platform | Present in the website and project README. The React website provides student, mentor and admin workspaces. |
| Student profile management | Present: profile inputs, saved assessments, evidence, corrections, goals and CV review. Some data still uses the transitional SQLite store; see `SUPABASE_MIGRATION.md`. |
| Data preprocessing | Present: `backend/data_pipeline.py` validates the schema, labels and missing values and explicitly handles exact duplicates. |
| Feature engineering | Present in the research XGBoost workflow: `backend/tune_xgboost.py` creates a coding/technical mean and an experience count, in addition to the original features. These engineered features are **not** part of the active website model. |
| Readiness prediction and score | Present: the active Gradient Boosting model uses nine inputs and returns a readiness ranking signal. The underlying `placement_ready` label and data source are unverified; it is not a verified placement probability. |
| Model comparison and ensembles | Present: `backend/compare_models.py` compares baselines and several algorithms; the active Gradient Boosting model is an ensemble. XGBoost is available as a separate research experiment. |
| Hyperparameter tuning | Added: `backend/tune_xgboost.py` performs a 3-fold grid search on the training split, selecting by balanced accuracy before evaluating the holdout. |
| Skill-gap analysis | Present: project-defined thresholds, role profiles, actions and recommendations in the student dashboard. They are advisory, not official LPU eligibility rules. |
| Explainable AI | Present: local one-feature sensitivity and counterfactual scenarios, global model importance, and an on-demand SHAP TreeExplainer view. SHAP is explicitly labeled in raw log-odds and is unavailable for unsupported/calibrated models. |
| Student dashboard and mentor support | Present: student overview and actions; mentor roster, follow-ups, coaching, resources and CV review. Access depends on the configured backend and Supabase state. |
| ML pipeline and artifact version | Present: dataset validation, evaluation, model persistence, a versioned active artifact and an offline tuning experiment. No automatic promotion of the research model occurs. |
| Deployment | **Partial:** local frontend/backend and Docker Compose deployment configurations exist. FastAPI is available as an optional ASGI wrapper around the same Flask API. No publicly hosted deployment, institutional access approval or external validation has been verified in this review. |

## Technology stack

- Python, pandas, NumPy and scikit-learn are used in the backend and ML pipeline.
- XGBoost, Matplotlib and Seaborn are used by the offline research experiment. Install `backend/requirements-research.txt` to reproduce it.
- SHAP is used by the authenticated, on-demand explanation endpoint and student factors panel. LIME is not included; the brief says SHAP/LIME.
- The working website uses React and Flask. `backend/asgi.py` adds an optional **FastAPI** entry point that mounts the existing Flask application and retains its authentication and CSRF checks. Streamlit is not used; the brief says Streamlit/FastAPI.
- GitHub workflow files exist locally under `.github/workflows`. The existence, ownership and current status of a remote GitHub repository have not been verified.

## Experiment and limitations

Run the optional comparison from the project root after installing the research dependencies:

```powershell
python backend/tune_xgboost.py
```

The report and confusion matrix are generated in `reports/teacher-brief-xgboost/`. The current run used 251 distinct rows, 200 for training and 51 for the held-out test. The tuned XGBoost candidate achieved 88.2% accuracy (45/51), versus 51.0% for a majority-class baseline on that split. Hyperparameter selection used only the training portion. This is a small same-dataset test of an unverified prototype label; it does not show real-world or LPU placement accuracy and does not replace the active model.

To run the existing API through the optional FastAPI wrapper after installing backend requirements:

```powershell
uvicorn --app-dir backend asgi:app --host 127.0.0.1 --port 5000
```

Use the documented environment configuration for the desired local or Supabase mode. The default project launcher still runs Flask; the FastAPI wrapper is an alternative entry point, not evidence that the website has been deployed publicly. The underlying Starlette WSGI adapter is deprecated in the currently installed version and should be replaced with a supported adapter before relying on it long term.

## Work still required before a real deployment

Verify dataset provenance, consent, outcome definition and role requirements; evaluate against separate representative LPU data; check calibration and approved subgroup performance; complete the Supabase data migration and access tests; and establish hosting, TLS, backups and monitoring. The current website remains an educational prototype.

The active artifact was serialized with scikit-learn 1.9.1; the Python environment checked during this review uses 1.9.0 and emits a compatibility warning when loading it. Restore the matching training environment or retrain and validate in the intended deployment environment before relying on its outputs.
