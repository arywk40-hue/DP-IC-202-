"""Nullable independent-event records and conservative, evidence-based admission."""
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

TARGETS = {'extreme_rainfall', 'heavy_rainfall', 'cloudburst', 'flood', 'flash_flood',
           'landslide', 'wildfire', 'storm', 'thermal_anomaly', 'heatwave', 'cold_wave'}
STATUSES = {'candidate', 'research_only', 'admitted_for_training', 'rejected'}
FIELDS = ['event_id','reported_event_id','event_group_id','event_type','source_provider','source_dataset','source_record_id',
          'source_version','source_uri','event_start_utc','event_end_utc','latitude','longitude',
          'geometry_type','geometry','spatial_uncertainty_km','temporal_uncertainty_hours',
          'severity','measurement_value','measurement_unit','threshold_definition','country','state','district',
          'quality_flag','confidence','label_provenance','evidence_kind','provider_license','provider_rights_status',
          'retrieved_at','source_hash','reported_date','reported_location','reported_time_text',
          'cloudburst_evidence_verified','admission_status','admission_reasons']
TIMES = ['event_start_utc','event_end_utc','retrieved_at']


def utc(value):
    t = pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None or t.utcoffset().total_seconds() != 0:
        raise ValueError('Explicit UTC required; preserve unknown original clocks as text')
    return t


def finite(value, low, high):
    if isinstance(value, bool) or not math.isfinite(float(value)) or not low <= float(value) <= high:
        raise ValueError('Invalid finite numeric field')
    return float(value)


def normalize(record):
    if not isinstance(record,dict) or set(record)-set(FIELDS):
        raise ValueError('Unknown event schema fields')
    r = {k:record.get(k) for k in FIELDS}
    for key in ['source_provider','source_dataset','source_record_id']:
        if not isinstance(r[key],str) or not r[key].strip():
            raise ValueError('Provider/dataset/record ID required')
    if not isinstance(r['event_type'],str) or r['event_type'] not in TARGETS or r['country'] != 'IN':
        raise ValueError('Known independent Indian target required; China excluded')
    if r['event_id'] is None:
        ancestry = json.dumps([r[k] for k in ['source_provider','source_dataset','source_record_id']],separators=(',',':'))
        r['event_id'] = 'event_'+hashlib.sha256(ancestry.encode()).hexdigest()[:24]
    if not isinstance(r['event_id'],str) or not r['event_id'].strip():
        raise ValueError('Nonempty event ID required')
    nontext=set(TIMES)|{'geometry','latitude','longitude','spatial_uncertainty_km','temporal_uncertainty_hours','confidence','measurement_value','cloudburst_evidence_verified','admission_reasons'}
    for key in set(FIELDS)-nontext:
        if r[key] is not None and not isinstance(r[key],str):raise ValueError('Text/null event field required: '+key)
    for key in TIMES:
        if r[key] is not None:
            r[key] = utc(r[key]).isoformat()
    if r['event_start_utc'] and r['event_end_utc'] and utc(r['event_end_utc']) < utc(r['event_start_utc']):
        raise ValueError('Reversed event interval')
    for key, bounds in {'latitude':(-90,90),'longitude':(-180,180),'spatial_uncertainty_km':(0,20000),
                        'temporal_uncertainty_hours':(0,87600),'confidence':(0,1),'measurement_value':(-1e12,1e12)}.items():
        if r[key] is not None:
            r[key]=finite(r[key],*bounds)
    if (r['measurement_value'] is None) != (r['measurement_unit'] is None):
        raise ValueError('Measurement value and explicit unit travel together')
    if r['geometry'] is not None:
        if not isinstance(r['geometry'],dict):raise ValueError('GeoJSON object required')
        if len(json.dumps(r['geometry']))>100000:raise ValueError('Geometry resource budget exceeded')
        from shapely.geometry import shape
        geom = shape(r['geometry'])
        if geom.geom_type not in ['Point','Polygon','MultiPolygon'] or geom.is_empty or not geom.is_valid:
            raise ValueError('Valid point/polygon geometry required')
        bounds=geom.bounds
        if bounds[0]<-180 or bounds[2]>180 or bounds[1]<-90 or bounds[3]>90 or bounds[2]-bounds[0]>180:
            raise ValueError('Invalid/dateline-crossing geometry requires explicit handling')
        if r['geometry_type'] != geom.geom_type:
            raise ValueError('Geometry type mismatch')
        if geom.geom_type == 'Point' and r['latitude'] is not None and r['longitude'] is not None:
            if (geom.x,geom.y)!=(r['longitude'],r['latitude']):
                raise ValueError('Point geometry/coordinate conflict')
    elif r['geometry_type'] is not None:
        raise ValueError('Missing geometry; unknown is null, not a fabricated centroid')
    if r['source_hash'] is not None:
        h=r['source_hash']
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('Source SHA256 required')
    if r['cloudburst_evidence_verified'] is not None and type(r['cloudburst_evidence_verified']) is not bool:
        raise ValueError('Evidence verification must be boolean/null')
    if r['admission_status'] is not None and r['admission_status'] not in STATUSES:
        raise ValueError('Unknown admission status')
    # Never preserve an input claim of admission; recompute using reviewed source.
    r['admission_status']='candidate';r['admission_reasons']=[]
    return r


def admit(record, source, restricted=False, allow_fixture=False):
    r=normalize(record); reasons=[]
    if source.get('evidence')=='SYNTHETIC_CONTRACT_ONLY' and not allow_fixture:
        reasons.append('SYNTHETIC_NOT_INDEPENDENT')
    if r['source_dataset']!=source.get('source_dataset') or r['source_provider']!=source.get('source_provider'):
        return {**r,'admission_status':'rejected','admission_reasons':['SOURCE_IDENTITY_MISMATCH']}
    if source.get('status') not in STATUSES or source.get('status') in ['candidate','rejected']:
        reasons.append('SOURCE_NOT_ADMITTED')
    if source.get('rights_status') not in ['approved_open','approved_restricted']:
        reasons.append('RIGHTS_BLOCKED')
    elif source['rights_status']=='approved_restricted' and not restricted:
        reasons.append('RESTRICTED_VIEW_REQUIRED')
    if not source.get('rights_evidence_uri') or not source.get('reviewed_by'):
        reasons.append('RIGHTS_REVIEW_REQUIRED')
    allowed_evidence=['observed_gauge','confirmed_occurrence']+(['satellite_detection'] if r['event_type']=='thermal_anomaly' else [])
    if source.get('independent_observed') is not True or r['evidence_kind'] not in allowed_evidence:
        reasons.append('LABELS_NOT_INDEPENDENT')
    if not r.get('event_group_id') or source.get('event_identity_reviewed') is not True:
        reasons.append('PHYSICAL_EVENT_IDENTITY_UNREVIEWED')
    if r['event_type'] not in source.get('targets',[]):
        reasons.append('TARGET_NOT_APPROVED')
    if source.get('country')!='IN':
        reasons.append('COUNTRY_UNVERIFIED')
    if r['event_start_utc'] is None or r['event_end_utc'] is None:
        reasons.append('UNKNOWN_EVENT_TIME')
    if r['geometry'] is None and (r['latitude'] is None or r['longitude'] is None):
        reasons.append('UNKNOWN_EVENT_LOCATION')
    if r['spatial_uncertainty_km'] is None or r['temporal_uncertainty_hours'] is None:
        reasons.append('UNKNOWN_UNCERTAINTY')
    if r['quality_flag']!='verified' or not r['threshold_definition'] or not r['label_provenance']:
        reasons.append('DEFINITION_OR_QC_UNVERIFIED')
    if r['retrieved_at'] and r['event_end_utc'] and utc(r['retrieved_at'])<utc(r['event_end_utc']):
        reasons.append('REPORT_PRECEDES_EVENT')
    if r['latitude'] is not None and r['longitude'] is not None and not (6<=r['latitude']<=38 and 68<=r['longitude']<=99):
        reasons.append('COUNTRY_COORDINATE_CONFLICT')
    if r['source_hash'] is None or not r['source_version'] or not r['retrieved_at']:
        reasons.append('PROVENANCE_INCOMPLETE')
    if r['provider_rights_status'] != source.get('rights_status') or r['provider_license'] != source.get('provider_license'):
        reasons.append('RIGHTS_METADATA_MISMATCH')
    if r['event_type']=='cloudburst' and (r['cloudburst_evidence_verified'] is not True or
        r['evidence_kind']!='observed_gauge' or r['measurement_unit']!='mm/h' or
        r['measurement_value'] is None or r['measurement_value']<100):
        reasons.append('CLOUDBURST_LOCAL_GAUGE_EVIDENCE_REQUIRED')
    status='admitted_for_training' if not reasons and source.get('status')=='admitted_for_training' else 'research_only'
    if source.get('status')=='rejected':status='rejected'
    elif source.get('status')=='candidate':status='candidate'
    return {**r,'admission_status':status,'admission_reasons':sorted(set(reasons))}


def read_events(path, sources=None, restricted=False, quarantine=None):
    records=[]
    if Path(path).stat().st_size>50_000_000:raise ValueError('Partition event exports before normalization')
    for number,line in enumerate(Path(path).read_text().splitlines(),1):
        if not line.strip():continue
        try:
            r=normalize(json.loads(line))
            if sources is not None:r=admit(r,sources.get(r['source_dataset'],{}),restricted)
            records.append(r)
        except (ValueError,TypeError) as exc:
            if quarantine is None:raise
            quarantine.append({'line':number,'raw_record':line,'reason':str(exc)})
    return records


def schema():
    properties={k:{'type':['string','null']} for k in FIELDS}
    for k in ['latitude','longitude','spatial_uncertainty_km','temporal_uncertainty_hours','measurement_value','confidence']:
        properties[k]={'type':['number','null']}
    properties['geometry']={'type':['object','null']}
    properties['cloudburst_evidence_verified']={'type':['boolean','null']}
    properties['admission_reasons']={'type':'array','items':{'type':'string'}}
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','title':'INDRA independent Indian event v1',
            'type':'object','additionalProperties':False,'required':FIELDS,'properties':properties,
            'description':'Nullable factual fields. Runtime validator enforces UTC, geometry, finite values and recomputed admission.'}
