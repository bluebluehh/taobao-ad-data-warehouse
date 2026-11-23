#!/usr/bin/env python3
"""Local full-source preflight. Does not load Hive or certify cluster acceptance."""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import time
from zoneinfo import ZoneInfo
from stage_csv import HEADERS, normalized_header, file_sha256

ATTRS = ['final_gender_code', 'age_level', 'shopping_level', 'pvalue_level', 'occupation', 'new_user_class_level']


def rows(path, name):
    import csv
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        normalized_header(next(reader, None), HEADERS[name])
        for row in reader:
            if len(row) != len(HEADERS[name]):
                raise ValueError(f'{path.name}:{reader.line_num}: wrong field count')
            yield [v.strip() for v in row]


def audit(source, staged):
    started = time.monotonic()
    manifest = json.loads((staged/'manifest.json').read_text())
    result = {'scope': 'full_csv_local_preflight', 'cluster_verified': False,
              'warehouse_real_data_accepted': False, 'technical_validation': manifest['technical_validation'],
              'business_period': manifest['business_period'], 'integrity': {}, 'dimensions': {}}
    # Verify both originals and prepared files before deriving evidence.
    for item in manifest['files']:
        for kind, path, digest, size in [
            ('source', source/item['source_file'], item['sha256'], item['source_bytes']),
            ('staged', staged/item['staged_file'], item['staged_sha256'], item['staged_bytes'])]:
            if path.stat().st_size != size or file_sha256(path) != digest:
                raise ValueError('Manifest integrity mismatch: '+str(path))
        result['integrity'][item['source_file']] = {'source_sha256': item['sha256'], 'staged_sha256': item['staged_sha256'], 'verified': True}
        print('Integrity verified: '+item['source_file'], flush=True)
    ads = set()
    profiles = {}
    for name, store in [('ad_feature', ads), ('user_profile', profiles)]:
        count = empty = duplicate = 0
        missing = Counter()
        for row in rows(source/(name+'.csv'), name):
            count += 1
            key = row[0]
            if not key:
                empty += 1
            elif key in store:
                duplicate += 1
            elif name == 'ad_feature':
                store.add(key)
            else:
                values = dict(zip(HEADERS[name], row))
                mask = sum(1 << i for i, attr in enumerate(ATTRS) if not values[attr])
                profiles[key] = mask
                for i, attr in enumerate(ATTRS):
                    missing[attr] += bool(mask & (1 << i))
        result['dimensions'][name] = {'rows': count, 'empty_keys': empty, 'duplicate_key_rows': duplicate,
                                      'unique_nonempty_keys': len(store), 'source_attribute_missing_rows': dict(missing)}
        if empty or duplicate:
            raise ValueError(name+': empty or duplicate dimension keys; join audit stopped')
    tz = ZoneInfo('Asia/Shanghai')
    period = manifest['business_period']
    start = int(datetime.fromisoformat(period['start_date']).replace(tzinfo=tz).timestamp())
    end = int((datetime.fromisoformat(period['end_date'])+timedelta(days=1)).replace(tzinfo=tz).timestamp())
    counts = Counter()
    rejects = Counter()
    dates = Counter()
    attr_missing = Counter()
    users, clicked_users, exposed_ads = set(), set(), set()
    for row in rows(source/'raw_sample.csv', 'raw_sample'):
        user, stamp, ad, pid, nonclk, clk = row
        counts['source_rows'] += 1
        reason = None
        if not user: reason = 'missing_user_id'
        elif not ad: reason = 'missing_adgroup_id'
        elif not pid: reason = 'missing_pid'
        elif not re.fullmatch('[0-9]{10}', stamp): reason = 'invalid_timestamp'
        elif not start <= int(stamp) < end: reason = 'outside_business_period'
        elif (nonclk, clk) not in [('1', '0'), ('0', '1')]: reason = 'invalid_click_flags'
        if reason:
            rejects[reason] += 1
        else:
            counts['valid_rows'] += 1
            counts['clicks'] += int(clk)
            users.add(user)
            exposed_ads.add(ad)
            if clk == '1': clicked_users.add(user)
            # Integer day offset avoids converting every timestamp into a datetime.
            dates[(int(stamp)-start)//86400] += 1
            if ad in ads: counts['matched_ad_exposures'] += 1
            mask = profiles.get(user)
            if mask is not None:
                counts['matched_profile_exposures'] += 1
                for i, attr in enumerate(ATTRS):
                    attr_missing[attr] += bool(mask & (1 << i))
        if counts['source_rows'] % 5_000_000 == 0:
            print('Audited exposure rows: '+str(counts['source_rows']), flush=True)
    counts['reached_users'] = len(users)
    counts['clicked_users'] = len(clicked_users)
    counts['exposed_ads'] = len(exposed_ads)
    counts['matched_profile_users'] = sum(user in profiles for user in users)
    expected = {x['source_file']: x['rows'] for x in manifest['files']}
    if counts['source_rows'] != expected['raw_sample.csv'] or any(result['dimensions'][n]['rows'] != expected[n+'.csv'] for n in ['ad_feature', 'user_profile']):
        raise ValueError('Row counts differ from manifest')
    result.update(counts=dict(counts), rejected_by_reason=dict(rejects),
                  date_rows={(datetime.fromisoformat(period['start_date'])+timedelta(days=d)).date().isoformat():n for d,n in sorted(dates.items())},
                  matched_profile_attribute_missing_exposures=dict(attr_missing),
                  local_preflight_passed=True, elapsed_seconds=round(time.monotonic()-started, 2),
                  limitations=['No Hive/Tez execution', 'No whole-row duplicate detection', 'No source-side Windows hash comparison', 'No business conclusions or cluster acceptance'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--staged', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    try:
        result = audit(args.source, args.staged)
    except Exception as error:
        (args.out/'failure.json').write_text(json.dumps({'local_preflight_passed':False, 'error':str(error)}, indent=2))
        raise
    (args.out/'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
