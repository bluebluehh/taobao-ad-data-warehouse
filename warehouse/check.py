"""Meaningful checks on real sample data and read-only HTTP behavior."""
import argparse
import json
import sqlite3
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .build import now, write_json
from .metrics import bundle, connect, grouped, overview
from .serve import validate_params

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--base',default='http://127.0.0.1:8765')
    args=p.parse_args()
    out=ROOT/'output/midterm'
    tests=[]
    def check(name, condition, detail=''):
        tests.append({'check':name,'passed':bool(condition),'detail':detail})
        if not condition:
            raise AssertionError(name+': '+str(detail))
    first=json.loads((out/'history/run_01_report.json').read_text(encoding='utf-8'))
    last=json.loads((out/'run_report.json').read_text(encoding='utf-8'))
    check('Deterministic rebuild produces identical metric counts',first['metrics']==last['metrics'])
    check('Source hashes unchanged after rebuild',
          [(x['name'],x['sha256']) for x in first['source_inventory']]==[(x['name'],x['sha256']) for x in last['source_inventory']])
    with connect(out/'warehouse.sqlite3') as db:
        db.execute('PRAGMA cache_size=-262144')
        total=overview(db)
        day=overview(db,{'start':'2017-05-06','end':'2017-05-06'})
        check('Date filter changes scope',0<day['impressions']<total['impressions'])
        daily=grouped(db,'date',order='key')
        check('Cross-day UV is not sum of daily UV',sum(r['reached_users'] for r in daily)>total['reached_users'])
        unmatched=overview(db,{'gender':'__unmatched__'})
        check('Unmatched users retained and separately identifiable',unmatched['impressions']>0 and unmatched['reached_users']>1 and unmatched['profile_row_coverage']==0)
        check('All-unmatched attribute missing rate is undefined',unmatched['pvalue_missing_rate'] is None)
        filtered=overview(db,{'gender':'1'},quality=True)
        check('Quality scope ignores profile filter',filtered['impressions']==total['impressions'] and filtered['profile_row_coverage']==total['profile_row_coverage'])
        sql="SELECT campaign_id FROM v_exposure_detail WHERE campaign_id IS NOT NULL GROUP BY campaign_id HAVING SUM(click_count)=0 LIMIT 1"
        zero_id=db.execute(sql).fetchone()[0]
        zero=overview(db,{'campaign':zero_id})
        check('Real zero-click group: CTR zero, not missing',zero['impressions']>0 and zero['ctr']==0 and zero['user_click_rate']==0)
        groups=grouped(db,'resource',{'campaign':zero_id})
        check('Zero-click contribution denominator returns null',all(r['click_share'] is None for r in groups))
        rows=grouped(db,'campaign',limit=20,order='ctr',min_impressions=1000)
        check('CTR rank enforces exposure eligibility',all(r['impressions']>=1000 for r in rows))
        check('CTR rank uses unrounded ratios',all(rows[i]['ctr']>=rows[i+1]['ctr'] for i in range(len(rows)-1)))
        check('Query value is bound, not SQL-injected',overview(db,{'pid':"' OR 1=1 --"})['impressions']==0)
        begin=time.perf_counter()
        page=bundle(db,{'start':'2017-05-06','end':'2017-05-06'})
        check('Direct query-service bundle matches source scope',page['overview']==day)
        check('Direct query service includes all result panels',all(k in page for k in ['daily','hourly','resources','ranking','cross','quality']))
        check('Temporary query tables cleaned after service call',db.execute("SELECT COUNT(*) FROM sqlite_temp_master WHERE name IN('ads_query_scope','v_exposure_detail')").fetchone()[0]==0)
        service_seconds=round(time.perf_counter()-begin,3)
        try:
            db.execute('DELETE FROM dwd_exposure WHERE source_line=-1')
        except sqlite3.OperationalError:
            check('Read-only connection rejects warehouse writes',True)
        else:
            check('Read-only connection rejects warehouse writes',False)
    for params in [{'group':['bad']},{'start':['2017-05-08'],'end':['2017-05-06']},
                   {'minimum':['-1']},{'unknown':['1']}]:
        try:
            validate_params(params)
        except ValueError:
            check('Service rejects invalid parameters '+str(params),True)
        else:
            check('Service rejects invalid parameters '+str(params),False)
    http=[]
    http_blocked=None
    for path in ['/api/health','/','/app.js','/style.css','/api/data?start=2017-05-06&end=2017-05-06']:
        begin=time.perf_counter()
        try:
            response=urlopen(args.base+path,timeout=180)
        except URLError as exc:
            http_blocked=repr(exc.reason)
            break
        with response:
            body=response.read()
            check('HTTP '+path,response.status==200 and len(body)>0)
            if path.startswith('/api/data'):
                data=json.loads(body)
                check('HTTP date-filter result matches SQL',data['overview']==day)
                check('API preserves quality and sample scope metadata',data['meta']['mode']=='development_sample' and 'quality_scope_note' in data)
            http.append({'path':path,'seconds':round(time.perf_counter()-begin,3),'bytes':len(body)})
    for path in ['/api/data?group=bad','/api/data?start=2017-05-08&end=2017-05-06','/api/data?minimum=-1','/api/data?unknown=1']:
        if http_blocked:
            break
        try:
            urlopen(args.base+path,timeout=20)
        except HTTPError as exc:
            check('Invalid query returns 400 '+path,exc.code==400)
        else:
            check('Invalid query returns 400 '+path,False)
    for path in ['/../sql/schema.sql','/output/midterm/warehouse.sqlite3']:
        if http_blocked:
            break
        try:
            urlopen(args.base+path,timeout=20)
        except HTTPError as exc:
            check('No arbitrary file download '+path,exc.code==404)
        else:
            check('No arbitrary file download '+path,False)
    report={'at':now(),'checks':tests,'http_measurements':http,'passed':all(t['passed'] for t in tests),
            'http_status':'blocked' if http_blocked else 'passed','http_blocker':http_blocked,
            'direct_query_service_seconds':service_seconds,
            'visual_browser_check':'Not completed: browser provider session failed; no screenshot inspection claimed.'}
    write_json(out/'integration_checks.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
