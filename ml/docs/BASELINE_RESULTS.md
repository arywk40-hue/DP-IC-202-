# Baseline v1 Results

## Run identity

This run was generated from the repository’s raw baseline input:

```text
Input:  ml/dataset/weatherHistory.csv
Rows:   96,453
Output: ml/data_baseline/
Models: ml/model_baseline/
C file: ml/generated/model_data_baseline.h
```

The existing `ml/model/` and `ml/generated/model_data.h` artifacts were not
overwritten.

## Dataset contract

- Features: 14
- Outputs: `wildfire`, `flood`, `storm`, `air_quality`
- PM2.5, CO2, and lightning: synthetic because they are absent from the raw
  Szeged weather source
- Labels: heuristic threshold rules from `ml/prepare_dataset.py`
- Split used by the current v1 trainer: 67,516 train / 9,646 validation /
  19,291 test, using a random split

## Test results

| Hazard | Accuracy | Precision | Recall | F1 | Trees |
|---|---:|---:|---:|---:|---:|
| Wildfire | 0.999326 | 0.986639 | 1.000000 | 0.993275 | 16 |
| Flood | 0.999119 | 0.987874 | 1.000000 | 0.993900 | 16 |
| Storm | 0.999637 | 0.997480 | 1.000000 | 0.998739 | 16 |
| Air quality | 0.998134 | 1.000000 | 0.996681 | 0.998338 | 16 |

These results validate that the current Python training and C export paths
work mechanically. They do **not** establish India-wide forecast quality.

## Export verification

The generated model has:

- 4 classes;
- 14 features in the documented order;
- 16 trees per class;
- maximum observed tree size of 31 nodes;
- normalization arrays with 14 means and 14 standard deviations.

The generated header passes:

```bash
clang -fsyntax-only -x c \
  -include ml/generated/model_data_baseline.h /dev/null
```

The exporter was updated to include `<math.h>`, which is required for its
generated `expf()` probability conversion. It was also corrected to translate
XGBoost’s indexed split names (`f0`, `f1`, ...) instead of silently mapping
unknown names to feature index zero. Export now rejects models that exceed the
feature, tree, or node limits instead of truncating or remapping them.

## Limitations and next gate

The current scores are likely inflated because the target labels are derived
from the same sensor features supplied to the model. The random split also
allows nearby time periods to occur in both training and testing. The next
required experiment is therefore a rebuilt temporal baseline with:

1. chronological holdout;
2. explicit synthetic-field flags;
3. leakage checks for feature/label construction;
4. precision-recall and calibration metrics;
5. station/region-aware splits once India observations are available.

Only after that report is stable should the model be compared against a larger
India dataset.

## Temporal v2 diagnostic run

The v2 preparation and trainer were also run separately:

```text
Input:  ml/dataset/weatherHistory.csv
Features: 22
Temporal split: first 80% train, final 20% future holdout
CV: 3-fold TimeSeriesSplit
Grid: fast, 8 parameter combinations
Output: ml/model_v2_baseline/
```

| Hazard | CV F1-macro | Future-holdout F1-macro | Positive F1 |
|---|---:|---:|---:|
| Wildfire | 0.9973 | 0.9993 | 0.999 |
| Flood | 0.9983 | 0.9983 | 0.997 |
| Storm | 0.9988 | 0.9999 | 1.000 |
| Air quality | 0.9978 | 0.9975 | 0.998 |

This is a stronger temporal evaluation than v1, but it is still not a valid
India generalization test. The labels remain generated from thresholds on the
same weather/synthetic features. The v2 models are also **offline diagnostic
artifacts only**: they use 22 features and 50–100 trees, while the current C
export contract supports 14 features and 16 trees.

Attempting to export a v2 model now fails explicitly with an export-limit error;
it does not produce a misleading partial model.

The SHAP report selected 13 candidate features, but pruning is not approved for
deployment until it is re-evaluated against real event labels and the India
geographic holdout.
