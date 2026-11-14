"""LoRa mesh gateway lines -> ingest payloads that the real normaliser accepts."""
from types import SimpleNamespace

from server.scripts.lora_adapter import LoraParser
from server.sensors import normalize


def parser(nodes=None):
    return LoraParser(SimpleNamespace(node_prefix="lora-", nodes=nodes or {}))


def accepted(payloads):
    rows, _ = normalize(payloads)
    return {row["node_id"]: row for row in rows}


def test_flat_json_with_aliases_and_pascals():
    out = parser().parse('{"id":"n3","lat":31.7,"lon":76.9,"temp":24.1,"hum":55,"pres":100820,"rssi":-97}')
    row = accepted(out)["lora-n3"]
    assert row["temperature_c"] == 24.1 and row["relative_humidity_pct"] == 55
    assert abs(row["pressure_hpa"] - 1008.2) < 1e-6          # Pa converted to hPa
    assert (row["lat"], row["lon"], row["rssi_dbm"]) == (31.7, 76.9, -97)
    assert row["transport"] == "lora_mesh"


def test_key_value_line_with_log_prefix():
    out = parser().parse("[LoRa] RX id=n7 T=18.5 H=60 P=1008.2 pm25=12 lat=31.7 lon=76.9 rssi=-101 snr=7.5")
    row = accepted(out)["lora-n7"]
    assert row["pm25_ug_m3"] == 12 and row["rssi_dbm"] == -101


def test_wrapped_gateway_json_and_microdegrees():
    line = '{"gateway":"gw1","rssi":-90,"nodes":[{"node":1,"latitude":317250000,"longitude":769420000,"t":20,"rh":50}]}'
    row = accepted(parser().parse(line))["lora-1"]
    assert (row["lat"], row["lon"]) == (31.725, 76.942)
    assert row["rssi_dbm"] == -90                             # gateway link metric inherited


def test_csv_header_then_rows():
    p = parser()
    assert p.parse("id,lat,lon,temp,hum,press") == []
    row = accepted(p.parse("n9,31.725,76.942,24.1,55,1008.2"))["lora-n9"]
    assert row["temperature_c"] == 24.1 and row["lat"] == 31.725


def test_uptime_timestamp_is_ignored_and_battery_mv_converted():
    line = '{"from":"0x1A2B","data":{"temperature":9.5,"humidity":80,"wind":3.2,"batt":3900},"ts":12345}'
    out = parser().parse(line)
    assert "timestamp_utc" not in out[0]                      # uptime, not an epoch
    assert out[0]["battery_v"] == 3.9
    assert accepted(out)["lora-0x1A2B"]["timestamp_source"] == "server_receive"


def test_non_data_lines_are_ignored():
    p = parser()
    for line in ("boot ok, listening on 868MHz", "", "ERR crc", '{"hello": "world"}'):
        assert p.parse(line) == []


def test_config_fills_only_missing_location():
    nodes = {"lora-n3": {"lat": 1.0, "lon": 2.0, "elevation_m": 1500, "name": "Ridge"}}
    out = parser(nodes).parse('{"id":"n3","temp":20,"lat":31.7,"lon":76.9}')
    assert out[0]["lat"] == 31.7 and out[0]["elevation_m"] == 1500 and out[0]["name"] == "Ridge"
