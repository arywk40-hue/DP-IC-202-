import csv,collections,datetime as dt,json,math,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
files={'temperature_c':'6b64941e-8646-4020-b7e8-a8024d86fae2','relative_humidity_pct':'b9377211-44a9-4380-b99a-f40bd4bbdfde','pressure_hpa':'bbb7d941-de74-438c-a19a-bfe9e42a5fad','wind_speed_mps':'22ef7020-904b-4ef8-a975-d6baa5701988'}
ranges={'temperature_c':(-60,85),'relative_humidity_pct':(0,100),'pressure_hpa':(300,1100),'wind_speed_mps':(0,100)}
report={'method':'Exact station name, coordinates and original timestamp join. Timezone not assumed. Broad project physical ranges only; passing these is not full quality validation. Duplicate keys excluded from usable overlap. Wind divided by 3.6; mb numerically equals hPa.','files':{}}
allkeys={}; goodkeys={}; stations={}
for sensor,uid in files.items():
 p=root/'himachal 4-sensor dataset'/f'{uid}.csv'
 n=0; invalid=0; badtime=0; vals=collections.Counter(); stationstats={}; keys=set(); good=set(); dup=set(); dates=[]
 with p.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f); column=reader.fieldnames[-1]
  for r in reader:
   n+=1
   station=(r['Station'],r['Latitude'],r['Longitude'])
   s=stationstats.setdefault(station,{'station':station[0],'latitude':station[1],'longitude':station[2],'district':r['District'],'rows':0,'outside_range_or_missing':0})
   s['rows']+=1
   try:
    v=float(r[column]); v=v/3.6 if sensor=='wind_speed_mps' else v
   except ValueError:v=float('nan')
   valid=math.isfinite(v) and ranges[sensor][0]<=v<=ranges[sensor][1]
   if not valid:invalid+=1;s['outside_range_or_missing']+=1
   if math.isfinite(v):vals[v]+=1
   try:t=dt.datetime.strptime(r['Data Acquisition Time'],'%d-%m-%Y %H:%M')
   except ValueError:badtime+=1;continue
   dates.append(t)
   key=(*station,t)
   if key in keys:dup.add(key)
   keys.add(key)
   if valid:good.add(key)
 good-=dup
 allkeys[sensor]=keys;goodkeys[sensor]=good;stations[sensor]=set(stationstats)
 report['files'][sensor]={'file':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_value_column':column,'rows':n,'stations':len(stationstats),'start':str(min(dates)),'end':str(max(dates)),'outside_range_or_missing':invalid,'unparseable_times':badtime,'duplicate_station_time_keys':len(dup),'min':min(vals),'max':max(vals),'most_common_values':vals.most_common(5),'station_details':list(stationstats.values())}
 print(sensor,{k:v for k,v in report['files'][sensor].items() if k not in ('station_details','sha256','file')},flush=True)
common=set.intersection(*allkeys.values()); good=set.intersection(*goodkeys.values())
report['overlap']={'all_four_raw_keys':len(common),'all_four_broad_range_valid_unique_keys':len(good),'stations_in_all_four':len(set.intersection(*stations.values())),'valid_overlap_by_station':dict(collections.Counter(k[0] for k in good)),'exact_six_hour_pairs_broad_range_valid':sum((*k[:3],k[3]+dt.timedelta(hours=6)) in good for k in good)}
report['limitations']=['PM2.5 and PM10 absent; no complete six-input training set','Timezone and pressure reference require confirmation','Air temperature explicitly named in CSV header; encoding of degree-C unit needs metadata confirmation','Broad range filtering does not detect sensor freezing, calibration errors or spikes','No model trained or tested in this audit']
(root/'data/himachal_weather_audit/audit_report.json').write_text(json.dumps(report,indent=2))
print('OVERLAP',json.dumps(report['overlap']),flush=True)
print('MANDI',[s for s in report['files']['temperature_c']['station_details'] if 'MANDI' in s['district'].upper()],flush=True)
