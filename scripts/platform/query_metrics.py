#!/usr/bin/env python3
"""Exact, filtered period/combination queries, with optional atomic MySQL scope publication."""
import argparse
import csv
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from metric_queries import build_queries, METRICS, QUALITY_COUNTS, QUALITY_RATES

ROOT=Path(__file__).resolve().parents[2]
AXIS_LABELS={'hour':'小时','pid':'展示位置','adgroup':'广告单元','campaign':'活动编码',
 'customer':'广告主编码','category':'类目编码','brand':'品牌编码','gender':'性别编码',
 'age':'年龄等级','shopping':'购物等级','pvalue':'消费档次','occupation':'occupation编码','city':'城市等级'}
MISSING_LABELS={'__unmatched_profile__':'画像未匹配','__unmatched_ad__':'广告未匹配',
 '__missing_attribute__':'属性缺失'}


def read_rows(text):
    reader=csv.DictReader(io.StringIO(text),delimiter='\t')
    if not reader.fieldnames:raise ValueError('Hive未返回查询表头')
    rows=[]
    integers=set(QUALITY_COUNTS)|{'impressions','clicks','reached_users','clicked_users','ad_units'}
    numbers=set(METRICS)|set(QUALITY_RATES)|{'impression_share','click_share'}
    for record in reader:
        row={}
        for name,value in record.items():
            name=name.split('.')[-1]
            if value is None:raise ValueError('Hive返回字段数不符')
            if value in ['NULL','null',r'\N']:row[name]=None
            elif name in integers:row[name]=int(value)
            elif name in numbers:row[name]=float(value)
            else:row[name]=value
        rows.append(row)
    return rows

def publish(result):
    import pymysql
    private=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
    context=result['request']
    database='taobao_reports' if context['namespace']=='taobao' else 'taobao_reports_validation'
    request_id=result['request_id']
    with pymysql.connect(host='127.0.0.1',port=3307,user='report_writer',password=private['report_writer'],
                         database=database,charset='utf8mb4',autocommit=False) as connection:
        try:
            with connection.cursor() as cursor:
                expected_rows={}
                for table in ['analysis_overview','analysis_quality','analysis_groups']:
                    cursor.execute('DELETE FROM '+table+' WHERE request_id=%s',(request_id,))
                def insert(table,values):
                    expected_rows.setdefault(table,[]).append(values)
                    columns=list(values)
                    cursor.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join(['%s']*len(columns))+')',
                                   tuple(values[column] for column in columns))
                insert('analysis_overview',{'request_id':request_id,**result['overview']})
                insert('analysis_quality',{'request_id':request_id,**result['quality']})
                for row in result['groups']:
                    group={axis:row['group_value_'+str(i+1)] for i,axis in enumerate(context['axes'])}
                    group_json=json.dumps(group,ensure_ascii=False,sort_keys=True)
                    values={key:row[key] for key in METRICS+['impression_share','click_share']}
                    insert('analysis_groups',{'request_id':request_id,
                        'group_key':hashlib.sha256(group_json.encode()).hexdigest(),
                        'group_label':' | '.join(AXIS_LABELS[axis]+'='+MISSING_LABELS.get(group[axis],str(group[axis])) for axis in context['axes']),
                        'group_values':group_json,**values})
                cursor.execute('''INSERT INTO analysis_scopes
                    (request_id,batch_id,source_namespace,start_date,end_date,request_json)
                    VALUES(%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE
                    request_json=VALUES(request_json),published_at=CURRENT_TIMESTAMP''',
                    (request_id,context['batch_id'],context['namespace'],context['start_date'],context['end_date'],
                     json.dumps(context,ensure_ascii=False)))
                for table,count in [('analysis_overview',1),('analysis_quality',1),('analysis_groups',len(result['groups']))]:
                    cursor.execute('SELECT COUNT(*) FROM '+table+' WHERE request_id=%s',(request_id,))
                    if cursor.fetchone()[0]!=count:raise ValueError('分析范围发布计数不符')
                for table,rows in expected_rows.items():
                    columns=list(rows[0])
                    cursor.execute('SELECT '+','.join(columns)+' FROM '+table+' WHERE request_id=%s',(request_id,))
                    actual_rows=[dict(zip(columns,row)) for row in cursor.fetchall()]
                    by_key={row.get('group_key','overview'):row for row in actual_rows}
                    for expected in rows:
                        actual=by_key[expected.get('group_key','overview')]
                        for column,value in expected.items():
                            observed=actual[column]
                            if column=='group_values':
                                if json.loads(value)!=json.loads(observed):raise ValueError('发布分组编码不符')
                            elif isinstance(value,float):
                                if observed is None or not math.isclose(value,float(observed),rel_tol=1e-10,abs_tol=1e-12):
                                    raise ValueError('发布比率字段不符：'+column)
                            elif value!=observed:raise ValueError('发布字段不符：'+column)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    return database

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-record',type=Path,required=True)
    parser.add_argument('--start-date')
    parser.add_argument('--end-date')
    parser.add_argument('--group-by',default='adgroup',help='comma separated, up to three: adgroup,pid,gender,occupation,city,...')
    parser.add_argument('--filter',action='append',default=[],help='axis=value; repeated filters use AND')
    parser.add_argument('--sort',choices=['clicks','impressions','ctr'],default='clicks')
    parser.add_argument('--min-impressions',type=int)
    parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('--publish',action='store_true',help='publish this EXACT scope atomically to MySQL analysis tables')
    parser.add_argument('--render-only',action='store_true')
    args=parser.parse_args()
    record=json.loads(args.run_record.read_text())
    if record.get('sql_revision')!=2:parser.error('需要SQL v2完整成功回执，旧批次请保留并使用新批次重算')
    if not record.get('run_id'):parser.error('成功回执缺少本次执行ID，请用当前执行器重跑同一v2批次')
    filters={}
    for item in args.filter:
        if '=' not in item:parser.error('筛选格式为axis=value')
        key,value=item.split('=',1)
        if key in filters:parser.error('同一筛选维度不能重复')
        filters[key]=value
    axes=[axis for axis in args.group_by.split(',') if axis]
    period=record['business_period']
    try:
        queries,context=build_queries(record['namespace'],record['batch_id'],
            args.start_date or period['start_date'],args.end_date or period['end_date'],axes,filters,
            args.sort,args.min_impressions,args.limit)
    except ValueError as error:parser.error(str(error))
    report=Path(tempfile.mkdtemp(prefix='metric-query-',dir=ROOT/'output'))
    for name,sql in queries.items():
        if sql:(report/(name+'.sql')).write_text('SET hive.execution.engine=tez;\nSET hive.tez.container.size=512;\nSET hive.tez.java.opts=-Xmx384m;\n'+sql)
    (report/'request.json').write_text(json.dumps(context,ensure_ascii=False,indent=2))
    if args.render_only:
        print('已渲染并验证查询，未执行：'+str(report))
        return
    env=os.environ.copy()
    env.update(dict(x.decode().split('=',1) for x in subprocess.check_output(
        ['bash','-c','source "$1"; env -0','bash',str(ROOT/'scripts/platform/env.sh')]).split(b'\0') if b'=' in x))
    with (ROOT/'output'/('.namespace-'+context['namespace']+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        # Verify the receipt still describes the immutable processing definition.
        remote='/warehouse/'+context['namespace']+'/processing/'+context['batch_id']+'/definition.json'
        current=json.loads(subprocess.check_output(['hdfs','dfs','-cat',remote],env=env,stderr=subprocess.DEVNULL))
        if any(current[key]!=record[key] for key in ['sql_revision','business_period','sql_sha256']):
            raise ValueError('成功回执与批次加工定义不符')
        completed=json.loads(subprocess.check_output(['hdfs','dfs','-cat',remote.rsplit('/',1)[0]+'/success.json'],env=env,stderr=subprocess.DEVNULL))
        if completed.get('run_id')!=record['run_id']:
            raise ValueError('回执不是批次当前完成状态，禁止查询失败重跑中的旧回执')
        combined=[]
        for name,sql in queries.items():
            if sql:
                combined += ["SELECT '__ADW_"+name+"_START__' AS adw_boundary;",
                             (report/(name+'.sql')).read_text(),
                             "SELECT '__ADW_"+name+"_END__' AS adw_boundary;"]
        (report/'query.sql').write_text('\n'.join(combined))
        with (report/'query.log').open('w') as log:
            output=subprocess.check_output(['beeline','--force=false','--silent=true','--showHeader=true',
                '--outputformat=tsv2','-u','jdbc:hive2://','-f',str(report/'query.sql')],
                env=env,stderr=log,timeout=1800,text=True)
        (report/'all.tsv').write_text(output)
        result={}
        lines=output.splitlines()
        for name,sql in queries.items():
            if sql is None:
                result[name]=[]
                continue
            first=lines.index('__ADW_'+name+'_START__')+1
            last=lines.index('__ADW_'+name+'_END__',first)
            section='\n'.join(line for line in lines[first:last] if line!='adw_boundary')+'\n'
            (report/(name+'.tsv')).write_text(section)
            result[name]=read_rows(section)
        if len(result['overview'])!=1 or len(result['quality'])!=1:raise ValueError('概览和质量应各返回一行，空范围也不例外')
        result['overview']=result['overview'][0]
        result['quality']=result['quality'][0]
        result.update(request=context,request_id=hashlib.sha256(json.dumps(context,sort_keys=True).encode()).hexdigest(),
                      technical_validation=context['namespace'].startswith('validation_'))
        if args.publish:result['published_database']=publish(result)
    (report/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    print(json.dumps({'request_id':result['request_id'],'output':str(report),'overview':result['overview'],
                      'published_database':result.get('published_database')},ensure_ascii=False))
if __name__=='__main__':main()
