# Evaluation entry points

| Script | Role | Data/model scope |
| --- | --- | --- |
| `test_india_mandi.py` | **Primary India/Mandi numerical benchmark** | Six modeled Mandi channels, newly Mandi-trained weights, existing Indian research profiles; no China models |
| `test_models.py` | Historical comprehensive audit | Archived feature contracts and foreign/Indian comparisons; retained to reproduce the earlier report |
| `download_copernicus_mandi.py` | Ten-year archive acquisition | ERA5 2016–2025 monthly requests; dry run by default, no model or hazard-label changes |

Use the primary script for current project results. The historical script is not
an independent Himalayan hazard evaluator. Raw downloads, recovered Git files
and local working outputs remain ignored. Neither script invents event truth.

Copernicus account setup, portal selections and request-size batching:
[download guide](../docs/reference/COPERNICUS_MANDI_DOWNLOAD.md).
