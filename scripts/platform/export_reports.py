#!/usr/bin/env python3
"""Publish a successful Hive batch through DataX, reconcile rows, then expose it to reports."""
import argparse
import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import pymysql

ROOT=Path(__file__).resolve().parents[2]
PRIVATE=Path('/opt/taobao/data/reporting')
TABLES={
 'daily_overview': [('impressions','long'),('clicks','long'),('ctr','double'),('reached_users','long'),('clicked_users','long'),('user_click_ratio','double'),('ad_units','long'),('impressions_per_user','double'),('unmatched_profiles','long'),('unmatched_ads','long'),('batch_id','string'),('dt','string')],
 'daily_axis': [('axis','string'),('axis_value','string'),('impressions','long'),('clicks','long'),('ctr','double'),('reached_users','long'),('clicked_users','long'),('user_click_ratio','double'),('ad_units','long'),('impressions_per_user','double'),('impression_share','double'),('click_share','double'),('batch_id','string'),('dt','string')],
 'daily_quality': [('impressions', 'long'), ('matched_profile_impressions', 'long'), ('reached_users', 'long'), ('matched_profile_users', 'long'), ('matched_ad_impressions', 'long'), ('gender_missing', 'long'), ('age_missing', 'long'), ('shopping_missing', 'long'), ('pvalue_missing', 'long'), ('occupation_missing', 'long'), ('city_missing', 'long'), ('profile_row_coverage', 'double'), ('profile_user_coverage', 'double'), ('ad_row_coverage', 'double'), ('gender_missing_rate', 'double'), ('age_missing_rate', 'double'), ('shopping_missing_rate', 'double'), ('pvalue_missing_rate', 'double'), ('occupation_missing_rate', 'double'), ('city_missing_rate', 'double'), ('batch_id', 'string'), ('dt', 'string')]
}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-record',type=Path,required=True,help='run_batch.py generated success.json')
    args=parser.parse_args()
    record=json.loads(args.run_record.read_text());ns=record['namespace'];batch=record['batch_id']
    if record.get('sql_revision')!=2:parser.error('仅发布SQL v2完整成功回执；旧批次请保留并以新批次重算')
    if not re.fullmatch(r'taobao|validation_[a-z0-9_]+',ns) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',batch):
        parser.error('批次或命名空间格式不符')
    namespace_lock=(ROOT/'output'/('.namespace-'+ns+'.lock')).open('a')
    fcntl.flock(namespace_lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
    target='taobao_reports_validation' if ns.startswith('validation_') else 'taobao_reports'
    secret=json.loads((PRIVATE/'credentials.json').read_text())
    report=Path(tempfile.mkdtemp(prefix='report-export-',dir=ROOT/'output'))
    env=os.environ.copy()
    env.update(dict(x.decode().split('=',1) for x in subprocess.check_output(['bash','-c','source "$1"; env -0','bash',str(ROOT/'scripts/platform/env.sh')]).split(b'\0') if b'=' in x))
    completed_path=f'/warehouse/{ns}/processing/{batch}/success.json'
    completed=json.loads(subprocess.check_output(['hdfs','dfs','-cat',completed_path],env=env,stderr=subprocess.DEVNULL))
    if not record.get('run_id') or completed.get('run_id')!=record['run_id']:
        raise ValueError('不是批次当前完整成功回执，停止发布')
    default_fs=subprocess.check_output(['hdfs','getconf','-confKey','fs.defaultFS'],env=env,text=True).strip()
    if not default_fs.startswith('hdfs://'):raise ValueError('当前配置不是HDFS地址，停止导出')
    export_root=f'/warehouse/{ns}/report_exports/{batch}'
    sql=['SET hive.execution.engine=tez;','SET hive.tez.container.size=512;','SET hive.tez.java.opts=-Xmx384m;']
    for table,columns in TABLES.items():
        sql.append(f"INSERT OVERWRITE DIRECTORY '{export_root}/{table}' ROW FORMAT DELIMITED FIELDS TERMINATED BY '\\t' STORED AS TEXTFILE SELECT "+','.join(c for c,t in columns)+f" FROM {ns}_ads.{table} WHERE batch_id='{batch}';")
    query=report/'export.sql';query.write_text('\n'.join(sql))
    with (report/'hive-export.log').open('w') as log:
        subprocess.run(['beeline','--force=false','-u','jdbc:hive2://','-f',str(query)],env=env,stdout=log,stderr=log,check=True,timeout=600)
    jobs=PRIVATE/'datax-jobs';jobs.mkdir(mode=0o700,exist_ok=True)
    connection=pymysql.connect(host='127.0.0.1',port=3307,user='report_writer',password=secret['report_writer'],database=target,charset='utf8mb4',autocommit=False)
    try:
        results={}
        for table,columns in TABLES.items():
            job={'job':{'setting':{'speed':{'channel':1},'errorLimit':{'record':0,'percentage':0.0}},'content':[{
              'reader':{'name':'hdfsreader','parameter':{'path':export_root+'/'+table+'/*','defaultFS':default_fs,'fileType':'text','encoding':'UTF-8','column':[{'index':i,'type':t} for i,(c,t) in enumerate(columns)],'fieldDelimiter':'\t','nullFormat':'\\N'}},
              'writer':{'name':'mysqlwriter','parameter':{'username':'report_writer','password':secret['report_writer'],'column':[c for c,t in columns],'writeMode':'update','batchSize':1000,'connection':[{'jdbcUrl':f'jdbc:mysql://127.0.0.1:3307/{target}?useUnicode=true&characterEncoding=UTF-8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai','table':[table]}]}}
            }]}}
            path=jobs/f'{ns}-{batch}-{table}.json'
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as out:json.dump(job,out,ensure_ascii=False)
            with (report/(table+'-datax.log')).open('w') as log:
                proc=subprocess.Popen(['python3','/opt/taobao/module/datax/bin/datax.py','--jvm=-Xms64m -Xmx256m',str(path)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                for line in proc.stdout:
                    log.write(line.replace(secret['report_writer'],'[REDACTED]'))
                if proc.wait()!=0:raise RuntimeError(table+' DataX同步失败，未发布批次')
            raw=subprocess.check_output(['hdfs','dfs','-cat',export_root+'/'+table+'/*'],env=env,text=True)
            expected=[]
            for line in raw.splitlines():
                values=line.split('\t')
                if len(values)!=len(columns):raise ValueError('导出字段数错误')
                expected.append(tuple(None if v=='\\N' else int(v) if t=='long' else float(v) if t=='double' else v for v,(c,t) in zip(values,columns)))
            # DataX writes through other connections. End any previous REPEATABLE READ snapshot before checking.
            connection.commit()
            with connection.cursor() as cursor:
                cursor.execute('SELECT '+','.join(c for c,t in columns)+' FROM '+table+' WHERE batch_id=%s',(batch,))
                actual=cursor.fetchall()
            def key(row):return tuple('' if v is None else str(v) for v in row)
            expected.sort(key=key);actual=sorted(actual,key=key)
            if len(expected)!=len(actual):raise RuntimeError(table+'同步记录数不一致')
            for left,right in zip(expected,actual):
                for a,b in zip(left,right):
                    if isinstance(a,float):
                        if b is None or not math.isclose(a,float(b),rel_tol=1e-10,abs_tol=1e-12):raise RuntimeError(table+'浮点指标不一致')
                    elif a is None:
                        if b is not None:raise RuntimeError(table+'空值不一致')
                    elif str(a)!=str(b):raise RuntimeError(table+'字段值不一致')
            results[table]={'rows':len(actual),'all_fields_reconciled':True}
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO published_batches(batch_id,source_namespace) VALUES(%s,%s) ON DUPLICATE KEY UPDATE source_namespace=VALUES(source_namespace),published_at=CURRENT_TIMESTAMP',(batch,ns))
        connection.commit()
        result={'batch_id':batch,'namespace':ns,'target_database':target,'technical_validation':ns.startswith('validation_'),'tables':results,'published':True,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        (report/'success.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False,indent=2));print('运行记录：',report)
    finally:connection.close()

if __name__=='__main__':main()
