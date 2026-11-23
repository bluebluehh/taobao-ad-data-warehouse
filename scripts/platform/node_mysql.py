#!/usr/bin/env python3
"""Manage the fresh adw101 MySQL instance; never connect to the development database."""
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time

sys.path.insert(0, '/opt/taobao/module/python-libs')
BASE = Path('/opt/taobao/data/reporting')


def main(action):
    if socket.gethostname().split('.')[0] != 'adw101':
        raise SystemExit('仅允许在adw101运行')
    import pymysql
    cpath = BASE/'credentials.json'
    credentials = json.loads(cpath.read_text())
    options = dict(unix_socket=str(BASE/'mysql.sock'), user='root', connect_timeout=3, autocommit=True)
    if action == 'bootstrap':
        connection = None
        for _ in range(30):
            try:
                connection = pymysql.connect(**options, password=credentials['mysql_root'])
                break
            except pymysql.err.OperationalError as error:
                if error.args[0] == 1045:
                    if (BASE/'node-bootstrap.complete').exists():
                        raise SystemExit('已初始化实例认证失败，停止，不重设密码')
                    connection = pymysql.connect(**options, password='')
                    with connection.cursor() as cur:
                        cur.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (credentials['mysql_root'],))
                    break
                time.sleep(1)
        if connection is None:
            raise SystemExit('数据库未在30秒内就绪')
    else:
        connection = pymysql.connect(**options, password=credentials['mysql_root'])
    with connection:
        with connection.cursor() as cur:
            cur.execute('SELECT @@port, @@datadir')
            port, data = cur.fetchone()
            if port != 3307 or Path(data).resolve() != (BASE/'mysql-data').resolve():
                raise SystemExit('数据库对象不符，停止')
            if action == 'shutdown':
                cur.execute('SHUTDOWN')
                return
            if action == 'bootstrap':
                if 'hive_metastore' not in credentials:
                    credentials['hive_metastore'] = secrets.token_urlsafe(32)
                    # Save credentials before creating accounts, so an interruption can resume.
                    with cpath.open('w') as out:
                        json.dump(credentials, out, indent=2)
                    cpath.chmod(0o600)
                cur.execute('CREATE DATABASE IF NOT EXISTS hive_metastore CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
                for host in ['localhost', '127.0.0.1']:
                    cur.execute('CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s', ('hive_metastore', host, credentials['hive_metastore']))
                    cur.execute('GRANT ALL PRIVILEGES ON hive_metastore.* TO %s@%s', ('hive_metastore', host))
                admin = BASE/'admin.cnf'
                if not admin.exists():
                    with os.fdopen(os.open(admin, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'w') as out:
                        out.write('[client]\nuser=root\npassword='+credentials['mysql_root']+'\nsocket='+str(BASE/'mysql.sock')+'\n')
                (BASE/'node-bootstrap.complete').write_text('adw101 fresh private instance; Hive account provisioned\n')
            cur.execute('SELECT VERSION(), @@port')
            print('adw101 MySQL连接检查通过：', cur.fetchone())


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ['bootstrap', 'check', 'shutdown']:
        raise SystemExit('使用：node_mysql.py bootstrap|check|shutdown')
    main(sys.argv[1])
