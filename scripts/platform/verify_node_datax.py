#!/usr/bin/env python3
"""Run three synthetic stream rows only; this does not import warehouse data."""
import json
from pathlib import Path
import re
import socket
import subprocess


def main():
    if socket.gethostname().split('.')[0] != 'adw101':
        raise SystemExit('仅允许在adw101运行')
    folder = Path('/opt/taobao/checks/master-metadata')
    job = folder/'datax-technical-stream.json'
    job.write_text(json.dumps({'job': {'setting': {'speed': {'channel': 1}}, 'content': [{
        'reader': {'name': 'streamreader', 'parameter': {'column': [
            {'type': 'long', 'value': '1'}, {'type': 'string', 'value': 'technical_only'}], 'sliceRecordCount': 3}},
        'writer': {'name': 'streamwriter', 'parameter': {'print': True, 'encoding': 'UTF-8'}},
    }]}}, indent=2)+'\n')
    with (folder/'datax-technical-stream.log').open('w') as out:
        result = subprocess.run(['bash', '-c', 'source /opt/taobao/node-env.sh; exec python3 /opt/taobao/module/datax/bin/datax.py --jvm="-Xms128m -Xmx256m" "$1"',
                                 'datax', str(job)], stdout=out, stderr=subprocess.STDOUT, timeout=120)
    log = (folder/'datax-technical-stream.log').read_text()
    if result.returncode or not re.search(r'读出记录总数\s*:\s*3\b', log) or not re.search(r'读写失败总数\s*:\s*0\b', log):
        raise SystemExit('DataX技术自检未通过，检查节点内日志')
    (folder/'datax-result.json').write_text(json.dumps({'kind': 'synthetic_stream_check', 'rows': 3, 'errors': 0})+'\n')
    print('DataX技术自检通过：3条人工流记录，0条失败；未导入业务数据。')


if __name__ == '__main__':
    main()
