"""Regression coverage for real input headers, immutable business periods and query safety."""
from pathlib import Path
import csv
import importlib
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/platform'))
stage=importlib.import_module('stage_csv')
queries=importlib.import_module('metric_queries')

class HeadersAndPeriod(unittest.TestCase):
    def test_documented_trailing_space_alias_preserves_original_header_and_source_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            original=list(stage.HEADERS['user_profile'])
            original[-1]+=' '
            source=root/'user_profile.csv'
            with source.open('w',newline='') as out:csv.writer(out).writerows([original,['1']*len(original)])
            before=source.read_bytes()
            result=stage.stage_file(source,root/'user_profile.tsv',stage.HEADERS['user_profile'])
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(result['source_header'],original)
            self.assertEqual(result['normalized_header'],stage.HEADERS['user_profile'])
            self.assertEqual(result['sha256'],stage.file_sha256(source))

    def test_unapproved_header_changes_still_rejected(self):
        expected=stage.HEADERS['user_profile']
        for actual in [expected+['extra'],expected[:-1],['userid ']+expected[1:],expected[:-1]+['city_level']]:
            with self.subTest(actual=actual),self.assertRaises(ValueError):
                stage.normalized_header(actual,expected)

    def test_period_requires_canonical_dates_and_order(self):
        self.assertEqual(stage.business_period()['timezone'],'Asia/Shanghai')
        for start,end in [('20170506','2017-05-13'),('2017-05-14','2017-05-13'),('2017-02-30','2017-05-13')]:
            with self.assertRaises(ValueError):stage.business_period(start,end)

class QueryContracts(unittest.TestCase):
    def build(self,**kwargs):
        options=dict(namespace='validation_tests',batch='v2',start='2017-05-06',end='2017-05-13',
                     axes=['occupation','city'],filters={},sort='clicks',minimum=None,limit=10)
        options.update(kwargs)
        return queries.build_queries(**options)

    def test_portrait_filter_not_used_to_inflate_quality_coverage(self):
        sql,context=self.build(filters={'gender':'1','pid':'slot_a'})
        self.assertEqual(context['quality_scope_filters'],{'pid':'slot_a'})
        self.assertIn("(pid)='slot_a'",sql['quality'])
        self.assertNotIn(")='1'",sql['quality'])
        self.assertIn(")='1'",sql['overview'])

    def test_ctr_threshold_and_topn_do_not_redefine_contribution_denominator(self):
        sql,context=self.build(sort='ctr',limit=1)
        self.assertEqual(context['min_impressions'],1000)
        self.assertLess(sql['groups'].index('SUM(impressions) OVER()'),sql['groups'].index('WHERE impressions>=1000'))
        self.assertIn('ORDER BY ctr DESC,impressions DESC,group_value_1,group_value_2 LIMIT 1',sql['groups'])

    def test_sql_injection_and_unbounded_requests_rejected(self):
        for options in [dict(namespace='bad;drop'),dict(batch="x'"),dict(filters={'unknown':'1'}),
                        dict(filters={'pid':"x';drop table x;--"}),dict(axes=['city','city']),
                        dict(limit=1001),dict(minimum=-1)]:
            with self.subTest(options=options),self.assertRaises(ValueError):self.build(**options)

    def test_empty_scope_count_contract_and_null_ratios(self):
        sql,_=self.build(start='2018-01-01',end='2018-01-02')
        self.assertIn('COALESCE(SUM(click_count),0) clicks',sql['overview'])
        self.assertIn('nullif(COUNT(*),0)',sql['overview'])
        self.assertIn('COALESCE(SUM(CASE WHEN profile_matched',sql['quality'])
        self.assertIn('nullif(matched_profile_impressions,0)',sql['quality'])

if __name__=='__main__':unittest.main()
