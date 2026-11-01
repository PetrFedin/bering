import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.v27_primary_xls import (OFFICIAL, OLE_MAGIC, admissible_url, get_public_xls,
                                    inspect_original, run, sha256, excel_label)


class V27PrimaryTests(unittest.TestCase):
    def test_exact_official_urls_allowed(self):
        self.assertEqual(len(OFFICIAL), 4)
        for url, _ in OFFICIAL.values():
            self.assertTrue(admissible_url(url))

    def test_reject_nonofficial(self):
        for url in ('http://magadanport.ru/z.xls', 'https://example.com/z.xls',
                    'https://magadanport.ru/other/z.xls',
                    'https://magadanport.ru/wp-content/uploads/2026/x.xls?query=1',
                    'https://user:pass@magadanport.ru/wp-content/uploads/2026/x.xls',
                    'https://magadanport.ru/wp-content/uploads/2026/x.xlsx'):
            with self.subTest(url=url):
                self.assertFalse(admissible_url(url))

    def test_bad_source_fails_before_network(self):
        with self.assertRaises(ValueError):
            get_public_xls('https://untrusted.example.com/a.xls')

    def test_ole_required(self):
        with self.assertRaises(ValueError):
            inspect_original(b'<html>error</html>', 'BAD')

    def test_size_limit(self):
        with self.assertRaises(ValueError):
            inspect_original(OLE_MAGIC + b'0' * 2_500_010, 'BIG')

    def test_sha_deterministic(self):
        self.assertEqual(sha256(b'abc'),
                         'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_excel_labels(self):
        self.assertEqual(excel_label(0, 0), 'A1')
        self.assertEqual(excel_label(26, 10), 'AA11')

    def test_failed_fetch_keeps_null_proof(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('scripts.v27_primary_xls.get_public_xls', side_effect=OSError('offline')):
                out, code = run(Path(d), require_all=True)
            self.assertEqual(code, 2)
            self.assertEqual(out['metrics_accepted'], 0)
            self.assertEqual(out['status'], 'SOURCE_FETCH_INCOMPLETE')
            self.assertTrue(all(x['file_sha256'] is None for x in out['sources'].values()))

    def test_encrypted_public_xls_retains_raw_sha_without_false_metric(self):
        with tempfile.TemporaryDirectory() as d:
            raw = OLE_MAGIC + b'SYNTHETIC_ENCRYPTED_FIXTURE'
            with patch('scripts.v27_primary_xls.get_public_xls', return_value=raw), \
                 patch('scripts.v27_primary_xls.inspect_original',
                       side_effect=ValueError('Workbook is encrypted')):
                out, code = run(Path(d), require_all=True, save_originals=True)
            self.assertEqual(code, 2)
            self.assertEqual(out['status'], 'SOURCE_BYTES_ACQUIRED_MAPPING_BLOCKED')
            for key, item in out['sources'].items():
                self.assertEqual(item['file_sha256'], sha256(raw))
                self.assertEqual(item['file_bytes'], len(raw))
                self.assertTrue(item['raw_file_acquired'])
                self.assertEqual(item['status'], 'SOURCE_BYTES_ACQUIRED_PARSING_BLOCKED')
                self.assertEqual(item['metrics_accepted'], 0)
                self.assertEqual((Path(d)/'original_xls'/(key+'.xls')).read_bytes(), raw)

    def test_valid_source_still_needs_manual_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            mock_result = {'status': 'ORIGINAL_BYTES_PARSED_METRICS_REQUIRE_MANUAL_CELL_MAPPING',
                           'file_sha256': sha256(OLE_MAGIC), 'candidate_rows': []}
            with patch('scripts.v27_primary_xls.get_public_xls', return_value=OLE_MAGIC), \
                 patch('scripts.v27_primary_xls.inspect_original', return_value=mock_result):
                out, code = run(Path(d), require_all=True)
            self.assertEqual(code, 0)
            self.assertEqual(out['status'], 'RAW_XLS_ACQUIRED_MAPPING_PENDING')
            self.assertFalse(out['new_40ft_paid_volume_verified'])
            self.assertEqual(out['metrics_accepted'], 0)


if __name__ == '__main__':
    unittest.main()
