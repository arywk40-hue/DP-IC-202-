# Shared numerical forecast engine

This code constructs exact +6h numeric targets and fits per-channel residual
tree teachers/compact students. It is shared by country/source profiles and
does not turn numeric outputs into disaster warnings.

Use [the India/Mandi workflow](../india_mandi/README.md) for the primary current
experiment. Its profile uses six modeled values and 66 causal history features,
with explicit temporal-only validation and complete-history cohorts. Source
data/model country and evidence kind are recorded beside the weights.

The generic CLIs retain legacy Beijing default paths for reproducibility.
Specify `--model ml/models/india_mandi_modeled_6h_v1` for direct India/Mandi
inference/export; never infer country from a shared implementation filename.
`--temporal-only` does not fabricate independent geographic validation.
