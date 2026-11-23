#!/usr/bin/env python3
"""Initialize ONLY the new rootless MySQL reporting instance. Never touch existing MariaDB."""
import json
import os
from pathlib import Path
import secrets
import subprocess

BASE = Path('/opt/taobao/data/reporting')
MYSQL = Path('/opt/taobao/module/mysql-ubuntu-8.0.46/usr')

def private_file(path, value):
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as out:
        out.write(value)

def main():
    BASE.mkdir(mode=0o700,exist_ok=True)
    for name in ['mysql-data','tmp','exports']:(BASE/name).mkdir(mode=0o700,exist_ok=True)
    credential_path=BASE/'credentials.json'
    if not credential_path.exists():
        credentials={name:secrets.token_urlsafe(32) for name in ['mysql_root','report_writer','report_reader','superset_meta','superset_secret','superset_admin']}
        private_file(credential_path,json.dumps(credentials,indent=2))
    conf=BASE/'mysql.cnf'
    if not conf.exists():
        private_file(conf,f'''[mysqld]
basedir={MYSQL}
datadir={BASE}/mysql-data
socket={BASE}/mysql.sock
port=3307
bind-address=127.0.0.1
mysqlx=0
pid-file={BASE}/mysql.pid
log-error={BASE}/mysql-error.log
tmpdir={BASE}/tmp
secure-file-priv={BASE}/exports
plugin-dir={MYSQL}/lib/mysql/plugin
lc-messages-dir={MYSQL}/share/mysql
innodb-buffer-pool-size=64M
innodb-log-buffer-size=8M
performance-schema=OFF
max-connections=30
skip-name-resolve
skip-log-bin
character-set-server=utf8mb4
collation-server=utf8mb4_bin
''')
    data=BASE/'mysql-data'
    if (data/'auto.cnf').exists():
        print('已有MySQL身份，跳过初始化；是否完整可用仍需连接验证。');return
    if any(data.iterdir()):raise SystemExit('MySQL目录非空但缺少身份文件，拒绝覆盖或重新初始化')
    env=os.environ.copy();env['LD_LIBRARY_PATH']=str(MYSQL/'lib/x86_64-linux-gnu')
    subprocess.run([str(MYSQL/'sbin/mysqld'),'--defaults-file='+str(conf),'--initialize-insecure'],env=env,check=True)
    print('独立MySQL目录初始化完成；凭据只保存于机器私有目录，尚未完成账号配置。')

if __name__=='__main__':main()
