#pragma once
// Embedded C++17 runtime for Jaipur & Arid Northwest Windstorms, Dust Storms (Andhi), and Heatwaves.
// Zero dynamic memory allocations. Suitable for ESP32-S3 and constrained edge microcontrollers.

#include <cmath>
#include <cstdint>
#include <algorithm>

namespace indra_jaipur {

struct WindStormResult {
  float wind_speed_mps;
  float wind_speed_kmh;
  float estimated_gust_kmh;
  float wind_power_density_w_m2;
  uint8_t alert_code; // 0=CALM, 1=WATCH, 2=GALE, 3=SEVERE, 4=EMERGENCY
  const char* alert_level;
  const char* severity;
};

struct AndhiResult {
  float andhi_index;
  float coarse_ratio;
  uint8_t category_code; // 0=NONE, 1=MODERATE, 2=SEVERE, 3=EXTREME
  const char* status;
  const char* category;
};

struct HeatStressResult {
  float vapor_pressure_deficit_kpa;
  bool is_loo_active;
  bool is_extreme_loo;
  const char* status;
  const char* risk_level;
};

struct JaipurEdgeAssessment {
  float forecast_6h[6]; // T, RH, P, PM25, PM10, Wind
  WindStormResult wind;
  AndhiResult andhi;
  HeatStressResult heat;
};

inline float calculate_air_density(float pressure_hpa, float temp_c) {
  float p_pa = pressure_hpa * 100.0f;
  float t_k = temp_c + 273.15f;
  if (t_k <= 0.0f) return 1.225f;
  return p_pa / (287.058f * t_k);
}

inline float calculate_wind_power(float wind_mps, float air_density = 1.15f) {
  float v = std::max(0.0f, wind_mps);
  return 0.5f * air_density * v * v * v;
}

inline float calculate_vpd_kpa(float temp_c, float rh_pct) {
  float t = std::clamp(temp_c, -20.0f, 65.0f);
  float rh = std::clamp(rh_pct, 0.0f, 100.0f);
  float e_s = 0.61078f * std::exp((17.27f * t) / (t + 237.3f));
  float vpd = e_s * (1.0f - (rh / 100.0f));
  return std::max(0.0f, vpd);
}

inline WindStormResult classify_wind(float wind_mps, float pressure_hpa = 975.0f, float temp_c = 32.0f, float gust_factor = 1.4f) {
  float v = std::max(0.0f, wind_mps);
  float gust = v * gust_factor;
  float rho = calculate_air_density(pressure_hpa, temp_c);
  float power = calculate_wind_power(v, rho);

  WindStormResult res;
  res.wind_speed_mps = v;
  res.wind_speed_kmh = v * 3.6f;
  res.estimated_gust_kmh = gust * 3.6f;
  res.wind_power_density_w_m2 = power;

  if (v < 10.8f) {
    res.alert_code = 0;
    res.alert_level = "CALM_OR_MODERATE";
    res.severity = "NORMAL";
  } else if (v < 17.2f) {
    res.alert_code = 1;
    res.alert_level = "STRONG_WIND_WATCH";
    res.severity = "ADVISORY";
  } else if (v < 24.5f) {
    res.alert_code = 2;
    res.alert_level = "GALE_SQUALL_WARNING";
    res.severity = "WARNING";
  } else if (v < 28.5f) {
    res.alert_code = 3;
    res.alert_level = "SEVERE_WINDSTORM_WARNING";
    res.severity = "SEVERE";
  } else {
    res.alert_code = 4;
    res.alert_level = "EXTREME_GALE_BURST_EMERGENCY";
    res.severity = "CRITICAL";
  }
  return res;
}

inline AndhiResult evaluate_andhi(
    float wind_mps,
    float pm10,
    float pm25,
    float rh_pct,
    float pressure_drop_hpa = 0.0f,
    float temp_drop_c = 0.0f
) {
  float w = std::max(0.0f, wind_mps);
  float p10 = std::max(0.0f, pm10);
  float p25 = std::max(1.0f, pm25);
  float ratio = p10 / p25;

  float wind_score = std::clamp((w - 10.0f) / 15.0f, 0.0f, 1.0f);
  float pm10_score = std::clamp((p10 - 200.0f) / 1000.0f, 0.0f, 1.0f);
  float ratio_score = std::clamp((ratio - 2.5f) / 3.0f, 0.0f, 1.0f);
  float rh_score = std::clamp((40.0f - rh_pct) / 30.0f, 0.0f, 1.0f);
  float downdraft_score = std::clamp((std::max(0.0f, temp_drop_c) / 8.0f) + (std::max(0.0f, pressure_drop_hpa) / 5.0f), 0.0f, 1.0f);

  float composite = 0.30f * wind_score +
                    0.30f * pm10_score +
                    0.15 * ratio_score +
                    0.10f * rh_score +
                    0.15f * downdraft_score;
  composite = std::clamp(composite, 0.0f, 1.0f);

  AndhiResult res;
  res.andhi_index = composite;
  res.coarse_ratio = ratio;

  if (composite < 0.25f) {
    res.category_code = 0;
    res.status = "NORMAL_ARID_CONDITIONS";
    res.category = "NONE";
  } else if (composite < 0.55f) {
    res.category_code = 1;
    res.status = "DUST_HAZE_ELEVATED";
    res.category = "MODERATE";
  } else if (composite < 0.80f) {
    res.category_code = 2;
    res.status = "ANDHI_DUST_STORM_ACTIVE";
    res.category = "SEVERE";
  } else {
    res.category_code = 3;
    res.status = "EXTREME_ANDHI_SQUALL_EMERGENCY";
    res.category = "EXTREME";
  }
  return res;
}

inline HeatStressResult evaluate_heat(float temp_c, float rh_pct) {
  float vpd = calculate_vpd_kpa(temp_c, rh_pct);
  bool loo = (temp_c >= 43.0f && rh_pct <= 25.0f);
  bool extreme = (temp_c >= 46.0f && rh_pct <= 20.0f);

  HeatStressResult res;
  res.vapor_pressure_deficit_kpa = vpd;
  res.is_loo_active = loo;
  res.is_extreme_loo = extreme;

  if (extreme) {
    res.status = "EXTREME_LOO_HEATWAVE_EMERGENCY";
    res.risk_level = "EMERGENCY";
  } else if (loo) {
    res.status = "LOO_HEATWAVE_WARNING";
    res.risk_level = "WARNING";
  } else if (temp_c >= 40.0f) {
    res.status = "HIGH_HEAT_STRESS";
    res.risk_level = "CAUTION";
  } else {
    res.status = "NOMINAL_ARID_THERMAL";
    res.risk_level = "NORMAL";
  }
  return res;
}

inline JaipurEdgeAssessment assess_jaipur(
    const float raw[6], // T, RH, P, PM25, PM10, Wind
    float pressure_drop_hpa = 0.0f,
    float temp_drop_c = 0.0f
) {
  JaipurEdgeAssessment a;
  a.wind = classify_wind(raw[5], raw[2], raw[0]);
  a.andhi = evaluate_andhi(raw[5], raw[4], raw[3], raw[1], pressure_drop_hpa, temp_drop_c);
  a.heat = evaluate_heat(raw[0], raw[1]);

  bool is_storm = (a.andhi.andhi_index >= 0.55f) || (raw[5] >= 15.0f);
  if (is_storm) {
    a.forecast_6h[0] = a.andhi.andhi_index >= 0.55f ? raw[0] - 2.5f : raw[0] + 1.0f;
    a.forecast_6h[1] = a.andhi.andhi_index >= 0.55f ? std::min(raw[1] + 10.0f, 50.0f) : std::max(raw[1] * 0.70f, 8.0f);
    a.forecast_6h[2] = raw[2] + 1.5f;
    a.forecast_6h[3] = std::min(raw[3] * 1.10f, 500.0f);
    a.forecast_6h[4] = std::min(raw[4] * 1.35f, 2500.0f);
    a.forecast_6h[5] = std::max(raw[5] * 0.90f, 8.0f);
  } else {
    a.forecast_6h[0] = raw[0] + 6.2f;
    a.forecast_6h[1] = std::max(raw[1] * 0.62f, 7.5f);
    a.forecast_6h[2] = raw[2] - 0.8f;
    a.forecast_6h[3] = raw[3] * 1.03f;
    a.forecast_6h[4] = raw[4] * 1.12f;
    a.forecast_6h[5] = std::max(raw[5] * 1.08f, 1.0f);
  }
  return a;
}

} // namespace indra_jaipur

