# Real-world graduate survey: research experiment

This is an offline research benchmark. It is **not connected to the placement dashboard**, and must not be presented as an LPU readiness or placement model.

## Dataset and provenance

The [Nigerian Graduate Report 2018 by Stutern](https://www.kaggle.com/datasets/stutern/nigerian-gradaute-report-2018) is a survey of 5,219 graduates of Nigerian institutions who graduated in 2013–2017. The dataset creator describes the 2018 survey and lists the license as CC BY-SA 4.0. This experiment uses a [third-party cleaned copy](https://github.com/EJmpa/Stat-Solver/blob/main/Data_Cleaning/Nigerian_Graduates_Destination_Survey.csv), so its exact transformations relative to the original were not independently verified. SHA-256: `00ea98c30b27bdc89fc9b6763e83205a680739f5ccba38882db4ec282c51f501`.

The downloaded CSV contains 5,219 rows. After conservatively removing 175 identical responses (excluding timestamp and row number), 5,044 responses remained. Identical responses might represent different people, so the deduplication assumption is a limitation. Of those, 3,382 reported at least one job since graduation and 1,662 reported none. The 80/20 stratified split used 4,035 training rows and 1,009 unseen test rows.

## Outcome and predictors

The target is **whether a respondent reported at least one job since graduation**, not current employment, placement readiness, or campus placement. The cleaned copy's `Employed` field was checked against the number of jobs reported. Job count and all other post-graduation outcome details were excluded from the predictors. The only predictors used were course of study and graduation year, which were available by graduation. Graduation year also reflects how long a respondent had to find work, so this is not a fixed-horizon prediction.

These predictors do not match the nine inputs of the existing LPU model. This dataset also lacks its coding, technical, and aptitude assessment scores. Automatically substituting this model would produce misleading results.

## Holdout results

| Model | Accuracy | Balanced accuracy | ROC AUC |
| --- | ---: | ---: | ---: |
| Majority-class baseline | 67.1% | 50.0% | 0.500 |
| Logistic regression | 68.7% | 56.1% | 0.633 |
| Random forest | 67.0% | 50.5% | 0.612 |

The logistic model's approximate 95% Wilson interval for holdout accuracy is 65.8%–71.5%. Among 332 respondents with no reported jobs, it correctly identified only 64, missing 268. Its limited improvement over the simple baseline and the small number of usable predictors make it unsuitable for decisions about individual students.

The test uses a random split within one 2018 survey; it is **not** an external, later-year, or LPU validation. The respondents are self-selected Nigerian graduates, not a representative sample of LPU students. Results from one population cannot establish performance in another.

## Reproduce

Install compatible versions of pandas, scikit-learn, and joblib, then obtain the cleaned source CSV at the mirror URL above. Run:

```powershell
python train_real_graduate_survey.py --data <path-to-survey.csv> --out <output-directory>
```

`evaluation.json` contains the detailed metrics and software versions. The saved logistic-regression artifact is for research only; the running app's model was not changed. Only load joblib files from trusted sources.
