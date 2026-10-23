export const PARAMETERS = {
  temperature_c: ["Temperature", "°C"],
  relative_humidity_pct: ["Humidity", "%"],
  pressure_hpa: ["Pressure", "hPa"],
  pm25_ug_m3: ["PM2.5", "µg/m³"],
  pm10_ug_m3: ["PM10", "µg/m³"],
  wind_speed_mps: ["Wind", "m/s"],
};
export function parameterColor(value) {
  const stops = [
    [113, 142, 163],
    [126, 167, 145],
    [218, 198, 139],
    [180, 119, 96],
  ];
  const x = Math.max(0, Math.min(1, value)) * 3,
    i = Math.min(2, Math.floor(x)),
    t = x - i;
  return `rgb(${stops[i].map((v, j) => Math.round(v * (1 - t) + stops[i + 1][j] * t)).join(",")})`;
}
