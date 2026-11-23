import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/platform'))
from audit_source_csv import audit
from create_sql_v2_fixture import FILES
from stage_csv import HEADERS, business_period, stage_file


class SourceAudit(unittest.TestCase):
    def fixture(self, root, duplicate=False):
        source, staged = root/'source', root/'staged'
        source.mkdir()
        staged.mkdir()
        for name, text in FILES.items():
            if duplicate and name == 'ad_feature.csv':
                text += text.splitlines()[1]+'\n'
            (source/name).write_text(text)
        files = [stage_file(source/(n+'.csv'), staged/(n+'.tsv'), h) for n,h in HEADERS.items()]
        (staged/'manifest.json').write_text(json.dumps({'files':files, 'business_period':business_period(), 'technical_validation':True}))
        return source, staged

    def test_full_fixture_counts_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            source, staged = self.fixture(Path(folder))
            result = audit(source, staged)
            c = result['counts']
            self.assertEqual([c[k] for k in ['source_rows','valid_rows','clicks','reached_users','exposed_ads','matched_profile_exposures','matched_profile_users']], [17,9,4,4,3,7,2])
            self.assertEqual(sum(result['rejected_by_reason'].values()), 8)
            self.assertFalse(result['warehouse_real_data_accepted'])
            (staged/'raw_sample.tsv').write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                audit(source, staged)

    def test_duplicate_dimension_stops_join_audit(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            source, staged = self.fixture(Path(folder), duplicate=True)
            with self.assertRaisesRegex(ValueError, 'duplicate dimension keys'):
                audit(source, staged)
