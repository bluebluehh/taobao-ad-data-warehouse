#!/usr/bin/env python3
"""Initialize an empty adw101 metastore, then validate; never reset an existing schema."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

sys.path.insert(0, '/opt/taobao/module/python-libs')


def main():
    if socket.gethostname().split('.')[0] != 'adw101':
        raise SystemExit('仅允许在adw101运行')
    import pymysql
    base = Path('/opt/taobao')
    credentials = json.loads((base/'data/reporting/credentials.json').read_text())
    with pymysql.connect(unix_socket=str(base/'data/reporting/mysql.sock'),
                         user='hive_metastore', password=credentials['hive_metastore'],
                         database='hive_metastore') as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()')
            empty = cur.fetchone()[0] == 0
    logs = base/'checks/master-metadata'
    logs.mkdir(mode=0o700, exist_ok=True)
    actions = ['-initSchema', '-validate'] if empty else ['-validate']
    for action in actions:
        name = action.lstrip('-')
        # Load only the machine-local environment; no secrets are passed on the command line.
        with (logs/(name+'.log')).open('w') as out:
            result = subprocess.run(['bash', '-c', 'source /opt/taobao/node-env.sh; exec schematool -dbType mysql "$1"',
                                     'schematool', action], stdout=out, stderr=subprocess.STDOUT, timeout=180)
        if result.returncode:
            raise SystemExit('Hive元数据'+name+'未通过；检查节点内日志：'+str(logs/(name+'.log')))
        print('Hive元数据'+name+'通过')
    (logs/'SUCCESS').write_text('Hive metastore initialized/validated; HDFS not initialized\n')


if __name__ == '__main__':
    main()
