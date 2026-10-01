# Jahangirpuri source verification: pressure and time

Checked 1 October 2026 against the locally held original Jahangirpuri DPCC 2024–2025 CSV (`raw/jahangirpuri_dpcc_2024_2025.csv`). The raw file is excluded from Git; its SHA-256 and origin are in `audit_report.json`. No pressure conversion, hourly aggregation, model evaluation, or training was done in this step.

## Pressure

- The source CSV and [OpenCity resource](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports/resource/734c459f-3e47-44c7-b0b8-8270090cecf0) label the field `BP (mmHg)`. The [CPCB CAAQM transmission protocol](https://www.airquality.cpcb.gov.in/ccr_docs/Protocol_CAAQM.pdf) also specifies mmHg for barometric pressure.
- In this particular export, 66,866 BP entries are numeric. Minimum: 712; 1st percentile: 971; median: 976; 99th percentile: 995; maximum: 1000. Of these, 66,819 (99.93%) exceed 850; only 23 are between 650 and 800.
- Treating the median literally as 976 mmHg yields about 1301 hPa, inconsistent with ordinary atmospheric pressure. Treating it as 976 hPa looks plausible but contradicts both the CSV header and CPCB protocol. These comparisons flag a likely unit or export problem; they **do not establish** the actual unit. The field also does not state whether it is station pressure or sea-level-adjusted pressure. The six-input forecast requires **station pressure in hPa**.
- **Decision:** quarantine this BP field for ML use until DPCC/CPCB or the publisher confirms the stored unit, pressure reference (station versus sea level), and whether a known export conversion or labelling error occurred. Do not silently divide, multiply, or relabel it.

## Timestamps

- The CSV uses offset-free strings such as `2024-01-01T00:00:00`. The 70,176 valid timestamped rows span 1 January 2024 through 31 December 2025 at 15-minute grid positions; one malformed separator row is excluded. The [OpenCity resource](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports/resource/734c459f-3e47-44c7-b0b8-8270090cecf0) does not identify the records' timezone. Its webpage's UTC *metadata update times* do not specify the CSV timestamp timezone.
- As an internal cross-check, the same CSV's `SR (W/mt2)` solar-radiation column has its highest mean in timestamp hour 12 (337.4 W/m²), with near-night baseline around 6–7 W/m² in hours 0–5 and 20–23. That pattern strongly suggests the CSV clock is local India time rather than UTC, but it is **not proof** of the source's timestamp convention. Other derivative CPCB datasets have described timestamps differently and cannot establish the convention for this exact export.
- The CPCB protocol describes 15-minute averages and regular transmission intervals. It does not resolve whether this export's timestamp denotes the beginning, end, or midpoint of each averaging window.
- **Decision:** preserve timestamps as naive source strings. Do not assign UTC or IST, shift time, or construct six-hour targets until the publisher confirms the timezone and interval timestamp convention.

## Exact source questions before the next preparation step

1. For `site_1423`, Jahangirpuri DPCC, 2024–2025: what unit do the **stored numeric values** in `BP (mmHg)` actually use?
2. Are those values measured at station elevation or corrected to sea level? Was any conversion applied during export?
3. Are `Timestamp` values UTC or IST, and do they label the start, end, or midpoint of each 15-minute average?

The source-page and protocol labels are documented facts. The unit mismatch and solar-time interpretation above are inferences from the local CSV. Neither resolves the three source questions.
