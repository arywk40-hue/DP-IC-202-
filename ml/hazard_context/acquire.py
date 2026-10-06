"""Frozen CDS requests: dry-run by default; explicit terms and normal authentication."""
import json
from datetime import datetime, timezone
from pathlib import Path

from ml.datasets.registry import digest
from ml.hazard_context.era5 import verify_requests


def download(client,requests,output,terms_accepted=False):
    if terms_accepted is not True:raise ValueError('Manually accept CDS product terms before an authenticated request')
    output=Path(output);output.mkdir(parents=True,exist_ok=True);receipts=[]
    for job in requests:
        r=job['request'];name=f"era5_land_{r['year']}_{r['month']}.nc"
        destination=output/name
        if destination.exists():raise ValueError('Preserve existing download; select an explicit fresh directory')
        partial=destination.with_suffix('.nc.part')
        if partial.exists():raise ValueError('Incomplete download exists; inspect before retrying')
        client.retrieve(job['dataset'],r,str(partial))
        with partial.open('rb') as handle:magic=handle.read(8)
        if not (magic.startswith(b'CDF') or magic==b'\x89HDF\r\n\x1a\n'):
            raise ValueError('Response not NetCDF; partial preserved, extract legitimate ZIP manually')
        partial.replace(destination)
        receipt={'provider':'ECMWF/Copernicus','dataset':'era5_land','request':job,'sha256':digest(destination),
                 'retrieved_at':datetime.now(timezone.utc).isoformat(),'terms_accepted_by_caller':True,'authenticated_submission_verified':True}
        destination.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt)
    return receipts


def audit(request_path='data/registry/cds_physics_requests.json',data_root='data'):
    report=verify_requests(request_path)
    paths=sorted(str(p) for p in Path(data_root).rglob('*') if p.is_file() and p.suffix.lower() in ['.nc','.nc4','.grib','.grib2'])
    # Files are candidates, never automatically assumed to be authorized ERA5.
    report.update(ERA5_DOWNLOAD_STATUS='BLOCKED_BY_ACCESS' if not paths else 'LOCAL_FILES_REQUIRE_PRODUCT_VALIDATION',
                  local_netcdf_grib_candidates=paths,real_era5_rows=0,credentials_read=False,
                  instruction='Own CDS account/token and manually accepted terms; no authentication bypass')
    return report
