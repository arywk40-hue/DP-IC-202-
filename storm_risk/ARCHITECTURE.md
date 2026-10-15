# ERA5 context ensemble architecture

```mermaid
flowchart TD
  A[Local ERA5 NetCDF files] --> B[Variable and unit checks · UTC grid]
  B --> C[Current values and causal 24-hour features]
  E[Confirmed event records and monitored negative coverage] --> D[Audited label matching and date splits]
  C --> D
  D --> T[Train-only scaler and chronological inner validation]
  T --> R[Ridge ranking model]
  T --> X[XGBoost classifier]
  T --> M[Fixed-epoch MLP]
  R --> W[Calib-only simplex weights]
  X --> W
  M --> W
  W --> K[Optional calib-only mapping]
  K --> G[Frozen test diagnostics and day-bootstrap gate]
  G --> O[Named scores · report · model bundle]
  C --> AN[Train-month percentile anomalies]
  C --> H[Original-grid feature NPZ and PNG exports]
  O --> N[Trailing-window neighbouring-grid confirmation]
  AN --> U[Read-only research API and React panel]
  H --> U
  N --> U
  O --> U
  D --> SGD[Optional daily SGD replay · fixed warm-up scaler]
  SGD --> Q[Separate online scores, diagnostics and checkpoints]
```

The current model input has 588 ordered features from 17 weather variables and
four derived values. The MLP defaults to 588 inputs → 64 ReLU units → one binary
ranking output. The ridge and boosted heads use the same feature order. Their
bounded outputs are combined with nonnegative coefficients summing to one;
coefficients are fitted on `calib`, never on `test`.

Anomalies and neighbouring-grid confirmation are separate outputs. Neither is
added to an event score. Grid agreement is not the physical-node authenticated
consensus implemented in the separate Himachal network phase.

The optional online learner predicts and saves each day before updating on
mature known labels. Its scaler and initial class weights are fixed; test-period
updates are disabled. It does not modify the three batch heads or their gate.

This architecture runs on the host/gateway. The six-channel ESP model, serial
transport and live sensor dashboard remain a distinct system. Real ERA5/event
data and independent held-out evidence are required before empirical promotion.
