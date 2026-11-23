#!/usr/bin/env python3
"""Download the official Ubuntu package, checking signed metadata and SHA256."""
import gzip
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.request

BASE = 'https://pkgs.tailscale.com/stable/'
OUT = Path('/opt/taobao/software/tailscale-offline')


def download(url, path, expected=None, size=None):
    if expected and path.exists() and digest(path) == expected:
        return
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    temporary = path.with_name(path.name+'.part')
    if size and size > 10*1024*1024:
        existing = temporary.stat().st_size if temporary.exists() else 0
        assert existing <= size
        remaining = size-existing
        chunk_size = max(1, (remaining+5)//6)
        segments = [(start, min(start+chunk_size, size)-1) for start in range(existing, size, chunk_size)]
        def fetch_segment(bounds):
            start, end = bounds
            segment = path.with_name(path.name+'.range.'+str(start))
            request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
            with opener.open(request, timeout=30) as response, segment.open('wb') as output:
                assert response.status == 206 and response.headers.get('Content-Range') == f'bytes {start}-{end}/{size}'
                while block := response.read(256*1024):
                    output.write(block)
            assert segment.stat().st_size == end-start+1
            return segment
        with ThreadPoolExecutor(max_workers=6) as pool:
            parts = list(pool.map(fetch_segment, segments))
        with temporary.open('ab') as output:
            for part in parts:
                with part.open('rb') as source:
                    while block := source.read(1024*1024):
                        output.write(block)
                part.unlink()
        assert temporary.stat().st_size == size and digest(temporary) == expected, '安装包校验失败'
        temporary.replace(path)
        return
    with opener.open(url, timeout=30) as response, temporary.open('wb') as output:
        while block := response.read(1024*1024):
            output.write(block)
    temporary.replace(path)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = OUT/'tailscale-archive-keyring.gpg'
    release = OUT/'Release'
    download(BASE+'ubuntu/noble.noarmor.gpg', key)
    download(BASE+'ubuntu/dists/noble/InRelease', OUT/'InRelease')
    release.unlink(missing_ok=True)
    subprocess.run(['gpgv', '--keyring', str(key), '--output', str(release), str(OUT/'InRelease')], check=True)
    checksums = {}
    in_section = False
    for line in release.read_text().splitlines():
        if line == 'SHA256:':
            in_section = True
        elif in_section:
            match = re.fullmatch(r'\s+([0-9a-f]{64})\s+(\d+)\s+(\S+)', line)
            if match:
                checksums[match[3]] = (match[1], int(match[2]))
            else:
                in_section = False
    index_name = 'main/binary-amd64/Packages.gz'
    expected, size = checksums[index_name]
    index = OUT/'Packages.gz'
    download(BASE+'ubuntu/dists/noble/'+index_name, index)
    assert index.stat().st_size == size and digest(index) == expected, '软件包索引校验失败'
    candidates = []
    for paragraph in gzip.decompress(index.read_bytes()).decode().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        if fields.get('Package') == 'tailscale' and fields.get('Architecture') == 'amd64':
            candidates.append(fields)
    assert candidates, '未找到amd64软件包'
    versions = subprocess.check_output(['sort', '-V'], input='\n'.join(p['Version'] for p in candidates)+'\n', text=True).splitlines()
    package = next(p for p in candidates if p['Version'] == versions[-1])
    filename = PurePosixPath(package['Filename'])
    assert not filename.is_absolute() and '..' not in filename.parts and str(filename).startswith('pool/')
    target = OUT/filename.name
    url = BASE+'ubuntu/'+str(filename)
    download(url, target, expected=package['SHA256'], size=int(package['Size']))
    assert target.stat().st_size == int(package['Size']) and digest(target) == package['SHA256'], '安装包校验失败'
    arch = subprocess.check_output(['dpkg-deb', '-f', str(target), 'Architecture'], text=True).strip()
    assert arch == 'amd64'
    manifest = {'package': 'tailscale', 'version': package['Version'], 'architecture': arch,
        'file': target.name, 'url': url, 'sha256': package['SHA256'],
        'release_signature': 'verified_with_official_https_repository_key',
        'key_sha256': digest(key), 'index_sha256': expected, 'depends': package.get('Depends', '')}
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (OUT/'SHA256SUMS').write_text(package['SHA256']+'  '+target.name+'\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
