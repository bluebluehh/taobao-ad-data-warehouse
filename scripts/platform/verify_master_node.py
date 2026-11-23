#!/usr/bin/env python3
"""Read-only/API checks for the prepared adw101 node, with a credential-free receipt."""
import json
from pathlib import Path
import socket
import sys
import time
import urllib.request

sys.path.insert(0, '/opt/taobao/module/python-libs')
from scheduler_api import Scheduler


def main():
    if socket.gethostname().split('.')[0] != 'adw101':
        raise SystemExit('仅允许在adw101运行')
    import pymysql
    # User services report active while the applications are still warming up.
    deadline = time.monotonic() + 180
    for port in [8089, 12345]:
        while True:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise SystemExit('应用端口尚未就绪：'+str(port))
                time.sleep(2)
    base = Path('/opt/taobao')
    secret = json.loads((base/'data/reporting/credentials.json').read_text())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request('http://127.0.0.1:8089/api/v1/security/login',
        data=json.dumps({'username': 'admin', 'password': secret['superset_admin'], 'provider': 'db'}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with opener.open(request, timeout=30) as response:
        token = json.load(response)['access_token']
    request = urllib.request.Request('http://127.0.0.1:8089/api/v1/me/', headers={'Authorization': 'Bearer '+token})
    with opener.open(request, timeout=30) as response:
        assert json.load(response)['result']['username'] == 'admin'
    Scheduler().call('/users/get-user-info')
    with pymysql.connect(unix_socket=str(base/'data/reporting/mysql.sock'), user='root',
                         password=secret['mysql_root']) as connection:
        with connection.cursor() as cur:
            cur.execute('SELECT VERSION(), @@port')
            version, port = cur.fetchone()
            assert port == 3307
            cur.execute('SELECT SCHEMA_VERSION FROM hive_metastore.VERSION')
            schema_version = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM hive_metastore.TBLS')
            hive_tables = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM dolphinscheduler_meta.t_ds_workflow_definition')
            workflows = cur.fetchone()[0]
    for directory in ['cluster-data', 'data/hadoop']:
        assert not (base/directory).exists(), '不应有HDFS状态：'+directory
    result = {'node': 'adw101', 'mysql_version': version, 'mysql_port': port,
        'hive_schema_version': schema_version, 'hive_tables': hive_tables,
        'superset_admin_api_login': 'passed', 'scheduler_admin_api_login': 'passed',
        'scheduler_workflows': workflows, 'hdfs': 'not_initialized',
        'cluster_network': 'not_yet_validated', 'real_data_analysis': 'not_started'}
    path = base/'checks/master-metadata/platform-check.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
