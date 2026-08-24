#include <math.h>
#include <unity.h>
#include "IndraCore.h"
namespace {
indra::Reading valid(float value, uint32_t at = 1000) { return {value, indra::SensorStatus::Valid, at}; }
indra::SensorSnapshot nominal(uint32_t at = 1000, float pressure = 1008.0f) { indra::SensorSnapshot s{}; s.temperature_c=valid(30,at); s.relative_humidity_pct=valid(65,at); s.pressure_hpa=valid(pressure,at); s.wind_speed_mps=valid(4,at); s.pm25_ug_m3=valid(25,at); s.latitude_deg=valid(22.5726f,at); s.longitude_deg=valid(88.3639f,at); s.time={2026,236,12,indra::SensorStatus::Valid}; return s; }
void test_first_sample_requires_pressure_history() { indra::FeatureBuilder b; indra::FeatureVector v{}; indra::ModelResult r{}; TEST_ASSERT_FALSE(b.build(nominal(), &v, &r)); TEST_ASSERT_EQUAL_STRING("pressure_trend_hpa_per_hour", r.missing_feature); }
void test_exact_order_and_not_ready() { indra::FeatureBuilder b; indra::FeatureVector v{}; indra::ModelResult r{}; TEST_ASSERT_FALSE(b.build(nominal(),&v,&r)); TEST_ASSERT_TRUE(b.build(nominal(3601000,1009),&v,&r)); TEST_ASSERT_EQUAL_FLOAT(30,v.values[0]); TEST_ASSERT_EQUAL_FLOAT(65,v.values[1]); TEST_ASSERT_EQUAL_FLOAT(1009,v.values[2]); TEST_ASSERT_EQUAL_FLOAT(4,v.values[3]); TEST_ASSERT_EQUAL_FLOAT(25,v.values[4]); TEST_ASSERT_FLOAT_WITHIN(.001f,1,v.values[5]); TEST_ASSERT_FLOAT_WITHIN(.001f,-1,v.values[9]); TEST_ASSERT_EQUAL_FLOAT(22.5726f,v.values[12]); TEST_ASSERT_EQUAL_FLOAT(88.3639f,v.values[13]); TEST_ASSERT_EQUAL_STRING("NOT_READY",indra::model_status_name(r.status)); }
void test_missing_input_rejected() { indra::FeatureBuilder b; indra::FeatureVector v{}; indra::ModelResult r{}; auto s=nominal(); s.pm25_ug_m3.status=indra::SensorStatus::Stale; TEST_ASSERT_FALSE(b.build(s,&v,&r)); TEST_ASSERT_EQUAL_STRING("pm25_ug_m3",r.missing_feature); }
void test_default_snapshot_never_implies_a_valid_reading() { indra::SensorSnapshot snapshot{}; TEST_ASSERT_EQUAL(indra::SensorStatus::Missing, snapshot.temperature_c.status); TEST_ASSERT_TRUE(isnan(snapshot.temperature_c.value)); TEST_ASSERT_EQUAL(indra::SensorStatus::Missing, snapshot.time.status); }
void run_tests() { UNITY_BEGIN(); RUN_TEST(test_first_sample_requires_pressure_history); RUN_TEST(test_exact_order_and_not_ready); RUN_TEST(test_missing_input_rejected); RUN_TEST(test_default_snapshot_never_implies_a_valid_reading); UNITY_END(); }
}
#ifdef ARDUINO
#include <Arduino.h>
void setup() { delay(2000); run_tests(); } void loop() {}
#else
int main() { run_tests(); return 0; }
#endif
