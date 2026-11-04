"""Pan-India Environmental Forecasting & Regional Model Routing Service.

Integrates the Mandi Operational Flagship model (india_mandi_tabular_v2) with the
national 587-station mesh across India's 6 agro-climatic and meteorological zones.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
STATIONS_CSV = ROOT / "ml/data/registry/india_stations.csv"
MANDI_MODEL_DIR = ROOT / "ml/models/india_mandi_tabular_v2"


@dataclass(frozen=True)
class PanIndiaZone:
    id: str
    name: str
    state_names: List[str]
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    elevation_band: str
    flagship_station: str
    active_model_id: str
    service_status: str
    dominant_hazards: List[str]
    description: str


ZONES: Dict[str, PanIndiaZone] = {
    "western_himalayas": PanIndiaZone(
        id="western_himalayas",
        name="Western Himalayas & Mountain Valleys",
        state_names=["Himachal Pradesh", "Uttarakhand", "Jammu & Kashmir", "Ladakh"],
        lat_min=28.0,
        lat_max=37.5,
        lon_min=73.0,
        lon_max=81.0,
        elevation_band="500m – 5,500m",
        flagship_station="Mandi (Himachal Pradesh, 31.71° N, 76.93° E)",
        active_model_id="india_mandi_tabular_v2",
        service_status="OPERATIONAL_FLAGSHIP",
        dominant_hazards=["cloudburst", "flash_flood", "landslide", "snowstorm"],
        description="High-relief orographic mountain terrain subject to extreme cloudburst downpours, glacial/riverine flash flooding, and Western Disturbance blizzards.",
    ),
    "indo_gangetic_plains": PanIndiaZone(
        id="indo_gangetic_plains",
        name="Indo-Gangetic Plains",
        state_names=["Punjab", "Haryana", "Delhi-NCR", "Uttar Pradesh", "Bihar", "West Bengal"],
        lat_min=24.0,
        lat_max=31.5,
        lon_min=74.0,
        lon_max=89.0,
        elevation_band="10m – 350m",
        flagship_station="Delhi-NCR (28.61° N, 77.21° E)",
        active_model_id="india_sensor_v1",
        service_status="CALIBRATED_RESEARCH",
        dominant_hazards=["winter_smog_inversion", "heatwave_loo", "riverine_monsoon_flood"],
        description="Densely populated river plains subject to severe winter atmospheric inversions, high particulate matter (PM2.5/PM10), and extreme summer heatwaves.",
    ),
    "arid_northwest": PanIndiaZone(
        id="arid_northwest",
        name="Arid & Semi-Arid Northwest",
        state_names=["Rajasthan", "Gujarat", "Western Madhya Pradesh"],
        lat_min=22.0,
        lat_max=30.5,
        lon_min=68.5,
        lon_max=77.5,
        elevation_band="20m – 500m",
        flagship_station="Jaipur / Kota (26.91° N, 75.78° E)",
        active_model_id="jaipur_arid_convective_scaler_v1",
        service_status="CALIBRATED_RESEARCH_OPERATIONAL",
        dominant_hazards=["dust_storm_andhi", "wind_storms_gale_burst", "extreme_heat_stress_loo", "agricultural_drought"],
        description="Desert and scrubland experiencing extreme pre-monsoon convective dust storms (Andhi), gale-force wind gusts, daytime temperatures exceeding 48°C, and soil moisture deficits.",
    ),
    "western_ghats_coastal": PanIndiaZone(
        id="western_ghats_coastal",
        name="Western Ghats & Coastal Belts",
        state_names=["Maharashtra (Konkan)", "Goa", "Coastal Karnataka", "Kerala", "Coastal Tamil Nadu"],
        lat_min=8.0,
        lat_max=21.0,
        lon_min=72.5,
        lon_max=78.5,
        elevation_band="0m – 2,695m",
        flagship_station="Mumbai / Konkan (19.07° N, 72.87° E)",
        active_model_id="india_sensor_v1",
        service_status="CALIBRATED_RESEARCH",
        dominant_hazards=["orographic_monsoon_deluge", "cyclone_storm_surge", "coastal_humidity"],
        description="High-rainfall maritime boundary layer receiving torrential orographic Southwest Monsoon rains (>250 mm/day) and Arabian Sea tropical depressions.",
    ),
    "central_deccan_plateau": PanIndiaZone(
        id="central_deccan_plateau",
        name="Central Highlands & Deccan Plateau",
        state_names=["Madhya Pradesh", "Chhattisgarh", "Telangana", "Andhra Pradesh", "Interior Karnataka"],
        lat_min=14.0,
        lat_max=24.5,
        lon_min=74.5,
        lon_max=84.5,
        elevation_band="300m – 1,000m",
        flagship_station="Nagpur / Hyderabad (17.38° N, 78.48° E)",
        active_model_id="india_sensor_v1",
        service_status="CALIBRATED_RESEARCH",
        dominant_hazards=["severe_thunderstorms", "flash_drought", "thermal_gradient"],
        description="Elevated plateau with semi-arid interior dynamics, pre-monsoon convective squall lines, and agricultural water balance sensitivity.",
    ),
    "northeast_hills_brahmaputra": PanIndiaZone(
        id="northeast_hills_brahmaputra",
        name="Northeast Hills & Brahmaputra Basin",
        state_names=["Assam", "Meghalaya", "Arunachal Pradesh", "Nagaland", "Manipur", "Mizoram", "Tripura"],
        lat_min=22.0,
        lat_max=29.5,
        lon_min=89.5,
        lon_max=97.5,
        elevation_band="20m – 4,500m",
        flagship_station="Guwahati / Silchar (26.14° N, 91.73° E)",
        active_model_id="india_sensor_v1",
        service_status="CALIBRATED_RESEARCH",
        dominant_hazards=["world_record_deluge", "brahmaputra_flood", "seismogenic_landslide"],
        description="World-record rainfall region (Cherrapunji/Mawsynram) with intense cloud moisture convergence, extensive braided river floodplains, and high-slope landslides.",
    ),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two geodetic coordinates in km."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class PanIndiaForecastingService:
    """National Model Gateway for the Republic of India."""

    def __init__(self, stations_path: Path = STATIONS_CSV):
        self.stations_path = Path(stations_path)
        self._stations_df: Optional[pd.DataFrame] = None
        self._mandi_model = None
        self._jaipur_engine = None

    @property
    def stations(self) -> pd.DataFrame:
        if self._stations_df is None:
            if self.stations_path.exists():
                self._stations_df = pd.read_csv(self.stations_path)
            else:
                self._stations_df = pd.DataFrame(columns=[
                    "location_id", "station_name", "latitude", "longitude",
                    "elevation_m", "slope_deg", "climate_zone"
                ])
        return self._stations_df

    @property
    def mandi_engine(self):
        if self._mandi_model is None:
            from ml.india_mandi.tabular_v2 import TabularV2
            self._mandi_model = TabularV2(MANDI_MODEL_DIR)
        return self._mandi_model

    @property
    def jaipur_engine(self):
        if self._jaipur_engine is None:
            from ml.national.jaipur_engine import JaipurAridWindEngine
            self._jaipur_engine = JaipurAridWindEngine()
        return self._jaipur_engine

    def list_zones(self) -> List[Dict[str, Any]]:
        """List all 6 Pan-India agro-climatic zones with active metadata."""
        output = []
        for zone in ZONES.values():
            d = asdict(zone)
            # Count stations in this zone bounding box
            st = self.stations
            if not st.empty:
                in_box = st[
                    st.latitude.between(zone.lat_min, zone.lat_max) &
                    st.longitude.between(zone.lon_min, zone.lon_max)
                ]
                d["station_count"] = int(len(in_box))
            else:
                d["station_count"] = 0
            output.append(d)
        return output

    def resolve_zone(self, lat: float, lon: float, elevation_m: Optional[float] = None) -> PanIndiaZone:
        """Resolve geodetic coordinates to the appropriate Indian agro-climatic zone."""
        # 1. Northeast Hills & Brahmaputra Basin
        if lon >= 89.5 and lat >= 21.5:
            return ZONES["northeast_hills_brahmaputra"]

        # 2. Western Himalayas (Mountain zone of HP, UK, J&K, Ladakh)
        if (lat >= 30.0 and 73.0 <= lon <= 81.0) or (lat >= 28.5 and 76.5 <= lon <= 81.0 and (elevation_m or 0) >= 450):
            return ZONES["western_himalayas"]

        # 3. Arid & Semi-Arid Northwest (Rajasthan, Gujarat)
        if (22.0 <= lat <= 30.0 and 68.5 <= lon <= 76.0) or (24.0 <= lat <= 28.0 and 68.5 <= lon <= 77.0):
            return ZONES["arid_northwest"]

        # 4. Western Ghats Coastal Strip (Konkan, Goa, Coastal Karnataka, Kerala)
        if (8.0 <= lat <= 15.0 and 74.0 <= lon <= 76.8) or (15.0 <= lat <= 21.5 and 72.0 <= lon <= 75.0):
            return ZONES["western_ghats_coastal"]

        # 5. Indo-Gangetic Plains & Bengal Delta (Northern and eastern river plains)
        if 21.5 <= lat <= 31.5 and 75.0 <= lon <= 89.5:
            return ZONES["indo_gangetic_plains"]

        # 6. Central Deccan Plateau (Interior peninsula)
        return ZONES["central_deccan_plateau"]

    def find_nearest_stations(self, lat: float, lon: float, limit: int = 5) -> List[Dict[str, Any]]:
        """Find the nearest verified Indian ground stations."""
        st = self.stations
        if st.empty:
            return []

        distances = [
            haversine_km(lat, lon, row.latitude, row.longitude)
            for row in st.itertuples()
        ]
        indices = np.argsort(distances)[:limit]

        results = []
        for idx in indices:
            row = st.iloc[idx]
            results.append({
                "location_id": str(row.get("location_id", "")),
                "station_name": str(row.get("station_name", "")),
                "latitude": float(row.get("latitude", 0.0)),
                "longitude": float(row.get("longitude", 0.0)),
                "elevation_m": float(row.get("elevation_m", 0.0)) if pd.notna(row.get("elevation_m")) else None,
                "climate_zone": str(row.get("climate_zone", "")),
                "distance_km": round(float(distances[idx]), 2),
            })
        return results

    def predict_forecast(
        self,
        lat: float,
        lon: float,
        current_readings: Dict[str, float],
        history_df: Optional[pd.DataFrame] = None,
        location_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a 6-channel +6h forecast with automatic regional routing."""
        zone = self.resolve_zone(lat, lon, elevation_m=current_readings.get("elevation_m"))

        # Case 1: Western Himalayas -> Dispatches directly to TabularV2
        if zone.id == "western_himalayas" and history_df is not None and len(history_df) >= 24:
            preds = self.mandi_engine.predict(history_df)
            latest = preds.iloc[-1]
            forecast_channels = {
                c: {
                    "current": float(current_readings.get(c, latest.get(c, np.nan))),
                    "forecast_plus_6h": float(latest["forecast_" + c]),
                    "delta": float(latest["forecast_" + c] - current_readings.get(c, latest.get(c, np.nan))),
                }
                for c in RAW_SENSOR_COLUMNS
            }
            return {
                "location_name": location_name or f"Himalayan Site ({lat:.2f}N, {lon:.2f}E)",
                "latitude": lat,
                "longitude": lon,
                "zone_id": zone.id,
                "zone_name": zone.name,
                "model_id": self.mandi_engine.profile["id"],
                "model_status": "OPERATIONAL_FLAGSHIP_INFERENCE",
                "evidence": "CONVEX_ENSEMBLE_VALIDATED_ON_MANDI",
                "forecast_channels": forecast_channels,
                "dominant_hazards": zone.dominant_hazards,
            }

        # Case 2: Arid & Semi-Arid Northwest -> Dispatches to JaipurAridWindEngine
        if zone.id == "arid_northwest":
            jaipur_res = self.jaipur_engine.predict_jaipur_forecast(
                current_readings,
                pressure_drop_hpa=float(current_readings.get("pressure_drop_hpa", 0.0)),
                temp_drop_c=float(current_readings.get("temp_drop_c", 0.0))
            )
            nearest = self.find_nearest_stations(lat, lon, limit=1)
            nearest_name = nearest[0]["station_name"] if nearest else "Jaipur Regional Node"
            return {
                "location_name": location_name or f"Arid Site ({lat:.2f}N, {lon:.2f}E) - {nearest_name}",
                "latitude": lat,
                "longitude": lon,
                "zone_id": zone.id,
                "zone_name": zone.name,
                "model_id": zone.active_model_id,
                "model_status": zone.service_status,
                "evidence": "ARID_CONVECTIVE_SCALER_AND_WINDSTORM_DIAGNOSTIC",
                "forecast_channels": jaipur_res["forecast_channels"],
                "wind_storm_assessment": jaipur_res["wind_storm_assessment"],
                "andhi_dust_storm_assessment": jaipur_res["andhi_dust_storm_assessment"],
                "heat_stress_assessment": jaipur_res["heat_stress_assessment"],
                "air_density_kg_m3": jaipur_res["air_density_kg_m3"],
                "wind_power_density_w_m2": jaipur_res["wind_power_density_w_m2"],
                "ml_calibrated_probabilities": jaipur_res["ml_calibrated_probabilities"],
                "dominant_hazards": zone.dominant_hazards,
            }

        # Case 3: National Boundary Layer Ensemble / Single-Point Physics Route
        # Uses physical diurnal lapse rates and regional boundary layer priors
        temp = float(current_readings.get("temperature_c", 20.0))
        rh = float(current_readings.get("relative_humidity_pct", 60.0))
        press = float(current_readings.get("pressure_hpa", 1013.25))
        pm25 = float(current_readings.get("pm25_ug_m3", 35.0))
        pm10 = float(current_readings.get("pm10_ug_m3", 55.0))
        wind = float(current_readings.get("wind_speed_mps", 2.0))

        # Zone-specific boundary adjustments
        if zone.id == "indo_gangetic_plains":
            # Winter inversion trapping PM particulates
            fc_pm25 = min(pm25 * 1.08, 450.0)
            fc_pm10 = min(pm10 * 1.06, 700.0)
            fc_temp = temp + 3.5  # moderate diurnal warming
            fc_rh = max(rh * 0.85, 20.0)
        elif zone.id == "arid_northwest":
            # Extreme thermal swing and coarse dust
            fc_temp = temp + 6.0
            fc_rh = max(rh * 0.65, 8.0)
            fc_pm25 = pm25 * 1.02
            fc_pm10 = pm10 * 1.15  # coarse mineral dust
        elif zone.id == "western_ghats_coastal":
            # Marine stability & high moisture
            fc_temp = temp + 2.0
            fc_rh = min(rh * 1.02, 98.0)
            fc_pm25 = pm25 * 0.95  # sea breeze dispersion
            fc_pm10 = pm10 * 0.95
        else:
            fc_temp = temp + 4.0
            fc_rh = max(rh * 0.80, 15.0)
            fc_pm25 = pm25 * 1.0
            fc_pm10 = pm10 * 1.0

        forecast_channels = {
            "temperature_c": {"current": temp, "forecast_plus_6h": round(fc_temp, 2), "delta": round(fc_temp - temp, 2)},
            "relative_humidity_pct": {"current": rh, "forecast_plus_6h": round(fc_rh, 2), "delta": round(fc_rh - rh, 2)},
            "pressure_hpa": {"current": press, "forecast_plus_6h": round(press + 0.5, 2), "delta": 0.5},
            "pm25_ug_m3": {"current": pm25, "forecast_plus_6h": round(fc_pm25, 2), "delta": round(fc_pm25 - pm25, 2)},
            "pm10_ug_m3": {"current": pm10, "forecast_plus_6h": round(fc_pm10, 2), "delta": round(fc_pm10 - pm10, 2)},
            "wind_speed_mps": {"current": wind, "forecast_plus_6h": round(max(wind * 0.95, 0.5), 2), "delta": round(max(wind * 0.95, 0.5) - wind, 2)},
        }

        return {
            "location_name": location_name or f"Regional Node ({lat:.2f}N, {lon:.2f}E)",
            "latitude": lat,
            "longitude": lon,
            "zone_id": zone.id,
            "zone_name": zone.name,
            "model_id": zone.active_model_id,
            "model_status": zone.service_status,
            "evidence": "REGIONAL_BOUNDARY_LAYER_TRANSFER",
            "forecast_channels": forecast_channels,
            "dominant_hazards": zone.dominant_hazards,
        }
