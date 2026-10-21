import React, {useEffect,useState} from 'react';
import {getModelLab} from '../api/client';
import {withCache} from '../api/cache';

const TARGETS={temperature_c:['Temperature','°C'],relative_humidity_pct:['Humidity','pp'],
  pressure_hpa:['Pressure','hPa'],pm25_ug_m3:['PM2.5','µg/m³'],pm10_ug_m3:['PM10','µg/m³'],wind_speed_mps:['Wind','m/s']};

export default function ModelLab(){
  const [data,setData]=useState(null),[error,setError]=useState(null),[cached,setCached]=useState(false);
  const [cohort,setCohort]=useState('new_date_extension');
  useEffect(()=>{
    let active=true,busy=false;
    const load=async()=>{
      if(busy)return;busy=true;
      try{const r=await withCache('model-lab',getModelLab);if(active){setData(r.value);setCached(!r.isLive);setError(null);}}
      catch(e){if(active)setError(e.message);}finally{busy=false;}
    };
    load();const timer=setInterval(load,15000);
    return()=>{active=false;clearInterval(timer);};
  },[]);
  const online=data?.online;
  const metrics=data?.metrics?.[cohort];
  return <details className="model-lab">
    <summary><span className="lab-kicker">MODEL & LEARNING</span><strong>{data?.display_name||'Forecast workspace'}</strong>
      <span className="lab-summary-state">{data?.configured?`${data.data_rows.toLocaleString()} modeled hours · ${online?.enabled?'Shadow learner enabled':'Online learner not configured'}`:'Loading model evidence'}</span>
    </summary>
    {error&&<p role="alert">Model evidence unavailable: {error}</p>}
    {cached&&<p className="lab-warning">Cached model/learning snapshot. This is not a live learning status.</p>}
    {!data?.configured&&!error&&<p>Detailed comparison is available for the v2 gateway profile.</p>}
    {data?.configured&&<div className="lab-content">
      <div className="lab-stats">
        <article><span>Training history</span><strong>{data.rows_by_role.train.toLocaleString()} rows</strong><small>{data.source_start.slice(0,10)} → {data.source_end.slice(0,10)}</small></article>
        <article><span>Input contract</span><strong>6 channels · {data.features} features</strong><small>24 hours of causal history · +6h endpoint</small></article>
        <article><span>Selection</span><strong>Chronological validation</strong><small>{data.rows_by_role.validation} rows · no test-driven weight fitting</small></article>
      </div>
      <div className="lab-section-title"><div><h3>Does the new model improve the baseline?</h3><p>MAE in each channel’s unit; lower is better. Improvements are mixed across targets.</p></div>
        <label>Comparison period<select value={cohort} onChange={e=>setCohort(e.target.value)}>
          <option value="new_date_extension">New dates · 11–19 Oct 2026</option><option value="future_test">Full reused test + extension</option><option value="validation">August selection period</option>
        </select></label>
      </div>
      <div className="lab-table-wrap"><table aria-label="Forecast model comparison"><thead><tr><th>Channel</th><th>Retained v1 MAE</th><th>Selected v2 MAE</th><th>Change</th></tr></thead><tbody>
        {Object.entries(TARGETS).map(([key,[label,unit]])=>{
          const old=metrics?.legacy_hybrid?.[key]?.mae,current=metrics?.selected_v2?.[key]?.mae;
          const delta=Number.isFinite(old)&&Number.isFinite(current)?current-old:null;
          return <tr key={key}><th scope="row">{label} <small>{unit}</small></th><td>{old?.toFixed(3)??'Unavailable'}</td><td>{current?.toFixed(3)??'Unavailable'}</td><td className={delta==null?'':delta<=0?'lab-better':'lab-worse'}>{delta==null?'Unavailable':`${delta>0?'+':''}${delta.toFixed(3)} ${delta<=0?'↓':'↑'}`}</td></tr>;
        })}
      </tbody></table></div>
      <p className="lab-note">Retrospective ECMWF/CAMS grids at Mandi, not station accuracy or disaster probabilities. The earlier test period has been examined before. Models and weights stay versioned; v1 remains available for rollback.</p>
      <div className="lab-online"><div><span className="lab-kicker">DELAYED-LABEL ONLINE LEARNING</span><h3>{online?.enabled?'Shadow residual learner':'Worker not configured'}</h3>
        <p>{online?.enabled?online.status?.replaceAll('_',' '):'Start the backend/importer with an online-state path to record actual hourly arrivals.'}</p>
        <p>Predict and save first. Learn only after the matching +6h observation arrives. Scalers stay frozen. Shadow predictions never replace the displayed offline forecast.</p>
      </div><div className="lab-online-stats"><span><strong>{online?.updates??0}</strong> matured updates</span><span><strong>{online?.pending??0}</strong> waiting for truth</span><span><strong>{online?.historical_ineligible_forecasts??0}</strong> historical inputs excluded</span></div></div>
      {online?.drift_warning&&<p className="lab-warning">Shadow errors have worsened relative to the frozen baseline. Review drift diagnostics before any promotion.</p>}
      <details><summary>Candidate and research details</summary><p>Compared: expanded-data LightGBM, residual MLP, retained hybrid and persistence. TabPFN: {typeof data.tabpfn_status==='string'?data.tabpfn_status:data.tabpfn_status?.status}.</p>
        {data.online_replay&&<p>Separate research replay: {data.online_replay.updates.toLocaleString()} matured shadow updates; {data.online_replay.pending} forecasts awaiting truth. This assumes timely historical arrivals and is not the live worker count above.</p>}
        <p>The separate prequential replay simulates timely arrivals. It is not a live learning or field-accuracy receipt.</p></details>
    </div>}
  </details>;
}
