"""Compile the portable Mandi edge runtime and compare it with Python v2."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
import sys
sys.path.insert(0, str(ROOT))

from ml.india_mandi.tabular_v2 import TabularV2
from ml.himachal.weather_categories import WeatherCategories, episode_features, synthetic_episodes
from ml.six_sensor_forecast.contract import RAW_SENSOR_COLUMNS


def main():
    """Run deterministic C++/Python parity over varied complete Mandi windows."""
    csv = ROOT / "ml/data/himachal/mandi_expanded_v2/observations.csv"
    frame = pd.read_csv(csv)
    frame.timestamp_utc = pd.to_datetime(frame.timestamp_utc, utc=True)
    frame = frame.sort_values("timestamp_utc").reset_index(drop=True)
    # Deterministic, spread-out set of complete chronological 25-reading windows.
    starts = np.linspace(0, max(0, len(frame)-25), 8, dtype=int)
    samples, expected, stamps = [], [], []
    model = TabularV2()
    for start in starts:
        block = frame.iloc[start:start+25].copy()
        if len(block) != 25 or block.timestamp_utc.diff().iloc[1:].dt.total_seconds().ne(3600).any():
            continue
        rows = block[RAW_SENSOR_COLUMNS].to_numpy(float)
        observed = block[["timestamp_utc", "location_id", *RAW_SENSOR_COLUMNS]].copy()
        prediction = model.predict(observed).iloc[-1]
        samples.append(rows)
        expected.append([float(prediction["forecast_"+c]) for c in RAW_SENSOR_COLUMNS])
        stamps.append(int(block.timestamp_utc.iloc[-1].timestamp()))
    if not samples:
        raise RuntimeError("No complete hourly verification windows found")

    def cpp_values(values):
        def emit(value):
            if isinstance(value, np.ndarray):
                value = value.tolist()
            if isinstance(value, (list, tuple)):
                return "{" + ",".join(emit(item) for item in value) + "}"
            return f"{float(value):.17g}"
        return emit(values)

    episodes, _, _ = synthetic_episodes(32, 7171)
    category_model = WeatherCategories()
    category_x = episode_features(episodes)
    category_expected = category_model.scores(category_x)
    category_rows = []
    category_stamps = []
    for n, episode in enumerate(episodes):
        pad = np.repeat(episode[:1], 18, axis=0)
        category_rows.append(np.vstack([pad, episode]))
        category_stamps.append(1767225600 + n * 30 * 3600)

    source = f'''#include <cstdio>
#include "indra_mandi_v2_runtime.h"
#include "mandi_v2_selftest.h"
static const double samples[{len(samples)}][25][6] = {cpp_values([row.reshape(-1,6) for row in samples])};
static const double expected[{len(expected)}][6] = {cpp_values(expected)};
static const unsigned stamps[{len(stamps)}] = {{{','.join(map(str,stamps))}}};
static const double category_rows[{len(category_rows)}][25][6] = {cpp_values(category_rows)};
static const double category_expected[{len(category_expected)}][10] = {cpp_values(category_expected)};
static const unsigned category_stamps[{len(category_stamps)}] = {{{','.join(map(str,category_stamps))}}};
int main() {{
  double max_error=0, max_pattern_error=0;
  mandi_v2::Runtime smoke; mandi_v2::Result smoke_result;
  for(int i=0;i<25;++i)smoke_result=smoke.push(1767225600u+i*3600u,mandi_v2::kSelfTestRows[i]);
  if(smoke_result.status!=mandi_v2::Status::Ready || !smoke_result.patterns.available || !smoke_result.scenarios.available)return 8;
  for(int j=0;j<6;++j)if(std::abs(smoke_result.forecast[j]-mandi_v2::kSelfTestExpected[j])>.03)return 9;
  for(int j=0;j<10;++j)if(std::abs(smoke_result.patterns.scores[j]-mandi_v2::kSelfTestPatternExpected[j])>.002)return 10;
  for (int n=0;n<{len(samples)};++n) {{
    mandi_v2::Runtime runtime; mandi_v2::Result result;
    for(int i=0;i<25;++i) result=runtime.push(stamps[n]-24*3600+i*3600,samples[n][i]);
    if(result.status!=mandi_v2::Status::Ready) return 2;
    for(int j=0;j<6;++j) {{
      double e=std::abs(result.forecast[j]-expected[n][j]); if(e>max_error) max_error=e;
      if(e>0.03) {{ std::fprintf(stderr,"case=%d channel=%d got=%.9f expected=%.9f err=%.9f\\n",n,j,result.forecast[j],expected[n][j],e); return 3; }}
    }}
  }}
  for(int n=0;n<{len(category_rows)};++n) {{
    auto pattern=mandi_v2::predict_patterns(category_rows[n]);
    if(!pattern.available) return 4;
    for(int j=0;j<10;++j) {{ double e=std::abs(pattern.scores[j]-category_expected[n][j]); if(e>max_pattern_error)max_pattern_error=e; if(e>0.002){{std::fprintf(stderr,"pattern case=%d category=%d error=%.9f\\n",n,j,e);return 5;}} }}
    if(n<4){{auto scenario=mandi_v2::simulate_scenarios(category_rows[n]);auto repeat=mandi_v2::simulate_scenarios(category_rows[n]);if(!scenario.available||scenario.seed!=repeat.seed)return 6;for(int f=0;f<3;++f)for(int j=0;j<3;++j){{double q=scenario.fraction[f][j];if(q<0||q>1||q!=repeat.fraction[f][j])return 7;}}}}
  }}
  std::printf("{{\\\"self_test_fixture\\\":\\\"PASS\\\",\\\"forecast_cases\\\":%d,\\\"forecast_max_abs_error\\\":%.12g,\\\"pattern_cases\\\":%d,\\\"pattern_max_abs_error\\\":%.12g,\\\"scenario_repeatability_cases\\\":4}}\\n",{len(samples)},max_error,{len(category_rows)},max_pattern_error);
  return 0;
}}
'''
    with tempfile.TemporaryDirectory(prefix="indra-mandi-edge-") as temp:
        temp = Path(temp)
        cpp, binary = temp / "parity.cpp", temp / "parity"
        cpp.write_text(source)
        subprocess.run([
            "c++", "-std=c++17", "-O2",
            f"-I{ROOT/'esp32/ml_integration/generated/mandi_v2'}",
            f"-I{ROOT/'esp32/ml_integration/include'}", str(cpp), "-o", str(binary),
        ], check=True)
        result = subprocess.run([str(binary)], check=True, text=True, capture_output=True)
        print(result.stdout.strip())
        report = json.loads(result.stdout)
        if report["forecast_max_abs_error"] > 0.03 or report["pattern_max_abs_error"] > 0.002:
            raise RuntimeError("C++ model parity tolerance exceeded")


if __name__ == "__main__":
    main()
