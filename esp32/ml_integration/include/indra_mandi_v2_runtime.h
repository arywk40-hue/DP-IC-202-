#pragma once
// Frozen six-channel Mandi v2 edge inference. No network, fitting or updating.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include "mandi_v2_trees.h"

namespace mandi_v2 {
enum class Status : uint8_t { Invalid, OutOfOrder, WarmingUp, Ready };
inline const char* status_name(Status s) {
  switch (s) {
    case Status::Invalid: return "INVALID_INPUT";
    case Status::OutOfOrder: return "OUT_OF_ORDER";
    case Status::WarmingUp: return "WARMING_UP_PERSISTENCE";
    case Status::Ready: return "HYBRID_READY";
  }
  return "INVALID_INPUT";
}
constexpr double kLow[6] = {-60,0,300,0,0,0};
constexpr double kHigh[6] = {85,100,1100,5000,5000,100};

inline double clip(double x, int j) {
  return x < kLow[j] ? kLow[j] : (x > kHigh[j] ? kHigh[j] : x);
}
inline double tree_sum(const Node* nodes, const uint32_t* roots, uint32_t count,
                       double base, const double* x, bool xgboost) {
  double result = base;
  for (uint32_t t=0; t<count; ++t) {
    const uint32_t offset=roots[t];
    int32_t i=0;
    for (unsigned depth=0; depth<32; ++depth) {
      const Node& n=nodes[offset+static_cast<uint32_t>(i)];
      if (n.feature < 0) { result += n.value; break; }
      const double v=x[n.feature];
      i = (xgboost ? (v < n.threshold) : (v <= n.threshold)) ? n.left : n.right;
      if (depth==31) return NAN;
    }
  }
  return result;
}

inline double mlp_residual(const double* x, const float* x_mean, const float* x_std,
    const float* y_mean, const float* y_std, const float* weights,
    const float* w0, const float* b0, const float* w1, const float* b1,
    const float* w2, const float* b2, int h1, int h2, int target) {
  double a[66], b[64], c[32], y[6];
  for (int i=0;i<66;++i) a[i]=(x[i]-x_mean[i])/x_std[i];
  for (int j=0;j<h1;++j) {
    double v=b0[j]; for (int i=0;i<66;++i) v+=a[i]*w0[i*h1+j];
    b[j]=v>0?v:0;
  }
  const double* last=b;
  int last_n=h1;
  if (h2) {
    for (int j=0;j<h2;++j) {
      double v=b1[j]; for (int i=0;i<h1;++i) v+=b[i]*w1[i*h2+j];
      c[j]=v>0?v:0;
    }
    last=c; last_n=h2;
  }
  const float* out_w=h2?w2:w1;
  const float* out_b=h2?b2:b1;
  const int out_width=6;
  double v=out_b[target];
  for (int i=0;i<last_n;++i) v+=last[i]*out_w[i*out_width+target];
  y[target]=v*y_std[target]+y_mean[target];
  return y[target]*weights[target];
}

inline void features_from_history(const double history[25][6], double* x) {
  int k=0;
  for (int s=0;s<6;++s) {
    const double current=history[24][s];
    x[k++]=static_cast<float>(current);
    const int lags[5]={1,3,6,12,24};
    for (int lag:lags) x[k++]=static_cast<float>(history[24-lag][s]);
    x[k++]=static_cast<float>(current-history[23][s]);
    const int windows[2]={6,24};
    for (int window_index=0;window_index<2;++window_index) {
      const int window=windows[window_index];
      double mean=0;
      for (int i=25-window;i<25;++i) mean+=history[i][s];
      mean/=window;
      double variance=0;
      for (int i=25-window;i<25;++i) { const double d=history[i][s]-mean; variance+=d*d; }
      variance/=window;
      x[k++]=static_cast<float>(mean);
      x[k++]=static_cast<float>(std::sqrt(variance));
    }
  }
}

inline double ridge_residual(const double* x, int target) {
  double value=ridge_intercepts[target];
  for (int i=0;i<66;++i)
    value += ((x[i]-ridge_mean[i])/ridge_std[i])*ridge_coefficients[target*66+i];
  return value;
}

inline void predict_complete(const double* x, const double* now, double* out) {
  const Node* lgb_nodes[6]={lgb_temperature_c_nodes,lgb_relative_humidity_pct_nodes,
    lgb_pressure_hpa_nodes,lgb_pm25_ug_m3_nodes,lgb_pm10_ug_m3_nodes,lgb_wind_speed_mps_nodes};
  const uint32_t* lgb_roots[6]={lgb_temperature_c_roots,lgb_relative_humidity_pct_roots,
    lgb_pressure_hpa_roots,lgb_pm25_ug_m3_roots,lgb_pm10_ug_m3_roots,lgb_wind_speed_mps_roots};
  const uint32_t lgb_counts[6]={lgb_temperature_c_root_count,lgb_relative_humidity_pct_root_count,
    lgb_pressure_hpa_root_count,lgb_pm25_ug_m3_root_count,lgb_pm10_ug_m3_root_count,lgb_wind_speed_mps_root_count};
  const double lgb_bases[6]={lgb_temperature_c_base,lgb_relative_humidity_pct_base,
    lgb_pressure_hpa_base,lgb_pm25_ug_m3_base,lgb_pm10_ug_m3_base,lgb_wind_speed_mps_base};
  const Node* xgb_nodes[6]={xgb_temperature_c_nodes,xgb_relative_humidity_pct_nodes,
    xgb_pressure_hpa_nodes,xgb_pm25_ug_m3_nodes,xgb_pm10_ug_m3_nodes,xgb_wind_speed_mps_nodes};
  const uint32_t* xgb_roots[6]={xgb_temperature_c_roots,xgb_relative_humidity_pct_roots,
    xgb_pressure_hpa_roots,xgb_pm25_ug_m3_roots,xgb_pm10_ug_m3_roots,xgb_wind_speed_mps_roots};
  const uint32_t xgb_counts[6]={xgb_temperature_c_root_count,xgb_relative_humidity_pct_root_count,
    xgb_pressure_hpa_root_count,xgb_pm25_ug_m3_root_count,xgb_pm10_ug_m3_root_count,xgb_wind_speed_mps_root_count};
  const double xgb_bases[6]={xgb_temperature_c_base,xgb_relative_humidity_pct_base,
    xgb_pressure_hpa_base,xgb_pm25_ug_m3_base,xgb_pm10_ug_m3_base,xgb_wind_speed_mps_base};
  const float* legacy_mlp_mean[2]={residual_mlp_32_x_mean,residual_mlp_64_32_x_mean};
  const float* legacy_mlp_std[2]={residual_mlp_32_x_std,residual_mlp_64_32_x_std};
  const float* legacy_y_mean[2]={residual_mlp_32_y_mean,residual_mlp_64_32_y_mean};
  const float* legacy_y_std[2]={residual_mlp_32_y_std,residual_mlp_64_32_y_std};
  const float* legacy_weights[2]={residual_mlp_32_weights,residual_mlp_64_32_weights};
  const float* legacy_w0[2]={residual_mlp_32_w0,residual_mlp_64_32_w0};
  const float* legacy_b0[2]={residual_mlp_32_b0,residual_mlp_64_32_b0};
  const float* legacy_w1[2]={residual_mlp_32_w1,residual_mlp_64_32_w1};
  const float* legacy_b1[2]={residual_mlp_32_b1,residual_mlp_64_32_b1};
  const float* legacy_w2[2]={residual_mlp_64_32_w2,residual_mlp_64_32_w2};
  const float* legacy_b2[2]={residual_mlp_64_32_b2,residual_mlp_64_32_b2};
  const int legacy_h1[2]={32,64}, legacy_h2[2]={0,32};
  for (int j=0;j<6;++j) {
    const double lgb=clip(now[j]+tree_sum(lgb_nodes[j],lgb_roots[j],lgb_counts[j],lgb_bases[j],x,false),j);
    const uint8_t selected[6]={legacy_neural_index_0,legacy_neural_index_1,
      legacy_neural_index_2,legacy_neural_index_3,legacy_neural_index_4,legacy_neural_index_5};
    const int m=selected[j];
    const double nn=clip(now[j]+mlp_residual(x,legacy_mlp_mean[m],legacy_mlp_std[m],legacy_y_mean[m],legacy_y_std[m],legacy_weights[m],legacy_w0[m],legacy_b0[m],legacy_w1[m],legacy_b1[m],legacy_w2[m],legacy_b2[m],legacy_h1[m],legacy_h2[m],j),j);
    const double teacher_weights[6]={xgb_teacher_weight_0,xgb_teacher_weight_1,xgb_teacher_weight_2,xgb_teacher_weight_3,xgb_teacher_weight_4,xgb_teacher_weight_5};
    const double xgb_value=clip(now[j]+teacher_weights[j]*tree_sum(xgb_nodes[j],xgb_roots[j],xgb_counts[j],xgb_bases[j],x,true),j);
    const double ridge=clip(now[j]+ridge_residual(x,j),j);
    const double lw_nn[6]={legacy_blend_0_0,legacy_blend_1_0,legacy_blend_2_0,legacy_blend_3_0,legacy_blend_4_0,legacy_blend_5_0};
    const double lw_xgb[6]={legacy_blend_0_1,legacy_blend_1_1,legacy_blend_2_1,legacy_blend_3_1,legacy_blend_4_1,legacy_blend_5_1};
    const double lw_ridge[6]={legacy_blend_0_2,legacy_blend_1_2,legacy_blend_2_2,legacy_blend_3_2,legacy_blend_4_2,legacy_blend_5_2};
    const double legacy_value=clip(lw_nn[j]*nn+lw_xgb[j]*xgb_value+lw_ridge[j]*ridge,j);
    const double neural=clip(now[j]+mlp_residual(x,mlp_v2_x_mean,mlp_v2_x_std,mlp_v2_y_mean,mlp_v2_y_std,mlp_v2_weights,mlp_v2_w0,mlp_v2_b0,mlp_v2_w1,mlp_v2_b1,mlp_v2_w2,mlp_v2_b2,64,32,j),j);
    const double v2_legacy[6]={v2_blend_0_0,v2_blend_1_0,v2_blend_2_0,v2_blend_3_0,v2_blend_4_0,v2_blend_5_0};
    const double v2_lgb[6]={v2_blend_0_1,v2_blend_1_1,v2_blend_2_1,v2_blend_3_1,v2_blend_4_1,v2_blend_5_1};
    const double v2_neural[6]={v2_blend_0_2,v2_blend_1_2,v2_blend_2_2,v2_blend_3_2,v2_blend_4_2,v2_blend_5_2};
    const double v2_persist[6]={v2_blend_0_3,v2_blend_1_3,v2_blend_2_3,v2_blend_3_3,v2_blend_4_3,v2_blend_5_3};
    out[j]=clip(v2_legacy[j]*legacy_value+v2_lgb[j]*lgb+v2_neural[j]*neural+v2_persist[j]*now[j],j);
  }
}

constexpr int kPatternCount=10;
constexpr const char* kPatternNames[kPatternCount]={"rain","rainstorm","snowstorm","heatwave_like","fog","frost","dust_storm","smoke","wildfire_weather","cloudburst_like"};
struct PatternResult { bool available=false, in_domain=false; double scores[10]{}; bool matched[10]{}; };
struct ScenarioResult { bool available=false; uint64_t seed=0; double fraction[3][3]{}; };
struct Result {
  Status status=Status::Invalid; uint8_t history_rows=0;
  double forecast[6]={NAN,NAN,NAN,NAN,NAN,NAN};
  PatternResult patterns{}; ScenarioResult scenarios{};
};
inline double sigmoid(double x) { return x>=0?1.0/(1.0+std::exp(-x)):std::exp(x)/(1.0+std::exp(x)); }
inline bool synthetic_domain(const double history[25][6]) {
  const double lo[6]={-25,5,550,0,1,0},hi[6]={50,100,1050,700,1500,35};
  for(int t=18;t<25;++t){for(int j=0;j<6;++j)if(history[t][j]<lo[j]||history[t][j]>hi[j])return false;if(history[t][3]>history[t][4])return false;}
  return true;
}
inline PatternResult predict_patterns(const double history[25][6]) {
  PatternResult out; if(!synthetic_domain(history))return out;const double (*h)[6]=history+18; double x[13]; int k=0;
  for(int j=0;j<6;++j)x[k++]=h[6][j];
  for(int j=0;j<6;++j)x[k++]=h[6][j]-h[5][j];
  x[k++]=h[6][2]-h[0][2];
  for(int j=0;j<13;++j)if(x[j]<pattern_feature_min[j]||x[j]>pattern_feature_max[j])return out;
  out.in_domain=true;
  const Node* trees[10]={cat_rain_nodes,cat_rainstorm_nodes,cat_snowstorm_nodes,cat_heatwave_like_nodes,cat_fog_nodes,cat_frost_nodes,cat_dust_storm_nodes,cat_smoke_nodes,cat_wildfire_weather_nodes,cat_cloudburst_like_nodes};
  const uint32_t* roots[10]={cat_rain_roots,cat_rainstorm_roots,cat_snowstorm_roots,cat_heatwave_like_roots,cat_fog_roots,cat_frost_roots,cat_dust_storm_roots,cat_smoke_roots,cat_wildfire_weather_roots,cat_cloudburst_like_roots};
  const uint32_t counts[10]={cat_rain_root_count,cat_rainstorm_root_count,cat_snowstorm_root_count,cat_heatwave_like_root_count,cat_fog_root_count,cat_frost_root_count,cat_dust_storm_root_count,cat_smoke_root_count,cat_wildfire_weather_root_count,cat_cloudburst_like_root_count};
  double v[13],a[64],b[32],neural[10];
  for(int i=0;i<13;++i)v[i]=(x[i]-pattern_mean[i])/pattern_std[i];
  for(int j=0;j<64;++j){double q=pattern_b0[j];for(int i=0;i<13;++i)q+=v[i]*pattern_w0[i*64+j];a[j]=q>0?q:0;}
  for(int j=0;j<32;++j){double q=pattern_b1[j];for(int i=0;i<64;++i)q+=a[i]*pattern_w1[i*32+j];b[j]=q>0?q:0;}
  for(int j=0;j<10;++j){double q=pattern_b2[j];for(int i=0;i<32;++i)q+=b[i]*pattern_w2[i*10+j];neural[j]=sigmoid(q);double tree=sigmoid(tree_sum(trees[j],roots[j],counts[j],0,x,false));out.scores[j]=tree*pattern_tree_weights[j]+neural[j]*(1-pattern_tree_weights[j]);out.matched[j]=out.scores[j]>=pattern_thresholds[j];}
  out.available=true;return out;
}

class ScenarioRng {
 public:
  explicit ScenarioRng(uint64_t seed):state_(seed?seed:0x9e3779b97f4a7c15ULL){}
  uint64_t next(){state_^=state_>>12;state_^=state_<<25;state_^=state_>>27;return state_*2685821657736338717ULL;}
  double uniform(){return (next()>>11)*(1.0/9007199254740992.0);}
  double normal(){double u=uniform();if(u<1e-15)u=1e-15;return std::sqrt(-2*std::log(u))*std::cos(6.2831853071795864769*uniform());}
 private:uint64_t state_;
};
inline double clamp01(double v){return v<0?0:(v>1?1:v);}
inline uint64_t scenario_seed(const double history[25][6]) {
  uint64_t h=1469598103934665603ULL;
  for(int t=18;t<25;++t)for(int j=0;j<6;++j){uint64_t bits;std::memcpy(&bits,&history[t][j],sizeof(bits));for(int b=0;b<8;++b){h^=(bits>>(8*b))&255;h*=1099511628211ULL;}}
  for(const char* p=kScenarioConfigSha256;*p;++p){h^=static_cast<uint8_t>(*p);h*=1099511628211ULL;}
  return h?h:1;
}
inline ScenarioResult simulate_scenarios(const double history[25][6]) {
  ScenarioResult out;if(!synthetic_domain(history))return out;const double (*h)[6]=history+18;
  const double t=h[6][0],rh=h[6][1],wind=h[6][5],dt=h[6][0]-h[5][0],dp6=h[6][2]-h[0][2];
  const double strength=sigmoid(kRain_intercept+kRain_humidity*(rh-70)/20+kRain_pressure_fall*std::max(-2.0,std::min(3.0,-dp6/3))+kRain_wind*std::max(0.0,std::min(3.0,wind/10))+kRain_cooling*std::max(-2.0,std::min(3.0,-dt/3)))*sigmoid((t-kRain_liquid_phase_center_c)/kRain_liquid_phase_scale_c);
  out.seed=scenario_seed(history);ScenarioRng rng(out.seed);const int draws=kScenarioDraws;int counts[3][3]{};
  const int runoff_ticks[3]={1,2,4};
  for(int n=0;n<draws;++n){
    bool active=rng.uniform()<strength;double base=std::exp(kRain_log_rate_intercept+kRain_log_rate_strength*strength+kRain_log_rate_sigma*rng.normal());double rain[12],ar=0;
    for(int i=0;i<12;++i){ar=kRain_temporal_ar*ar+std::sqrt(1-kRain_temporal_ar*kRain_temporal_ar)*rng.normal();rain[i]=active?base*std::exp(kRain_temporal_log_rate_sigma*ar):0;}
    double wet_u=rng.uniform(),capacity_u=rng.uniform(),sus_u=rng.uniform(),storage=kSoilStorage[0]+(kSoilStorage[1]-kSoilStorage[0])*rng.uniform(),dry=kDryRunoffCoefficient[0]+(kDryRunoffCoefficient[1]-kDryRunoffCoefficient[0])*rng.uniform(),area=kCatchmentArea[0]+(kCatchmentArea[1]-kCatchmentArea[0])*rng.uniform();
    int tc_index=static_cast<int>(rng.uniform()*3);double tc=kConcentrationTimes[tc_index];
    for(int f=0;f<3;++f){double rr[12],moisture[12],runoff[12],acc=0;
      for(int i=0;i<12;++i){rr[i]=std::min(rain[i]*kFamilyRainMultiplier[f],static_cast<double>(kRain_rain_rate_cap_mm_h));acc+=rr[i]*.5;moisture[i]=clamp01(kFamilyWetness[f][0]+(kFamilyWetness[f][1]-kFamilyWetness[f][0])*wet_u+acc/storage);runoff[i]=dry+(kWetRunoffCoefficient-dry)*moisture[i];}
      bool cloud=false,flood=false,slide=false;
      for(int i=0;i<11;++i)if((rr[i]+rr[i+1])*.5>=kCloudburstThreshold)cloud=true;
      for(int ti=0;ti<3;++ti){int ticks=runoff_ticks[ti];if(std::abs(tc-ticks*.5)>1e-9)continue;for(int i=0;i+ticks<=12;++i){double mean=0;for(int q=0;q<ticks;++q)mean+=rr[i+q];mean/=ticks;double peak=(1.0/3.6)*runoff[i+ticks-1]*mean*area;if(peak>=(kFamilyCapacity[f][0]+(kFamilyCapacity[f][1]-kFamilyCapacity[f][0])*capacity_u)*area)flood=true;}}
      for(int di=0;di<2;++di){int hours=kLandslideDurations[di],ticks=2*hours;double threshold=kLandslideIdCoefficient*std::pow(static_cast<double>(hours),kLandslideIdExponent);for(int i=0;i+ticks<=12;++i){double mean=0;for(int q=0;q<ticks;++q)mean+=rr[i+q];mean/=ticks;if(mean>=threshold*(kLandslideWetnessBase-kLandslideWetnessCoefficient*moisture[i+ticks-1]))slide=true;}}
      counts[f][0]+=cloud;counts[f][1]+=flood;counts[f][2]+=slide&&sus_u<kFamilySusceptibility[f];
    }
  }
  for(int f=0;f<3;++f)for(int j=0;j<3;++j)out.fraction[f][j]=static_cast<double>(counts[f][j])/draws;
  out.available=true;return out;
}

class Runtime {
 public:
  void reset() { count_=0; last_=0; }
  Result push(uint32_t timestamp, const double* raw) {
    Result r;
    if (!timestamp || !raw) return r;
    for (int j=0;j<6;++j) if (!std::isfinite(raw[j]) || raw[j]<kLow[j] || raw[j]>kHigh[j]) return r;
    if (count_ && timestamp<=last_) { r.status=Status::OutOfOrder; r.history_rows=count_; return r; }
    if (count_ && timestamp-last_!=3600) reset();
    if (count_==25) { std::memmove(rows_,rows_+1,24*sizeof(rows_[0])); count_=24; }
    std::memcpy(rows_[count_++],raw,sizeof(rows_[0])); last_=timestamp;
    r.history_rows=count_; for(int j=0;j<6;++j) r.forecast[j]=raw[j];
    r.status=Status::WarmingUp;
    if(count_==25) { double x[66]; features_from_history(rows_,x); predict_complete(x,raw,r.forecast); r.status=Status::Ready; }
    if(count_>=7){r.patterns=predict_patterns(rows_);r.scenarios=simulate_scenarios(rows_);}
    return r;
  }
 private:
  double rows_[25][6]{};
  uint32_t last_=0;
  uint8_t count_=0;
};
} // namespace mandi_v2
