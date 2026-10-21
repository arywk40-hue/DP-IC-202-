# Synthetic-trained six-sensor weather-pattern classifier

Current-condition, multi-label LightGBM / MLP blend. **Not trained or calibrated
on independently observed weather events.** See the
[feature guide](../../../docs/PARAMETER_MAPS_AND_WEATHER_CATEGORIES.md).

Inputs: six current measurements, their six one-hour changes and six-hour
pressure change, in the profile's exact 13-feature order. Six complete hours of
native history are required. Ten ordered output scores correspond to the profile's
categories. They are synthetic pattern scores, not real event probabilities.

The shared MLP has architecture 13→64→32→10 with ReLU hidden/sigmoid output layers.
`neural.npz` stores arrays/scaler; ten `.txt` files store binary LightGBM heads.
`profile.json` checksums these artifacts and records validation-selected blend
weights/thresholds, synthetic split identities, input domain and limitations.
Missing history/out-of-domain inputs are unavailable rather than normal/safe.

16,000 independent synthetic training episodes, 4,000 validation, 4,000 test;
zero real event labels. Generation and comparison are reproducible through
`scripts/train_weather_categories.py` and `scripts/test_weather_features.py`.
The numerical +6h forecast, original Beijing event model and ESP32 exports remain
separate and unchanged. This classifier runs on the Python gateway.
