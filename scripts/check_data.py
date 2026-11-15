"""Read-only source audit. Uses Python standard library; run from project root."""
import csv
import hashlib
import json
import tarfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'data_check'
OUT.mkdir(parents=True, exist_ok=True)
data = next(p.parent for p in ROOT.rglob('raw_sample.csv.tar.gz'))
result = {'source': str(data), 'tables': {}, 'notes': [
    'Source files are never modified. Counts cover local files, not the entire platform.',
    'UTC+08:00 is an analysis convention checked against boundaries, not proven source metadata.',
    'Exact duplicate rows are counted but not removed; identical observations need not be errors.'
]}


def say(msg):
    print(msg, flush=True)


def path_for(name):
    return next(p for p in data.rglob(name + '.csv') if p.is_file())


def dimension(name, key):
    """Keep only dimension keys in memory; collect field quality separately."""
    say('Checking ' + name)
    keys = set()
    missing = Counter()
    codes = {}
    rows = duplicates = bad_width = 0
    prices = Counter()
    with path_for(name).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = [x.strip() for x in header]
        pos = cols.index(key)
        for row in reader:
            rows += 1
            if len(row) != len(cols):
                bad_width += 1
                continue
            for col, value in zip(cols, row):
                if not value.strip():
                    missing[col] += 1
                if name == 'user_profile' and col != key:
                    codes.setdefault(col, Counter())[value] += 1
            value = row[pos]
            duplicates += value in keys
            keys.add(value)
            if name == 'ad_feature':
                try:
                    from math import isfinite
                    price = float(row[cols.index('price')])
                    prices['nonfinite' if not isfinite(price) else 'negative' if price < 0 else 'zero' if price == 0 else 'positive'] += 1
                except ValueError:
                    prices['invalid'] += 1
    result['tables'][name] = {'header_original': header, 'header_trimmed': cols,
        'rows': rows, 'bad_width': bad_width, 'key': key, 'distinct_keys': len(keys),
        'extra_duplicate_keys': duplicates, 'missing': {c: missing[c] for c in cols},
        'code_counts': codes, 'price_status': prices}
    return keys


ads = dimension('ad_feature', 'adgroup_id')
profiles = dimension('user_profile', 'userid')
say('Checking raw_sample: full scan and duplicate partitioning')
users = set()
ad_ids = set()
missing_users = set()
missing_ads = set()
days = Counter()
utc_days = Counter()
labels = Counter()
missing = Counter()
rows = bad_width = invalid_labels = invalid_time = clicks = 0
unmatched_users = unmatched_ads = 0
min_time = max_time = None
with TemporaryDirectory(prefix='audit_', dir=OUT) as temp:
    # Rows sharing user + timestamp always enter the same bucket. This permits
    # exact full-row and candidate-key checks without retaining 26m rows in RAM.
    buckets = [Path(temp) / f'{i:03}.bin' for i in range(128)]
    handles = [p.open('wb') for p in buckets]
    try:
        with path_for('raw_sample').open('rb') as f:
            header = f.readline().decode('utf-8-sig').strip().split(',')
            expected = ['user', 'time_stamp', 'adgroup_id', 'pid', 'nonclk', 'clk']
            if header != expected:
                raise ValueError(f'Unexpected raw header: {header}')
            for line in f:
                rows += 1
                row = line.rstrip(b'\r\n').split(b',')
                if len(row) != 6:
                    bad_width += 1
                    continue
                u, stamp, ad, pid, nonclk, clk = row
                for col, value in zip(header, row):
                    missing[col] += not value.strip()
                user = u.decode('ascii')
                aid = ad.decode('ascii')
                users.add(user)
                ad_ids.add(aid)
                if user not in profiles:
                    unmatched_users += 1
                    missing_users.add(user)
                if aid not in ads:
                    unmatched_ads += 1
                    missing_ads.add(aid)
                labels[(nonclk + b',' + clk).decode('ascii')] += 1
                valid = (nonclk, clk) in [(b'1', b'0'), (b'0', b'1')]
                invalid_labels += not valid
                clicks += clk == b'1' and valid
                try:
                    t = int(stamp)
                    min_time = t if min_time is None else min(min_time, t)
                    max_time = t if max_time is None else max(max_time, t)
                    utc_days[t // 86400] += 1
                    days[(t + 28800) // 86400] += 1
                except ValueError:
                    invalid_time += 1
                index = hashlib.blake2b(u + b',' + stamp, digest_size=1).digest()[0] % 128
                handles[index].write(b','.join(row) + b'\n')
                if rows % 5_000_000 == 0:
                    say(f'raw_sample scanned: {rows:,}')
    finally:
        for f in handles:
            f.close()
    say('Checking exact duplicate rows and user + timestamp collisions')
    extra_rows = duplicate_groups = key_extra = key_groups = 0
    for p in buckets:
        full = Counter()
        keys = Counter()
        with p.open('rb') as f:
            for line in f:
                full[line] += 1
                fields = line.split(b',', 2)
                keys[(fields[0], fields[1])] += 1
        extra_rows += sum(n - 1 for n in full.values() if n > 1)
        duplicate_groups += sum(n > 1 for n in full.values())
        key_extra += sum(n - 1 for n in keys.values() if n > 1)
        key_groups += sum(n > 1 for n in keys.values())
        del full, keys
        p.unlink()


def time_text(t, hours):
    return datetime.fromtimestamp(t, timezone(timedelta(hours=hours))).isoformat()


def dates(counts):
    return {datetime.fromtimestamp(d * 86400, timezone.utc).date().isoformat(): n
            for d, n in sorted(counts.items())}


result['tables']['raw_sample'] = {
    'header_original': header, 'rows': rows, 'bad_width': bad_width,
    'missing': dict(missing), 'label_pairs_nonclk_clk': dict(labels),
    'invalid_label_rows': invalid_labels, 'invalid_timestamp_rows': invalid_time,
    'valid_clicks': clicks, 'ctr_before_duplicate_policy': clicks / rows,
    'distinct_users': len(users), 'distinct_ads': len(ad_ids),
    'unmatched_profile_rows': unmatched_users, 'unmatched_profile_users': len(missing_users),
    'unmatched_ad_rows': unmatched_ads, 'unmatched_ad_ids': len(missing_ads),
    'profile_row_coverage': 1 - unmatched_users / rows,
    'profile_user_coverage': 1 - len(missing_users) / len(users),
    'ad_row_coverage': 1 - unmatched_ads / rows,
    'min_timestamp': min_time, 'max_timestamp': max_time,
    'range_utc': [time_text(t, 0) for t in (min_time, max_time)],
    'range_utc8': [time_text(t, 8) for t in (min_time, max_time)],
    'daily_utc': dates(utc_days), 'daily_utc8': dates(days),
    'exact_duplicate_groups': duplicate_groups, 'extra_exact_duplicate_rows': extra_rows,
    'user_timestamp_duplicate_groups': key_groups, 'user_timestamp_extra_rows': key_extra
}
say('Inspecting behavior archive header only (not a full row count)')
with tarfile.open(data / 'behavior_log.csv.tar.gz', mode='r|gz') as tar:
    member = next(m for m in tar if m.isfile())
    f = tar.extractfile(member)
    lines = [f.readline().decode('utf-8-sig').rstrip('\r\n') for _ in range(4)]
    result['tables']['behavior_log'] = {'archive_bytes': (data / 'behavior_log.csv.tar.gz').stat().st_size,
        'member': member.name, 'uncompressed_bytes_declared': member.size,
        'first_four_lines': lines, 'full_scan_completed': False,
        'warning': 'Tar member size is declared metadata; full gzip CRC and actual row count not checked.'}
path = OUT / 'audit.json'
path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
say('Audit complete: ' + str(path))
