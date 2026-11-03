# 1,000-record placement experiment

This is a separate experiment based on 1,000 existing rows sampled from the user-provided placement files. No synthetic records were created and the website's existing model was not replaced. The source and whether the supplied data is real or synthetic are unverified.

The sampler uses random seed 42 and stratified selection: 800 unique input combinations from the original `train.csv` and 200 from the original `test.csv`. It excludes repeated input combinations and train/test overlaps before sampling. Both original files have placement labels; the label is **placement status**, not the readiness label of the current website. The original files do not document the outcome definition or observation period.

The training set was split into 640 fitting and 160 validation rows for model selection. The selected model was then refitted on all 800 training rows and evaluated on the separate 200-row test set. The test set has 127 Not Placed and 73 Placed records; there were no matching student IDs or identical model inputs across the sampled training and test records.

| Measure | Result |
| --- | ---: |
| Selected model | Histogram gradient boosting |
| Training records after final refit | 800 |
| Test records | 200 |
| Test accuracy | 100% (200 of 200) |
| Test balanced accuracy | 100% |
| Majority-class test baseline | 63.5% |
| Approximate 95% Wilson interval for test accuracy | 98.1%–100% |

The model correctly classified all 127 Not Placed and all 73 Placed test records. Its 100% score is **not evidence of 100% accuracy in the real world or at LPU**. On the same training/validation split a small 10-leaf decision tree achieved 99.375% validation accuracy, suggesting the labels may be governed by simple rules; this does not prove the dataset is synthetic. A dataset from the same unknown source is not an external validation cohort.

The model uses eight inputs: CGPA, internships, projects, coding skills, communication skills, aptitude test score, certifications, and backlogs. The website's existing model expects an additional independent technical score, and this dataset uses 1–10 skill values whose equivalence to dashboard percentages is not established. Therefore the model is incompatible with the current website without a separate, validated integration.

## Reproduce

With pandas, scikit-learn and joblib installed, sample the source files and then run training:

```powershell
python sample_1000_placement.py --train <original-train.csv> --test <original-test.csv> --out <sample-folder>
python train_supplied_placement.py --train <sample-folder>/train_800.csv --test <sample-folder>/test_200.csv --out <result-folder>
```

The saved `evaluation.json` contains input hashes and detailed metrics. `research_placement_model.joblib` is a research artifact; only load joblib files from trusted sources. The two original CSV files and sampled records are not copied into this report folder.
