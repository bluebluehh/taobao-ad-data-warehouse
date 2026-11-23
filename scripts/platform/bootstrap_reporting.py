#!/usr/bin/env python3
"""Provision application accounts and schemas only in the isolated port-3307 MySQL instance."""
import json
import os
from pathlib import Path
import secrets
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BASE=Path('/opt/taobao/data/reporting')

def private_file(path,text):
    if not path.exists():
        with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as out:out.write(text)

def main():
    c=json.loads((BASE/'credentials.json').read_text())
    if 'scheduler_meta' not in c:
        c['scheduler_meta']=secrets.token_urlsafe(32)
        (BASE/'credentials.json').write_text(json.dumps(c,indent=2));(BASE/'credentials.json').chmod(0o600)
    admin=BASE/'admin.cnf'
    private_file(admin,'[client]\nuser=root\npassword='+c['mysql_root']+'\nsocket='+str(BASE/'mysql.sock')+'\n')
    command=['mysql','--defaults-file='+str(admin)]
    check=subprocess.run(command+['-N','-e','SELECT @@port,@@datadir'],text=True,capture_output=True)
    if check.returncode:
        if (BASE/'bootstrap.complete').exists():raise SystemExit('已有账号初始化记录，但管理员连接失败；停止，不重设密码。')
        subprocess.run(['mysql','--no-defaults','--protocol=SOCKET','--socket='+str(BASE/'mysql.sock'),'-uroot'],
            input="ALTER USER 'root'@'localhost' IDENTIFIED BY '"+c['mysql_root']+"';",text=True,check=True)
        check=subprocess.run(command+['-N','-e','SELECT @@port,@@datadir'],text=True,capture_output=True,check=True)
    port,data=check.stdout.strip().split('\t')
    if port!='3307' or Path(data).resolve()!=(BASE/'mysql-data').resolve():raise SystemExit('连接对象不是本项目独立报表MySQL，停止。')
    sql=''
    for database in ['taobao_reports','taobao_reports_validation','superset_meta','dolphinscheduler_meta']:
        sql+=f'CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;\n'
    for user in ['report_writer','report_reader','superset_meta','scheduler_meta']:
        sql+=f"CREATE USER IF NOT EXISTS '{user}'@'127.0.0.1' IDENTIFIED BY '{c[user]}';\n"
    for database in ['taobao_reports','taobao_reports_validation']:
        sql+=f"GRANT SELECT,INSERT,UPDATE,DELETE ON {database}.* TO 'report_writer'@'127.0.0.1';\n"
        sql+=f"GRANT SELECT,SHOW VIEW ON {database}.* TO 'report_reader'@'127.0.0.1';\n"
    for database,user in [('superset_meta','superset_meta'),('dolphinscheduler_meta','scheduler_meta')]:
        sql+=f"GRANT ALL PRIVILEGES ON {database}.* TO '{user}'@'127.0.0.1';\n"
    subprocess.run(command,input=sql,text=True,check=True)
    for database in ['taobao_reports','taobao_reports_validation']:
        subprocess.run(command+[database],input=(ROOT/'sql/mysql/report_schema.sql').read_text(),text=True,check=True)
    private_file(BASE/'scheduler-client.cnf','[client]\nuser=scheduler_meta\npassword='+c['scheduler_meta']+'\nhost=127.0.0.1\nport=3307\nprotocol=TCP\n')
    scheduler=['mysql','--defaults-file='+str(BASE/'scheduler-client.cnf'),'dolphinscheduler_meta']
    count=int(subprocess.check_output(scheduler+['-N','-e','SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()'],text=True).strip())
    if count==0:
        schema=Path('/opt/taobao/module/apache-dolphinscheduler-3.3.2-bin/standalone-server/conf/sql/dolphinscheduler_mysql.sql')
        # The upstream script contains DROP TABLE statements. It is only permitted in this verified EMPTY, dedicated schema.
        subprocess.run(scheduler,input=schema.read_text(),text=True,check=True,stdout=subprocess.DEVNULL)
    private_file(BASE/'superset-login.txt','本机 Superset\n地址：http://127.0.0.1:8089/\n用户名：admin\n密码：'+c['superset_admin']+'\n')
    (BASE/'bootstrap.complete').write_text('Independent MySQL accounts provisioned; existing MariaDB untouched.\n')
    print('独立MySQL账号、报表视图与元数据库检查通过；已有业务数据和调度记录保留。')

if __name__=='__main__':main()
