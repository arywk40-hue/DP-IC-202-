"""Download contracts only; synthetic bytes do not establish real CDS access."""
import copy
import calendar
import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from scripts import download_copernicus_mandi as cli
from scripts.download_copernicus_mandi import download, make_plan


class Client:
    def __init__(self, payload=b'CDF\x01synthetic-test-container'):
        self.calls = 0
        self.payload = payload

    def retrieve(self, dataset, request, path):
        self.calls += 1
        Path(path).write_bytes(self.payload)


class DownloadTests(unittest.TestCase):
    def test_plan_coverage_and_scope(self):
        plan = make_plan()
        self.assertFalse(plan['hazard_training_allowed'])
        self.assertEqual(len(plan['jobs']), 125)
        self.assertEqual(len([j for j in plan['jobs'] if j['stage'] == 'smoke']), 1)
        self.assertEqual(len({j['id'] for j in plan['jobs']}), 125)
        full = [j for j in plan['jobs'] if j['stage'] == 'full']
        self.assertEqual(len(full), 120)
        self.assertEqual({int(j['request']['year']) for j in full}, set(range(2016, 2026)))
        self.assertEqual(sum(len(j['request']['day']) * 24 for j in full), 87672)
        frozen = json.loads((cli.ROOT / 'data/registry/copernicus_mandi_context_requests_v1.json').read_text())
        self.assertEqual(plan, frozen)
        for job in plan['jobs']:
            self.assertEqual(job['request']['time'][0], '00:00')
            self.assertEqual(job['request']['time'][-1], '23:00')
            self.assertNotIn('pm2_5', job['request']['variable'])
            if job['stage'] != 'smoke':
                r = job['request']
                self.assertEqual(len(r['day']), calendar.monthrange(int(r['year']), int(r['month']))[1])

    def test_missing_token_never_constructs_authenticated_client(self):
        client = mock.Mock()
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(cli.Path, 'home', return_value=Path(tmp)), \
                mock.patch.object(cli.os, 'environ', {}), \
                mock.patch.dict('sys.modules', {'cdsapi': SimpleNamespace(Client=client)}), \
                mock.patch('sys.argv', ['download', '--execute', '--accepted-terms',
                                        'reanalysis-era5-single-levels']), \
                contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(), 2)
        client.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['status'], 'BLOCKED_CDS_ACCOUNT_TOKEN_NOT_CONFIGURED')

    def test_missing_terms_block_execution(self):
        output = io.StringIO()
        with mock.patch('sys.argv', ['download', '--execute']), contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(), 2)
        self.assertEqual(json.loads(output.getvalue())['status'], 'BLOCKED_MANUAL_PRODUCT_TERMS_REQUIRED')

    def test_verified_resume_and_tampered_original(self):
        job = make_plan()['jobs'][0]
        client = Client()
        with tempfile.TemporaryDirectory() as tmp:
            first = download([job], tmp, client)
            self.assertEqual(download([job], tmp, client), first)
            self.assertEqual(client.calls, 1)
            self.assertFalse(first[0]['numeric_contents_validated'])
            self.assertFalse(first[0]['used_for_labels'])
            Path(tmp, job['id'] + '.download').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                download([job], tmp, client)
            self.assertEqual(client.calls, 1)

    def test_changed_request_and_incomplete_source_refused(self):
        job = make_plan()['jobs'][0]
        with tempfile.TemporaryDirectory() as tmp:
            client = Client()
            download([job], tmp, client)
            changed = copy.deepcopy(job)
            changed['request']['day'] = ['05']
            with self.assertRaises(ValueError):
                download([changed], tmp, client)
            Path(tmp, job['id'] + '.receipt.json').unlink()
            with self.assertRaises(ValueError):
                download([job], tmp, client)
            self.assertEqual(client.calls, 1)

    def test_bad_response_preserves_partial(self):
        job = make_plan()['jobs'][0]
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(b'<html>login required</html>')
            with self.assertRaises(ValueError):
                download([job], tmp, client)
            self.assertTrue(Path(tmp, job['id'] + '.part').exists())
            with self.assertRaises(ValueError):
                download([job], tmp, client)
            self.assertEqual(client.calls, 1)

    def test_zip_preserved_without_silent_extraction(self):
        job = make_plan()['jobs'][0]
        with tempfile.TemporaryDirectory() as tmp:
            result = download([job], tmp, Client(b'PK\x03\x04synthetic-container'))
            self.assertEqual(result[0]['container'], 'zip_requires_member_and_variable_validation')
            self.assertFalse(result[0]['numeric_contents_validated'])


if __name__ == '__main__':
    unittest.main()
