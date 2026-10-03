import importlib.metadata as m
import json
import urllib.request
from pathlib import Path
packages=['numpy','pandas','scikit-learn','xgboost','scipy','joblib','threadpoolctl','python-dateutil','six']
queries=[{'package':{'name':p,'ecosystem':'PyPI'},'version':m.version(p)} for p in packages]
queries += [{'package':{'name':line.split('==')[0],'ecosystem':'PyPI'},'version':line.split('==')[1]} for line in Path('requirements.txt').read_text().splitlines() if '==' in line]
request=urllib.request.Request('https://api.osv.dev/v1/querybatch',data=json.dumps({'queries':queries}).encode(),headers={'Content-Type':'application/json'})
try:
 with urllib.request.urlopen(request,timeout=30) as response: results=json.load(response)['results']
 report={'scope':'Installed ML runtime dependencies plus requirements pins; OSV registry audit, not source/firmware security certification','queries':[{**q,'advisories':r.get('vulns',[])} for q,r in zip(queries,results)]}
except Exception as exc:
 report={'scope':'OSV query attempted','error':str(exc),'queries':queries}
Path('reports/review/dependency_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
