# Project-folder dataset: 1,000-record experiment

This experiment uses **`dataset/college_placement_engineering.csv`** from the project folder, not the separately supplied placement dataset. The live website's readiness model was not changed.

The original CSV has 2,966 rows, including 1,829 exact duplicate rows. After removing exact duplicates, 1,137 distinct full rows remain. Distinct rows are not proof of distinct individuals. A stratified sample of 1,000 of these rows was selected using seed 42. No new records were generated.

The target is `PlacedOrNot`; its source and exact meaning have not been independently verified. The model uses Age, Stream, Internships, CGPA, Hostel and HistoryOfBacklogs; Gender is excluded. Age and hostel status can introduce bias, and the model has not been validated for individual decisions. The dataset's provenance, license and whether the records are real or synthetic remain unverified.

## Method and result

All rows sharing the six model inputs were kept in the same group during the split, preventing matching input combinations from appearing in both training and test sets. The split produced 792 training records and 208 test records. Within the training split, 631 records were used to fit candidate models and 161 to select a model on validation balanced accuracy; the selected model was then refitted using all 792 training records.

| Measure | Result |
| --- | ---: |
| Selected model | Random forest |
| Test accuracy | 80.77% (168 of 208) |
| Test balanced accuracy | 80.89% |
| Test precision for label 1 | 85.84% |
| Test recall for label 1 | 80.17% |
| Majority-class test baseline | 58.17% |

Of the 87 test records labeled 0, the model predicted 71 correctly and 16 as 1. Of the 121 labeled 1, it predicted 97 correctly and 24 as 0. An approximate 95% Wilson interval for accuracy is 74.9%–85.5%; its assumptions do not account for dependence within groups.

The test data comes from the same CSV as the training data, not a verified independent LPU cohort. These results cannot establish the model's accuracy for real LPU student outcomes. It is also not a replacement for the readiness model: this dataset lacks technical, coding, aptitude, communication, projects and certifications inputs, and uses a different target.

## Reproduce

With pandas, scikit-learn, and joblib installed:

```powershell
python train_project_1000.py --data <project>/dataset/college_placement_engineering.csv --out <output-folder>
```

`evaluation.json` records source hash, sample sizes, split, validation metrics, and software versions. The saved `research_placement_model.joblib` is a research artifact; only load joblib files from trusted sources.
