"""Produce exact monthly requests, without reading credentials or downloading."""
import json
from pathlib import Path
from ml.datasets.era5_land import request

def main():
    jobs=[request(year,month,[38,68,6,98.5]) for year in [2023,2024] for month in range(1,13)]
    for job in jobs:job['request']['product_type']=['reanalysis']
    output={'authentication':'CDS account, accepted terms and API token OR manual download required. No credentials read or downloads attempted.',
        'verification':'Request variables/area/calendar checked locally. Authenticated API submission not tested; confirm current CDS Show API request code before submitting.',
        'requests':jobs}
    Path('data/registry/cds_physics_requests.json').write_text(json.dumps(output,indent=2)+'\n')
if __name__=='__main__':main()
