PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sources (
 source_id TEXT PRIMARY KEY, source_version TEXT NOT NULL, uri TEXT NOT NULL,
 provider TEXT NOT NULL, license_id TEXT NOT NULL,
 license_class TEXT NOT NULL CHECK (license_class IN ('open','restricted','unresolved')),
 license_evidence_uri TEXT NOT NULL, metadata_sha256 TEXT,
 timezone TEXT, timezone_verified INTEGER NOT NULL DEFAULT 0 CHECK(timezone_verified IN (0,1)),
 pressure_reference TEXT NOT NULL DEFAULT 'unknown' CHECK(pressure_reference IN ('station','sea_level','grid_surface','unknown','not_applicable')),
 pressure_verified INTEGER NOT NULL DEFAULT 0 CHECK(pressure_verified IN (0,1)),
 interval_semantics TEXT NOT NULL DEFAULT 'unknown',
 approval_evidence TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS raw_files (
 raw_sha256 TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
 path TEXT NOT NULL, bytes INTEGER NOT NULL, retrieved_at_utc TEXT
);
CREATE TABLE IF NOT EXISTS observations (
 record_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
 raw_sha256 TEXT NOT NULL REFERENCES raw_files(raw_sha256), source_row_id TEXT NOT NULL,
 station_id TEXT NOT NULL, physical_site_id TEXT NOT NULL, instrument_id TEXT,
 latitude_deg REAL CHECK(latitude_deg BETWEEN -90 AND 90),
 longitude_deg REAL CHECK(longitude_deg BETWEEN -180 AND 180),
 elevation_m REAL, elevation_datum TEXT, elevation_source_id TEXT REFERENCES sources(source_id),
 elevation_asset_sha256 TEXT, source_timestamp TEXT NOT NULL,
 interval_start_utc TEXT, interval_end_utc TEXT, available_at_utc TEXT,
 variable TEXT NOT NULL, value REAL, unit TEXT NOT NULL,
 original_value TEXT, original_unit TEXT NOT NULL,
 pressure_reference TEXT NOT NULL CHECK(pressure_reference IN ('station','sea_level','grid_surface','unknown','not_applicable')),
 measurement_height_m REAL, qc_flags TEXT NOT NULL CHECK(json_valid(qc_flags)),
 observed_or_modeled TEXT NOT NULL CHECK(observed_or_modeled IN ('observed','modeled','static')),
 source_metadata_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(source_metadata_json)),
 uncertainty REAL, status TEXT NOT NULL CHECK(status IN ('approved','quarantined')),
 CHECK(status != 'approved' OR (interval_end_utc IS NOT NULL AND available_at_utc IS NOT NULL
   AND latitude_deg IS NOT NULL AND longitude_deg IS NOT NULL AND value IS NOT NULL
   AND qc_flags = '[]')),
 UNIQUE(source_id,raw_sha256,source_row_id,variable)
);
CREATE INDEX IF NOT EXISTS obs_station_time ON observations(station_id,interval_end_utc,variable);
CREATE INDEX IF NOT EXISTS obs_source_status ON observations(source_id,status,variable);
-- Sources stay separate. Unresolved rights/time/reference cannot enter either view.
CREATE VIEW IF NOT EXISTS training_open AS
 SELECT o.* FROM observations o JOIN sources s USING(source_id)
 WHERE o.status='approved' AND o.observed_or_modeled='observed' AND s.license_class='open' AND s.timezone_verified=1 AND s.interval_semantics IN ('instant','hour_end','hour_start')
 AND (o.variable != 'pressure_hpa' OR (s.pressure_verified=1 AND s.pressure_reference='station' AND o.pressure_reference='station'));
CREATE VIEW IF NOT EXISTS training_restricted AS
 SELECT o.* FROM observations o JOIN sources s USING(source_id)
 WHERE o.status='approved' AND o.observed_or_modeled='observed' AND s.license_class='restricted' AND s.timezone_verified=1 AND s.interval_semantics IN ('instant','hour_end','hour_start')
 AND (o.variable != 'pressure_hpa' OR (s.pressure_verified=1 AND s.pressure_reference='station' AND o.pressure_reference='station'));
CREATE VIEW IF NOT EXISTS quarantine AS
 SELECT o.* FROM observations o WHERE o.record_id NOT IN
 (SELECT record_id FROM training_open UNION SELECT record_id FROM training_restricted UNION SELECT record_id FROM background_open);
CREATE TRIGGER IF NOT EXISTS observation_source_matches_raw BEFORE INSERT ON observations
 WHEN (SELECT source_id FROM raw_files WHERE raw_sha256=NEW.raw_sha256) != NEW.source_id
 BEGIN SELECT RAISE(ABORT,'Source does not match raw file'); END;

CREATE VIEW IF NOT EXISTS background_open AS
 SELECT o.* FROM observations o JOIN sources s USING(source_id)
 WHERE o.status='approved' AND o.observed_or_modeled='modeled'
 AND s.license_class='open' AND s.timezone_verified=1 AND s.interval_semantics IN ('instant','hour_end','hour_start');
