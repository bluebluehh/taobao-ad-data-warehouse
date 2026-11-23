#!/usr/bin/env python3
"""Stream real CSV to provenance TSV for Hive ODS; does not sample or alter sources."""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path

HEADERS = {
    'raw_sample': ['user', 'time_stamp', 'adgroup_id', 'pid', 'nonclk', 'clk'],
    'ad_feature': ['adgroup_id', 'cate_id', 'campaign_id', 'customer', 'brand', 'price'],
    'user_profile': ['userid', 'cms_segid', 'cms_group_id', 'final_gender_code',
                     'age_level', 'pvalue_level', 'shopping_level', 'occupation', 'new_user_class_level'],
}

DEFAULT_START = '2017-05-06'
DEFAULT_END = '2017-05-13'

def business_period(start=DEFAULT_START, end=DEFAULT_END):
    if (datetime.date.fromisoformat(start).isoformat() != start or
            datetime.date.fromisoformat(end).isoformat() != end or start > end):
        raise ValueError('业务日期必须是有效YYYY-MM-DD，且开始日期不晚于结束日期')
    return {'start_date':start, 'end_date':end, 'timezone':'Asia/Shanghai'}

def normalized_header(header, expected):
    # Only the documented user-profile spelling is accepted as an alias.
    aliases = {'new_user_class_level ': 'new_user_class_level'}
    normalized = [aliases.get(value, value) for value in (header or [])]
    if normalized != expected:
        raise ValueError(f'表头不符：{header!r}；预期 {expected!r}')
    return normalized

def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def stage_file(source, target, expected):
    source, target = Path(source), Path(target)
    if target.exists():
        raise ValueError(f'输出已存在，拒绝覆盖：{target}')
    if any(c in source.name for c in '\t\r\n\\'):
        raise ValueError('源文件名包含不支持的分隔符')
    before = source.stat()
    digest = hashlib.sha256()
    # Read in bounded chunks; retain a source checksum for later independent checks.
    with source.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    rows = 0
    created = False
    try:
        out_stream = target.open('x', encoding='utf-8', newline='')
        created = True
        with source.open(encoding='utf-8-sig', newline='') as stream, out_stream as out:
            reader = csv.reader(stream, strict=True)
            header = next(reader, None)
            normalized_header(header, expected)
            previous_line = reader.line_num
            for row in reader:
                source_line = previous_line + 1
                if reader.line_num != source_line:
                    raise ValueError(f'{source.name}:{source_line} 含跨行字段，需单独处理')
                if len(row) != len(expected):
                    raise ValueError(f'{source.name}:{source_line} 字段数量错误')
                if any(any(c in value for c in '\t\r\n\\') for value in row):
                    raise ValueError(f'{source.name}:{source_line} 含不支持的TSV控制字符或反斜杠')
                out.write('\t'.join([source.name, str(source_line), *row]) + '\n')
                rows += 1
                previous_line = reader.line_num
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('读取期间源文件发生变化，停止使用结果')
    except BaseException:
        # Only remove the partial output created by this call, never source data.
        if created and target.exists():
            target.unlink()
        raise
    return {'source_file': source.name, 'source_bytes': before.st_size,
            'sha256': digest.hexdigest(), 'rows': rows, 'header': expected,
            'source_header': header, 'normalized_header': expected,
            'staged_file': target.name, 'staged_bytes': target.stat().st_size,
            'staged_sha256': file_sha256(target)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='新建输出目录，不覆盖已有批次')
    parser.add_argument('--start-date', default=DEFAULT_START)
    parser.add_argument('--end-date', default=DEFAULT_END)
    args = parser.parse_args()
    try:
        period = business_period(args.start_date, args.end_date)
    except ValueError as error:
        parser.error(str(error))
    sources = {name: args.source / (name + '.csv') for name in HEADERS}
    missing = [str(p) for p in sources.values() if not p.is_file()]
    if missing:
        parser.error('缺少主体文件：' + ', '.join(missing))
    args.out.mkdir(parents=True, exist_ok=False)
    results = []
    for name, header in HEADERS.items():
        results.append(stage_file(sources[name], args.out / (name + '.tsv'), header))
    # This manifest is the completion marker. Never load a batch without it.
    manifest = {'kind': 'full_csv_staging', 'sampled': False, 'files': results,
                'business_period':period,
                'technical_validation': (args.source / 'TECHNICAL_FIXTURE_ONLY').exists()}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
