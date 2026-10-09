"""Acquire public NASA landslide reports as candidates, never training labels.

Reported ArcGIS dates and approximate clocks are retained without assuming
an occurrence timezone. Missing reports do not create monitored negatives.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import ssl
import urllib.parse
import urllib.request

from ml.hazard_context.events import admit
from ml.hazard_context.output import fresh_directory, new_file

LAYER = ('https://gis.earthdata.nasa.gov/portal/rest/services/Landslides/'
         'COOLR_Reports_Points/FeatureServer/0')
SOURCE_ID = 'nasa_coolr_north_india_reports'
WHERE = ("country_code = 'IN' AND latitude >= 29 AND latitude <= 36 "
         'AND longitude >= 72 AND longitude <= 81')


def fetch(path, params):
    url = LAYER + path + '?' + urllib.parse.urlencode(params)
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    with urllib.request.urlopen(url, context=context, timeout=45) as response:
        raw = response.read(50_000_001)
    if len(raw) > 50_000_000:
        raise ValueError('Public response exceeds resource budget')
    result = json.loads(raw)
    if 'error' in result:
        raise ValueError('NASA query error: ' + json.dumps(result['error']))
    return result, raw, url


def source_descriptor(retrieved, digest):
    return dict(source_provider='NASA COOLR', source_dataset=SOURCE_ID,
                source_uri=LAYER, country='IN', targets=['landslide'],
                status='candidate', independent_observed=False,
                event_identity_reviewed=False, rights_status='unresolved',
                provider_license=None, rights_evidence_uri=None, reviewed_by=None,
                version='live FeatureServer snapshot', retrieved_at=retrieved,
                source_hash=digest, used_for_training=False,
                used_for_validation=False, used_for_labels=False,
                reason='Reported events require original-source, clock, identity, '
                       'uncertainty and rights review; no monitored negatives')


def coordinates(attributes):
    lat, lon = attributes.get('latitude'), attributes.get('longitude')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) for v in [lat, lon]):
        raise ValueError('Explicit finite source coordinates required')
    if attributes.get('country_code') != 'IN' or not (29 <= lat <= 36 and 72 <= lon <= 81):
        raise ValueError('Record outside declared Indian bounding-box selection')
    return lat, lon


def serialized_date(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Unexpected ArcGIS date encoding')
    stamp = datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    return f'ArcGIS event_date={value}; UTC serialization={stamp}; occurrence clock unverified'


def candidate(attributes, source):
    lat, lon = coordinates(attributes)
    object_id = attributes.get('objectid')
    if isinstance(object_id, bool) or not isinstance(object_id, int):
        raise ValueError('Stable source object ID required')
    record = dict(source_provider=source['source_provider'], source_dataset=SOURCE_ID,
                  source_record_id=str(object_id), reported_event_id=str(attributes['event_id'])
                  if attributes.get('event_id') is not None else None,
                  event_type='landslide', country='IN', latitude=lat, longitude=lon,
                  state=attributes.get('admin_division_name'),
                  source_uri=LAYER + '/query?' + urllib.parse.urlencode(
                      dict(objectIds=object_id, outFields='*', f='json')),
                  source_version=source['version'], source_hash=source['source_hash'],
                  retrieved_at=source['retrieved_at'],
                  provider_license=source['provider_license'],
                  provider_rights_status=source['rights_status'],
                  reported_date=serialized_date(attributes.get('event_date')),
                  reported_time_text=attributes.get('event_time'),
                  reported_location=attributes.get('location_description'),
                  quality_flag='unreviewed', evidence_kind='reported_occurrence',
                  label_provenance='NASA report candidate; original source and episode identity unreviewed',
                  threshold_definition=None)
    # No UTC onset/end, uncertainty radius, physical group or confidence is invented.
    return admit(record, source)


def distance_to_mandi(lat, lon):
    a, b = math.radians(lat), math.radians(31.71)
    h = math.sin((a-b)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(lon-76.93)/2)**2
    return 6371.0088 * 2 * math.asin(min(1., math.sqrt(h)))


def run(output, audit_output):
    if Path(audit_output).exists():
        raise ValueError('Choose a fresh audit path')
    folder = fresh_directory(output)
    retrieved = datetime.now(timezone.utc).isoformat()
    metadata, raw, metadata_url = fetch('', dict(f='json'))
    if metadata.get('objectIdField') != 'objectid':
        raise ValueError('NASA source schema changed')
    (folder/'layer.json').write_bytes(raw)
    ids, raw, ids_url = fetch('/query', dict(where=WHERE, returnIdsOnly='true', f='json'))
    (folder/'ids.json').write_bytes(raw)
    if 'objectIds' not in ids or ids.get('objectIdFieldName') != 'objectid':
        raise ValueError('Unexpected ID query schema; do not treat it as zero events')
    requested = sorted(ids.get('objectIds') or [])
    if len(requested) != len(set(requested)) or len(requested) > 10000:
        raise ValueError('Invalid or excessive source ID inventory')
    features, receipts = [], []
    for start in range(0, len(requested), 500):
        chunk = requested[start:start+500]
        page, raw, url = fetch('/query', dict(objectIds=','.join(map(str, chunk)),
                              outFields='*', returnGeometry='false', f='json'))
        if page.get('exceededTransferLimit'):
            raise ValueError('Incomplete source page; reduce chunk size')
        path = folder/f'page_{start:05}.json'
        path.write_bytes(raw)
        features.extend(page['features'])
        receipts.append(dict(url=url, file=path.name, sha256=hashlib.sha256(raw).hexdigest()))
    attributes = [f['attributes'] for f in features]
    received = [a['objectid'] for a in attributes]
    if sorted(received) != requested:
        raise ValueError('Missing/duplicated source records; do not use partial download')
    attributes.sort(key=lambda a:a['objectid'])
    snapshot = folder/'snapshot.json'
    snapshot.write_text(json.dumps(dict(features=[dict(attributes=a) for a in attributes]),
                                  sort_keys=True, allow_nan=False)+'\n')
    digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    source = source_descriptor(retrieved, digest)
    records = [candidate(a, source) for a in attributes]
    (folder/'candidates.jsonl').write_text(''.join(json.dumps(r, allow_nan=False)+'\n' for r in records))
    (folder/'sources.json').write_text(json.dumps(dict(sources=[source]), indent=2)+'\n')
    dates = [datetime.fromtimestamp(a['event_date']/1000, timezone.utc) for a in attributes
             if a.get('event_date') is not None]
    report = dict(source=source, metadata_url=metadata_url, id_query_url=ids_url,
                  where=WHERE, spatial_selection='Indian reports within 29–36 N, 72–81 E; not an administrative boundary',
                  snapshot_sha256=digest, retrieved_at= retrieved, downloads=receipts,
                  records_requested=len(requested), records_received=len(records),
                  complete_id_snapshot=True, date_serialization_year_counts=dict(sorted(Counter(str(t.year) for t in dates).items())),
                  state_counts=dict(Counter(a.get('admin_division_name') or 'unknown' for a in attributes)),
                  location_accuracy_counts=dict(Counter(a.get('location_accuracy') or 'unknown' for a in attributes)),
                  himachal_report_count=sum(a.get('admin_division_name')=='Himachal Pradesh' for a in attributes),
                  reports_within_50km_of_mandi=sum(distance_to_mandi(*coordinates(a))<=50 for a in attributes),
                  reports_with_date_serialization_in_2023_2024=sum(t.year in [2023,2024] for t in dates),
                  verified_utc_event_intervals=0, reviewed_physical_event_groups=0,
                  synchronized_six_channel_matches=0, monitored_negative_records=0,
                  admitted_training_labels=0, model_weights_created=0,
                  raw_output=str(Path(output)), status='CANDIDATE_DISCOVERY_ONLY',
                  blockers=['Original-source confirmation, time/location uncertainty and rights review',
                            'Matched causal six-channel observations', 'Independent monitored non-event coverage'])
    (folder/'receipt.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    new_file(audit_output).write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, help='Fresh local directory; use ignored results/')
    p.add_argument('--audit-output', required=True, help='Fresh summary JSON path')
    args = p.parse_args()
    print(json.dumps(run(args.output, args.audit_output), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
