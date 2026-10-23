#!/usr/bin/env python3
"""Bounded CDS context downloads; default dry run, no model/label changes."""
from __future__ import annotations

import argparse
import calendar
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
API_URL = 'https://cds.climate.copernicus.eu/api'
DATASETS = {
    'reanalysis-era5-single-levels': [
        '2m_temperature', '2m_dewpoint_temperature', 'surface_pressure',
        '10m_u_component_of_wind', '10m_v_component_of_wind',
        'total_precipitation', 'snowfall',
    ],
}
AREA = [32.5, 76.0, 31.0, 78.0]  # North, west, south, east; Mandi/Kullu pilot.


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def make_plan():
    jobs = []
    periods = [('smoke', 2024, 7, [f'{d:02d}' for d in range(1, 4)])]
    periods += [('pilot', year, month,
                 [f'{d:02d}' for d in range(1, calendar.monthrange(year, month)[1] + 1)])
                for year in (2023, 2024) for month in (7, 8)]
    periods += [('full', year, month,
                 [f'{d:02d}' for d in range(1, calendar.monthrange(year, month)[1] + 1)])
                for year in range(2016, 2026) for month in range(1, 13)]
    for stage, year, month, days in periods:
        for dataset, variables in DATASETS.items():
            jobs.append({
                'id': f'{stage}_{dataset}_{year}_{month:02d}',
                'stage': stage, 'dataset': dataset,
                'request': {
                    'product_type': ['reanalysis'], 'variable': variables,
                    'year': str(year), 'month': f'{month:02d}', 'day': days,
                    'time': [f'{h:02d}:00' for h in range(24)], 'area': AREA,
                    'data_format': 'netcdf', 'download_format': 'unarchived',
                },
            })
    return {
        'schema_version': 'indra_copernicus_mandi_context_v1',
        'purpose': 'RETROSPECTIVE_GRID_CONTEXT_NOT_INDEPENDENT_HAZARD_TRUTH',
        'country': 'IN', 'site': {'latitude': 31.71, 'longitude': 76.93},
        'api_url': API_URL, 'jobs': jobs,
        'full_period': {'start': '2016-01-01', 'end': '2025-12-31',
                        'years': 10, 'hourly_time_slots_per_grid_cell': 87672},
        'batching': 'One calendar month per request; no reduction in total coverage',
        'learned_sensor_inputs_changed': False, 'hazard_training_allowed': False,
        'note': 'RH and wind derive from temperature/dewpoint and u/v; no PM in these requests.',
    }


def download(jobs, output, client):
    """Preserve originals/partials; existing files require receipt/hash agreement."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    receipts = []
    for job in jobs:
        destination = output / (job['id'] + '.download')
        receipt_path = output / (job['id'] + '.receipt.json')
        partial = output / (job['id'] + '.part')
        if destination.exists() or receipt_path.exists():
            if not destination.is_file() or not receipt_path.is_file():
                raise ValueError('Existing download has no complete receipt; preserve and review it')
            receipt = json.loads(receipt_path.read_text())
            if receipt['job'] != job or receipt['sha256'] != sha256(destination):
                raise ValueError('Existing request or source hash differs; preserve and review it')
            receipts.append(receipt)
            continue
        if partial.exists():
            raise ValueError('Partial download exists; preserve and review it before retrying')
        client.retrieve(job['dataset'], job['request'], str(partial))
        with partial.open('rb') as stream:
            magic = stream.read(8)
        if magic.startswith(b'CDF') or magic == b'\x89HDF\r\n\x1a\n':
            container = 'netcdf_or_hdf5_requires_variable_validation'
        elif magic.startswith(b'PK\x03\x04'):
            container = 'zip_requires_member_and_variable_validation'
        else:
            raise ValueError('Unexpected response container; original partial preserved')
        receipt = {
            'provider': 'ECMWF/Copernicus', 'country': 'IN', 'job': job,
            'source_uri': f"https://cds.climate.copernicus.eu/datasets/{job['dataset']}",
            'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
            'bytes': partial.stat().st_size, 'sha256': sha256(partial),
            'container': container, 'terms_acceptance_asserted_by_caller': True,
            'authenticated_retrieval_completed': True,
            'numeric_contents_validated': False,
            'independent_station_observations': False,
            'used_for_training': False, 'used_for_labels': False,
            'used_for_validation': False, 'issue_time_availability_verified': False,
        }
        partial.replace(destination)
        with receipt_path.open('x') as stream:
            stream.write(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
        receipts.append(receipt)
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['smoke', 'pilot', 'full'], default='full')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--accepted-terms', nargs='+', choices=list(DATASETS), default=[],
                        help='Name only datasets whose terms you already accepted manually')
    parser.add_argument('--output', type=Path, default=ROOT / 'ml/data/backgrounds/raw/copernicus_mandi_v1')
    args = parser.parse_args()
    output = args.output.resolve()
    # Keep downloads in the designated Git-ignored source folder.
    if not output.is_relative_to(ROOT / 'ml/data/backgrounds/raw'):
        parser.error('--output must be inside ml/data/backgrounds/raw/')
    plan = make_plan()
    jobs = [job for job in plan['jobs'] if job['stage'] == args.stage]
    report = {
        'stage': args.stage, 'jobs': len(jobs), 'output': str(output),
        'status': 'DRY_RUN_NO_AUTHENTICATION', 'credentials_printed': False,
        'hazard_training_allowed': False, 'requests': jobs,
    }
    code = 0
    if args.execute:
        if set(args.accepted_terms) != {job['dataset'] for job in jobs}:
            report['status'] = 'BLOCKED_MANUAL_PRODUCT_TERMS_REQUIRED'
            code = 2
        elif not (Path.home() / '.cdsapirc').is_file() and not os.environ.get('CDSAPI_KEY'):
            report['status'] = 'BLOCKED_CDS_ACCOUNT_TOKEN_NOT_CONFIGURED'
            code = 2
        else:
            try:
                import cdsapi
            except ImportError:
                report['status'] = 'BLOCKED_INSTALL_CDSAPI_IN_ISOLATED_ENVIRONMENT'
                code = 2
            else:
                try:
                    # Standard personal-token discovery. Disable client progress/log output.
                    client = cdsapi.Client(url=API_URL, quiet=True, debug=False, progress=False)
                    report['receipts'] = download(jobs, output, client)
                    report['status'] = 'DOWNLOADED_CONTEXT_REQUIRES_NUMERIC_VALIDATION'
                except Exception as exc:
                    # Provider/client errors can include token-bearing URLs; never print them.
                    report['status'] = 'DOWNLOAD_FAILED_REVIEW_LOCAL_PARTIALS'
                    report['error_type'] = type(exc).__name__
                    code = 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
