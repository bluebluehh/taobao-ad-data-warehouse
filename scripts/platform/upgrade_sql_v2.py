#!/usr/bin/env python3
"""Apply additive reporting schema only on the handed-over adw101 metadata instance."""
from pathlib import Path
import socket
import subprocess

ROOT=Path(__file__).resolve().parents[2]

def main():
    if socket.gethostname().split('.')[0]!='adw101':
        raise SystemExit('仅在adw101执行；两台工作节点不创建MySQL报表表')
    if Path('/etc/taobao-clone-identity').read_text().strip()!='adw101':
        raise SystemExit('主节点交付身份不符')
    subprocess.run(['systemctl','--user','start','taobao-node-mysql'],check=True)
    base=Path('/opt/taobao/data/reporting')
    client=Path('/opt/taobao/module/mysql-ubuntu-8.0.46/usr/bin/mysql')
    command=[str(client),'--defaults-file='+str(base/'admin.cnf')]
    port,data=subprocess.check_output(command+['-N','-e','SELECT @@port,@@datadir'],text=True).strip().split('\t')
    if port!='3307' or Path(data).resolve()!=(base/'mysql-data').resolve():
        raise SystemExit('数据库目标不符，停止')
    sql=(ROOT/'sql/mysql/report_schema.sql').read_text()
    for database in ['taobao_reports','taobao_reports_validation']:
        subprocess.run(command+[database],input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
    print('SQL v2报表扩展已就绪；保留原数据、凭据和HDFS，不执行格式化。')
if __name__=='__main__':main()
