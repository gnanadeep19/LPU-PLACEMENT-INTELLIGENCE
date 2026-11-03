# Supplied student placement dataset: research experiment

This experiment uses the supplied `train.csv` and `test.csv` files and is **not connected to the dashboard**. The model predicts the supplied `Placement_Status` label. This label is not equivalent to the dashboard's readiness score.

## Dataset

- Original training file: 45,000 records; supplied test file: 5,000 records.
- The files do not document how the data was collected, what placement means, its observation period, consent or license. Whether the records are real or synthetic **has not been established**.
- Eight inputs: CGPA, internships, projects, coding skills, communication skills, aptitude test score, certifications, and backlogs. Coding and communication scores in these files range from 1 to 10; equivalence to the dashboard's percentage inputs has not been established.
- Student ID, age, gender, degree, branch, and soft skills rating were excluded. There is no independent technical-score field, although the current dashboard model expects one.

## Evaluation method

There were 112 distinct combinations of the eight model inputs appearing in both supplied files, corresponding to 115 training rows. These training rows were removed before fitting. The remaining training data was deduplicated on the eight model inputs, leaving **44,384 unique input combinations**; distinct students can legitimately share inputs, so this conservative exclusion can discard valid records. The supplied test set contains seven repeated input rows and was kept intact; its 5,000 rows are not all independent input combinations.

The cleaned training set was split into 35,507 fitting rows and 8,877 validation rows. Logistic regression and histogram gradient boosting were trained, and the model with higher validation balanced accuracy was selected. The chosen model was refitted on all 44,384 cleaned training rows and evaluated against the supplied test file. A majority-class baseline was also evaluated.

## Results

| Model | Validation accuracy | Test accuracy | Test balanced accuracy |
| --- | ---: | ---: | ---: |
| Majority baseline | 63.9% | 63.76% | 50.0% |
| Logistic regression | 86.2% | Not evaluated | Not evaluated |
| Histogram gradient boosting | 99.98% | **100%** | **100%** |

The selected model correctly classified all 5,000 test rows: 3,188 labeled Not Placed and 1,812 labeled Placed. The 95% Wilson interval for this test accuracy is approximately 99.92%–100%, assuming independent test observations; repeated input combinations mean that assumption is not fully met.

**The 100% result requires investigation.** A decision tree with only 12 leaves also reproduced the training and validation labels perfectly using the same eight inputs, after overlap and duplicate removal. This suggests that the supplied labels may follow simple rules or reflect data-generation patterns. It does **not** prove that the dataset is synthetic. The provided split may come from one source and is not a verified independent university cohort. Neither the score nor the model has been validated on LPU students, and it must not be claimed as LPU placement accuracy.

## Reproduce

With pandas, scikit-learn and joblib installed:

```powershell
python train_supplied_placement.py --train <path-to-train.csv> --test <path-to-test.csv> --out <output-folder>
```

`evaluation.json` includes hashes, metrics, the confusion matrix, validation results, and software versions. `research_placement_model.joblib` is a research artifact; load joblib files only from trusted sources. No source CSV contents are copied into this report folder, and the website's current model was not changed.
