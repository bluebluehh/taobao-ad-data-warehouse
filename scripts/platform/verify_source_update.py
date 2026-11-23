#!/usr/bin/env python3
"""Read-only source comparison against a delivery ZIP; optionally run local tool tests."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import socket
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'taobao-ad-warehouse/'


def compare(root, archive_path):
    root = root.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('ZIP包含重复文件名')
        hashes = json.loads(archive.read('SOURCE_FILES_SHA256.json'))
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError('源码哈希清单为空或格式错误')
        actual_sources = {name for name in names if name.startswith(PREFIX) and not name.endswith('/')}
        if actual_sources != set(hashes):
            raise ValueError('ZIP源码与哈希清单不一致')
        differences = []
        for name, digest in sorted(hashes.items()):
            relative = name.removeprefix(PREFIX)
            parts = PurePosixPath(relative).parts
            if (not name.startswith(PREFIX) or not parts or relative.startswith('/')
                    or '..' in parts or '\\' in relative
                    or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
                raise ValueError('非法清单路径或哈希')
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError('ZIP源码哈希不符：'+name)
            path = root.joinpath(*parts)
            if not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in [path, *path.parents] if p != root):
                differences.append({'path': relative, 'status': 'unsafe_path'})
            elif not path.is_file():
                differences.append({'path': relative, 'status': 'missing'})
            elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                differences.append({'path': relative, 'status': 'changed'})
        return {'expected_files': len(hashes), 'source_matches': not differences, 'differences': differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True, help='负责人通过独立渠道提供的ZIP SHA256')
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--run-tests', action='store_true')
    args = parser.parse_args()
    # Receipts and logs must stay outside the versioned source tree.
    output = (ROOT/'output').resolve()
    if not args.receipt.resolve().is_relative_to(output):
        parser.error('--receipt必须位于项目output目录')
    if args.receipt.exists():
        parser.error('回执已存在，请使用新的文件名')
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'hostname': socket.gethostname(),
              'scope': 'local_source_and_tool_tests_only', 'cluster_runtime_verified': False,
              'real_data_accepted': False, 'local_tests': 'not_run'}
    try:
        result['archive_sha256'] = hashlib.sha256(args.archive.read_bytes()).hexdigest()
        if result['archive_sha256'] != args.expected_sha256.lower():
            raise ValueError('交付包SHA256与指定值不符')
        result.update(compare(ROOT, args.archive))
        if result['source_matches'] and args.run_tests:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            log = args.receipt.with_suffix('.tests.log')
            with log.open('x') as stream:
                run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
                                     cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
            result.update(local_tests='passed' if run.returncode == 0 else 'failed', test_log=str(log))
        result['passed'] = result['source_matches'] and (not args.run_tests or result['local_tests'] == 'passed')
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        result.update(passed=False, error=str(error))
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
