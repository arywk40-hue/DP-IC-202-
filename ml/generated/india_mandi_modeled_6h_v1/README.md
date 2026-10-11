# India/Mandi compact numerical forecast — host C export

Exported from `ml/models/india_mandi_modeled_6h_v1/esp32_student/`, trained on
Mandi-location API model grids. `INDRA_FORECAST_COUNTRY` is `IN` and the evidence
macro is `MODELED_GRID_RETROSPECTIVE`. No Beijing weights are in this header.

Six inputs/outputs, exact +6h numerical forecasts, 16 depth-3 trees per head.
`c_export_report.json` records 4,063 valid and 18 invalid host test vectors,
the fixed tolerance, maximum errors and source/header hashes. Valid vectors
include source samples and generated split-boundary cases, not field observations.

This has not been selected by existing firmware or run on a physical board.
It does not provide hazard classifications, calibrated disaster probabilities
or measured Mandi sensor accuracy. Use the [primary benchmark commands](../../india_mandi/README.md).
