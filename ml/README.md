# ML Workspace

`ml/` contains offline data preparation, training, evaluation, distillation,
and edge export. It must not contain ESP board-specific code.

## Stable Entry Points

| Task | Entry point |
|---|---|
| Baseline dataset | `prepare_dataset.py` |
| Baseline training | `train_model.py` |
| V2 experiments | `prepare_dataset_v2.py`, `train_model_v2.py` |
| India workflows | `real_india_data/` |
| C export | `convert_to_c.py` |
| Pipeline documentation | `docs/` |

## Artifact Policy

- `model/` is the original baseline model.
- `model_*` directories are named experiment outputs retained for
  reproducibility.
- `generated/` contains C headers produced by the exporter.
- Local `data_*` directories are ignored because they are large and
  reproducible from documented sources.
- The current firmware release consumes
  `generated/model_data_india_26_masked_distilled_edge.h`.

Do not change the promoted firmware header silently. Regenerate it, run Python
versus C parity, run the host firmware tests, and build the ESP32-S3 target.

