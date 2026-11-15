"""Build a reproducible development warehouse from genuine source files.

Run: python -m warehouse.build --rate 0.02
Use --rate 1 for the future full-data run; this is not run implicitly.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sqlite3
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .metrics import AGG, bundle, grouped, overview

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))
SCHEMA_VERSION = 'midterm-1'


def now():
    return datetime.now(TZ).isoformat(timespec='seconds')


def log(message):
    print(f'[{now()}] {message}', flush=True)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def sources(folder):
    found = {}
    for name in ['raw_sample', 'ad_feature', 'user_profile']:
        matches = [p for p in folder.rglob(name + '.csv') if p.is_file()]
        if len(matches) != 1:
            raise ValueError(f'Expected one {name}.csv, found {len(matches)}')
        found[name] = matches[0]
    return found


def fingerprint(paths):
    return {k: {'path': str(p.resolve()), 'bytes': p.stat().st_size,
                'mtime_ns': p.stat().st_mtime_ns} for k, p in paths.items()}


def program_hash():
    h = hashlib.sha256()
    for p in sorted([ROOT/'warehouse/build.py', ROOT/'warehouse/metrics.py', ROOT/'sql/schema.sql']):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def load_dimension(db, name, path, table, expected):
    h = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    batch, rows = [], 0
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        original = next(reader)
        if [c.strip() for c in original] != expected:
            raise ValueError(f'Unexpected header for {name}: {original}')
        sql = f'INSERT INTO {table} VALUES ({",".join("?" for _ in range(len(expected)+1))})'
        for num, row in enumerate(reader, 2):
            rows += 1
            if len(row) != len(expected):
                raise ValueError(f'Dimension malformed at {name}:{num}')
            batch.append((num, *row))
            if len(batch) == 10000:
                db.executemany(sql, batch)
                batch.clear()
        db.executemany(sql, batch)
    db.execute('INSERT INTO source_inventory VALUES (?,?,?,?,?,?)',
               (name, str(path.resolve()), h, rows, path.stat().st_size, json.dumps(original)))
    log(f'{table}: {rows:,} rows')


def load_exposure(db, path, rate, seed):
    h = hashlib.sha256()
    threshold = int(rate * (1 << 64))
    key = seed.encode('utf-8')
    batch, rejected = [], []
    expected = {'source_rows': 0, 'selected_rows': 0, 'valid_rows': 0, 'clicks': 0,
                'daily': Counter(), 'resources': Counter()}
    users, ads, clicked = set(), set(), set()
    start, end = 1494000000, 1494691200
    with path.open('rb') as f:
        head = f.readline()
        h.update(head)
        header = head.decode('utf-8-sig').strip().split(',')
        if header != ['user', 'time_stamp', 'adgroup_id', 'pid', 'nonclk', 'clk']:
            raise ValueError(f'Unexpected exposure header: {header}')
        for line_num, raw in enumerate(f, 2):
            expected['source_rows'] += 1
            h.update(raw)
            choose = rate == 1 or int.from_bytes(hashlib.blake2b(raw, digest_size=8, key=key).digest(), 'big') < threshold
            if not choose:
                continue
            expected['selected_rows'] += 1
            text = raw.decode('utf-8').rstrip('\r\n')
            row = text.split(',')
            if len(row) != 6:
                rejected.append(('raw_sample', line_num, 'field_count', text))
                continue
            batch.append((line_num, *row))
            u, stamp, ad, pid, nonclk, clk = row
            reason = None
            try:
                ts = int(stamp)
                if not all([u.strip(), ad.strip(), pid.strip(), stamp.strip()]):
                    reason = 'missing_required'
                elif (nonclk, clk) not in [('1', '0'), ('0', '1')]:
                    reason = 'invalid_label'
                elif not start <= ts < end:
                    reason = 'outside_business_range'
            except ValueError:
                reason = 'invalid_timestamp'
            if reason:
                rejected.append(('raw_sample', line_num, reason, text))
            else:
                expected['valid_rows'] += 1
                expected['clicks'] += int(clk)
                day = datetime.fromtimestamp(ts, TZ).date().isoformat()
                expected['daily'][day] += 1
                expected['resources'][pid] += 1
                users.add(u)
                ads.add(ad)
                if clk == '1':
                    clicked.add(u)
            if len(batch) >= 10000:
                db.executemany('INSERT INTO ods_exposure VALUES (?,?,?,?,?,?,?)', batch)
                batch.clear()
            if expected['source_rows'] % 5_000_000 == 0:
                log(f"Source position {expected['source_rows']:,}, selected {expected['selected_rows']:,}")
        db.executemany('INSERT INTO ods_exposure VALUES (?,?,?,?,?,?,?)', batch)
        db.executemany('INSERT INTO ods_reject VALUES (?,?,?,?)', rejected)
    expected.update(reached_users=len(users), clicked_users=len(clicked), exposed_ads=len(ads),
                    rejected_rows=len(rejected))
    db.execute('INSERT INTO source_inventory VALUES (?,?,?,?,?,?)',
               ('raw_sample', str(path.resolve()), h.hexdigest(), expected['source_rows'],
                path.stat().st_size, json.dumps(header)))
    log(f"Exposure selected {expected['selected_rows']:,}; valid {expected['valid_rows']:,}")
    return expected


def make_dimensions(db):
    for table, key in [('ods_ad', 'adgroup_id'), ('ods_user', 'userid')]:
        total, unique = db.execute(f'SELECT COUNT(*),COUNT(DISTINCT NULLIF(TRIM({key}),\'\')) FROM {table}').fetchone()
        if total != unique:
            raise ValueError(f'Dimension duplicate or missing keys in {table}')
    db.executescript('''
    INSERT INTO dim_user(user_id,cms_segid,cms_group_id,gender_code,age_level,pvalue_level,
      shopping_level,occupation,city_level,profile_matched)
    SELECT TRIM(userid),NULLIF(TRIM(cms_segid),''),NULLIF(TRIM(cms_group_id),''),
      NULLIF(TRIM(final_gender_code),''),NULLIF(TRIM(age_level),''),NULLIF(TRIM(pvalue_level),''),
      NULLIF(TRIM(shopping_level),''),NULLIF(TRIM(occupation),''),NULLIF(TRIM(new_user_class_level),''),1
    FROM ods_user ORDER BY source_line;
    INSERT INTO dim_user(user_id,profile_matched)
    SELECT DISTINCT TRIM(o.user),0 FROM ods_exposure o
    LEFT JOIN dim_user u ON u.user_id=TRIM(o.user) WHERE u.user_sk IS NULL;
    INSERT INTO dim_ad(adgroup_id,cate_id,campaign_id,customer_id,brand,price,ad_matched)
    SELECT TRIM(adgroup_id),NULLIF(TRIM(cate_id),''),NULLIF(TRIM(campaign_id),''),
      NULLIF(TRIM(customer),''),NULLIF(TRIM(brand),''),CAST(NULLIF(TRIM(price),'') AS REAL),1 FROM ods_ad ORDER BY source_line;
    INSERT INTO dim_ad(adgroup_id,ad_matched)
    SELECT DISTINCT TRIM(o.adgroup_id),0 FROM ods_exposure o
    LEFT JOIN dim_ad a ON a.adgroup_id=TRIM(o.adgroup_id) WHERE a.ad_sk IS NULL;
    INSERT INTO dim_resource SELECT DISTINCT TRIM(pid) FROM ods_exposure WHERE TRIM(pid)<>'';
    ''')
    first = date(2017, 5, 6)
    db.executemany('INSERT INTO dim_date VALUES (?,?,?,?,?,?)',
                   [(int(d.strftime('%Y%m%d')), d.isoformat(), d.year, d.month, d.day, d.isoweekday())
                    for d in [first + timedelta(days=i) for i in range(8)]])
    db.executemany('INSERT INTO dim_hour VALUES (?,?)', [(i, f'{i:02}:00') for i in range(24)])


def make_fact(db):
    db.executescript('''
    INSERT INTO dwd_exposure
    SELECT o.source_line,u.user_sk,a.ad_sk,
      CAST(strftime('%Y%m%d',CAST(o.time_stamp AS INTEGER),'unixepoch','+8 hours') AS INTEGER),
      CAST(strftime('%H',CAST(o.time_stamp AS INTEGER),'unixepoch','+8 hours') AS INTEGER),
      TRIM(o.pid),CAST(o.time_stamp AS INTEGER),1,CAST(o.clk AS INTEGER)
    FROM ods_exposure o JOIN dim_user u ON u.user_id=TRIM(o.user)
    JOIN dim_ad a ON a.adgroup_id=TRIM(o.adgroup_id)
    WHERE NOT EXISTS(SELECT 1 FROM ods_reject r WHERE r.source='raw_sample' AND r.source_line=o.source_line);
    CREATE INDEX idx_fact_date_pid ON dwd_exposure(date_key,pid);
    CREATE INDEX idx_fact_user ON dwd_exposure(user_sk);
    CREATE INDEX idx_fact_ad ON dwd_exposure(ad_sk);
    ''')


def make_summary(db):
    groups = {'dws_daily': 'date', 'dws_resource_daily': 'date,pid',
              'dws_hourly': 'date,hour_key,pid', 'dws_ad_daily': 'date,ad_sk,pid',
              'dws_audience_daily': 'date,profile_matched,gender_code,age_level,shopping_level,pvalue_level,city_level'}
    for name, cols in groups.items():
        log('Building ' + name)
        db.execute(f'CREATE TABLE {name} AS SELECT {cols},{AGG} FROM v_exposure_detail GROUP BY {cols}')
    db.execute('CREATE TABLE ads_overview AS SELECT '+ AGG +' FROM v_exposure_detail')
    for name, cols in {'ads_daily': 'date', 'ads_resource': 'pid', 'ads_campaign': 'campaign_id',
                       'ads_gender': 'profile_matched,gender_code',
                       'ads_cross_age_resource': 'pid,profile_matched,age_level'}.items():
        db.execute(f'CREATE TABLE {name} AS WITH g AS (SELECT {cols},{AGG} FROM v_exposure_detail GROUP BY {cols}) '
                   'SELECT *,1.0*clicks/NULLIF(impressions,0) ctr,1.0*clicked_users/NULLIF(reached_users,0) user_click_rate, '
                   '1.0*impressions/NULLIF(reached_users,0) avg_impressions_per_user FROM g')


def validate(db, expected):
    tests = []
    def check(name, actual, wanted):
        passed = actual == wanted
        tests.append({'check': name, 'actual': actual, 'expected': wanted, 'passed': passed})
        if not passed:
            raise AssertionError(f'{name}: {actual} != {wanted}')
    m = overview(db)
    for key in ['impressions', 'clicks', 'reached_users', 'clicked_users', 'exposed_ads']:
        check('Independent source vs DWD: ' + key, m[key], expected['valid_rows'] if key == 'impressions' else expected[key])
    check('Selected = valid + rejected', expected['selected_rows'], expected['valid_rows'] + expected['rejected_rows'])
    check('Eight dates in development sample', len(expected['daily']), 8)
    check('Foreign key violations', len(db.execute('PRAGMA foreign_key_check').fetchall()), 0)
    check('Fact to detail join row preservation', db.execute('SELECT COUNT(*) FROM dwd_exposure').fetchone()[0], m['impressions'])
    for table in ['dws_daily', 'dws_resource_daily', 'dws_hourly', 'dws_ad_daily', 'dws_audience_daily',
                  'ads_daily', 'ads_resource', 'ads_campaign', 'ads_gender', 'ads_cross_age_resource']:
        n, clicks = db.execute(f'SELECT SUM(impressions),SUM(clicks) FROM {table}').fetchone()
        check(table + ' exposure conservation', n, m['impressions'])
        check(table + ' click conservation', clicks, m['clicks'])
    actual_daily = {row['group_key']: row['impressions'] for row in grouped(db, 'date', order='key')}
    check('Daily counts vs independent Python source counter', actual_daily, dict(expected['daily']))
    empty = overview(db, {'start': '2018-01-01'})
    check('Empty scope count', empty['impressions'], 0)
    check('Empty scope CTR undefined', empty['ctr'], None)
    check('Source lineage unique', db.execute('SELECT COUNT(*)-COUNT(DISTINCT source_line) FROM dwd_exposure').fetchone()[0], 0)
    for filt in [{'start': '2017-05-06', 'end': '2017-05-06'}, {'pid': next(iter(expected['resources']))},
                 {'gender': '__unmatched__'}, {'gender': '1'}]:
        total = overview(db, filt)
        rows = grouped(db, 'campaign', filt)
        check('Filtered exposure totals ' + str(filt), sum(r['impressions'] for r in rows), total['impressions'])
        check('Filtered click totals ' + str(filt), sum(r['clicks'] for r in rows), total['clicks'])
        if rows:
            top = grouped(db, 'campaign', filt, limit=1)
            check('Top N contribution denominator '+str(filt), top[0]['impression_share'], top[0]['impressions']/total['impressions'])
    return tests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / '淘宝展示广告点击率预估数据集')
    parser.add_argument('--out', type=Path, default=ROOT / 'output/midterm')
    parser.add_argument('--rate', type=float, default=0.02)
    parser.add_argument('--seed', default='dw2026-midterm')
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    if not 0 < args.rate <= 1 or len(args.seed.encode()) > 64:
        parser.error('rate must be in (0,1], seed <=64 UTF-8 bytes')
    args.out.mkdir(parents=True, exist_ok=True)
    paths = sources(args.source)
    config = {'rate': args.rate, 'seed': args.seed, 'schema_version': SCHEMA_VERSION,
              'program_hash': program_hash(), 'sources': fingerprint(paths)}
    target = args.out / 'warehouse.sqlite3'
    report_path = args.out / 'run_report.json'
    if target.exists() and report_path.exists() and not args.rebuild:
        old = json.loads(report_path.read_text(encoding='utf-8'))
        if old['config'] != config:
            raise ValueError('Inputs or program changed; use --rebuild or a different --out')
        write_json(args.out / 'reuse_check.json', {'at': now(), 'reused': True,
                   'db_bytes': target.stat().st_size, 'source_unchanged': True,
                   'note': 'Reused without inserting records again; source size/mtime and program fingerprint match.'})
        log('Verified existing run reused; no duplicate import')
        return
    build_path = args.out / 'warehouse.building.sqlite3'
    if build_path.exists():
        raise FileExistsError('A partial build exists; inspect it before retrying: '+str(build_path))
    begin = time.perf_counter()
    db = sqlite3.connect(build_path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA cache_size=-262144')
    db.execute('PRAGMA temp_store=FILE')
    db.executescript((ROOT / 'sql/schema.sql').read_text(encoding='utf-8'))
    try:
        log('Loading genuine dimension sources')
        load_dimension(db, 'ad_feature', paths['ad_feature'], 'ods_ad',
                       ['adgroup_id','cate_id','campaign_id','customer','brand','price'])
        load_dimension(db, 'user_profile', paths['user_profile'], 'ods_user',
                       ['userid','cms_segid','cms_group_id','final_gender_code','age_level','pvalue_level',
                        'shopping_level','occupation','new_user_class_level'])
        # Validate price in Python: SQLite CAST alone would turn invalid text into zero.
        invalid_prices = sum(1 for row in db.execute('SELECT price FROM ods_ad')
                             if row[0].strip() and (not math.isfinite(float(row[0])) or float(row[0]) < 0))
        if invalid_prices:
            raise ValueError('Nonfinite or negative price values require review')
        log('Scanning exposure source and choosing deterministic sample')
        expected = load_exposure(db, paths['raw_sample'], args.rate, args.seed)
        log('Building dimensions and transaction facts')
        make_dimensions(db)
        make_fact(db)
        make_summary(db)
        db.execute('ANALYZE')
        tests = validate(db, expected)
        meta = {'created_at': now(), 'mode': 'full' if args.rate == 1 else 'development_sample',
                'sample_rate': args.rate, 'sample_seed': args.seed,
                'sampling': 'keyed BLAKE2b-64 on each exact source line, unsigned digest below rate*2^64',
                'source_rows_scanned': expected['source_rows'], 'source_selected_rows': expected['selected_rows'],
                'timezone': 'UTC+08:00', 'start_date': '2017-05-06', 'end_date': '2017-05-13',
                'scope': 'Three core tables only; no behavior_log import; original files unchanged'}
        for key, value in meta.items():
            db.execute('INSERT INTO run_info VALUES (?,?)', (key, json.dumps(value, ensure_ascii=False)))
        db.commit()
        log('Exporting ADS snapshot for browser preview')
        snap = {'meta': meta, **bundle(db)}
        snap['options'] = {key: [row[0] for row in db.execute('SELECT DISTINCT '+col+' FROM v_exposure_detail WHERE '+col+' IS NOT NULL ORDER BY '+col)]
                           for key, col in [('pid','pid'),('gender','gender_code'),('age','age_level'),('shopping','shopping_level')]}
        source_rows = [dict(row) for row in db.execute('SELECT * FROM source_inventory')]
        report = {'at': now(), 'config': config, 'meta': meta, 'source_inventory': source_rows,
                  'independent_source_sample': expected, 'metrics': snap['overview'],
                  'checks': tests, 'checks_passed': all(t['passed'] for t in tests),
                  'elapsed_seconds': round(time.perf_counter()-begin, 2),
                  'tables': [dict(row) for row in db.execute("SELECT name,type FROM sqlite_master WHERE type IN('table','view') ORDER BY name")]}
        db.close()
        os.replace(build_path, target)
        report['database_bytes'] = target.stat().st_size
        write_json(report_path, report)
        write_json(args.out / 'ads_snapshot.json', snap)
        write_json(args.out / 'checks.json', tests)
        log(f"Complete: {expected['valid_rows']:,} valid sample facts, {len(tests)} checks passed")
    except Exception as exc:
        db.close()
        write_json(args.out / 'failed_run.json', {'at': now(), 'error': repr(exc),
                   'partial_database': str(build_path), 'previous_database_preserved': target.exists()})
        raise


if __name__ == '__main__':
    main()
