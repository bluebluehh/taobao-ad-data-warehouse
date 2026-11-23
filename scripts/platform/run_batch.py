#!/usr/bin/env python3
"""Load an immutable staged CSV batch and run Hive layers, preserving all execution logs."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid
from stage_csv import HEADERS, file_sha256, business_period, normalized_header

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', type=Path, required=True)
    parser.add_argument('--batch', required=True)
    parser.add_argument('--receipt', type=Path, help='optional success receipt inside project output for downstream tasks')
    parser.add_argument('--namespace', default='taobao', help='taobao or validation_*')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.batch):
        parser.error('批次名只允许字母、数字、下划线、横线，最长64字符')
    if not re.fullmatch(r'taobao|validation_[a-z0-9_]+', args.namespace):
        parser.error('命名空间只允许 taobao 或 validation_*')
    if args.receipt:
        receipt = args.receipt.resolve()
        if not receipt.is_relative_to((ROOT/'output').resolve()):
            parser.error('回执必须保存在项目output目录中')
        if receipt.exists():
            old = json.loads(receipt.read_text())
            if old.get('batch_id') != args.batch or old.get('namespace') != args.namespace:
                parser.error('回执属于另一个批次，拒绝覆盖')
    manifest_path = args.staged / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('kind') != 'full_csv_staging' or manifest.get('sampled') is not False:
        parser.error('不是完整CSV整理批次')
    if manifest.get('technical_validation') is True and args.namespace == 'taobao':
        parser.error('人工技术测试数据禁止导入taobao正式命名空间')
    period = manifest.get('business_period', business_period())
    try:
        if business_period(period['start_date'], period['end_date']) != period:
            raise ValueError('业务期或时区不符')
    except (KeyError, TypeError, ValueError) as error:
        parser.error('批次业务期无效：'+str(error))
    entries = manifest.get('files', [])
    if len(entries) != 3 or {r.get('source_file') for r in entries} != {name+'.csv' for name in HEADERS}:
        parser.error('完成清单必须准确包含三个主体文件')
    for item in entries:
        name = item['source_file'][:-4]
        expected_name = name + '.tsv'
        if item.get('staged_file') != expected_name or item.get('header') != HEADERS[name]:
            parser.error('清单中的文件名或表头不符')
        if 'source_header' in item:
            try:
                normalized_header(item['source_header'], HEADERS[name])
            except ValueError as error:
                parser.error(str(error))
        if item.get('normalized_header', HEADERS[name]) != HEADERS[name]:
            parser.error('规范表头与预期不符')
        path = args.staged / expected_name
        if item.get('rows', 0) <= 0 or path.stat().st_size != item['staged_bytes'] or file_sha256(path) != item.get('staged_sha256'):
            parser.error(f'{expected_name} 的内容与完成清单不符或记录为空')
    output = ROOT / 'output'
    output.mkdir(exist_ok=True)
    # One owner writes a namespace at a time, including shared DIM/hour and schema updates.
    lock_path = output / f'.namespace-{args.namespace}.lock'
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = Path(tempfile.mkdtemp(prefix='batch-', dir=output))
        env = os.environ.copy()
        # Resolve the same environment as interactive validation, without exposing credentials.
        loaded = subprocess.check_output(['bash','-c','source "$1"; env -0','bash',str(ROOT/'scripts/platform/env.sh')])
        env.update(dict(x.decode().split('=',1) for x in loaded.split(b'\0') if b'=' in x))
        with (report/'run.log').open('w') as log:
            def run(command, capture=False):
                log.write(json.dumps(command,ensure_ascii=False)+'\n');log.flush()
                result = subprocess.run(command,env=env,stdout=subprocess.PIPE if capture else log,stderr=log,check=True,timeout=1800)
                return result.stdout if capture else None
            def hdfs(*command, capture=False):
                return run(['hdfs','dfs',*map(str,command)],capture=capture)
            def hive_sql(text, capture=False):
                path = report/('query-'+uuid.uuid4().hex+'.sql')
                path.write_text(text)
                return run(['beeline','--force=false','--silent=true','--showHeader=false',
                            '--outputformat=tsv2','-u','jdbc:hive2://','-f',str(path)],capture=capture)
            def render(text):
                for key,value in {'ns':args.namespace,'batch':args.batch,**period}.items():
                    text = text.replace('$'+'{hivevar:'+key+'}', value)
                if '$'+'{' in text:
                    raise ValueError('SQL包含未替换的变量，停止执行')
                return text
            remote = f'/warehouse/{args.namespace}/incoming/{args.batch}'
            exists = subprocess.run(['hdfs','dfs','-test','-e',remote],env=env,stdout=log,stderr=log)
            if exists.returncode == 0:
                if json.loads(hdfs('-cat',remote+'/manifest.json',capture=True)) != manifest:
                    raise RuntimeError('HDFS已有不同内容的同名批次，拒绝覆盖')
            elif exists.returncode == 1:
                temporary = remote + '.upload-' + uuid.uuid4().hex
                hdfs('-mkdir','-p',temporary)
                for name in HEADERS:
                    hdfs('-mkdir',temporary+'/'+name)
                    hdfs('-put',args.staged/(name+'.tsv'),temporary+'/'+name+'/data.tsv')
                hdfs('-put',manifest_path,temporary+'/manifest.json')
                hdfs('-mv',temporary,remote)
            else:
                raise RuntimeError('无法检查HDFS批次，停止')
            hive_sql(render('\n'.join((ROOT/'sql/hive'/f).read_text() for f in ['01_ods.sql','02_layers.sql'])))
            describe = hive_sql(f'DESCRIBE {args.namespace}_dwd.exposure;',capture=True).decode()
            columns = [line.split('\t')[0].strip() for line in describe.splitlines()]
            base_columns = ['source_file','source_line','user_id','adgroup_id','pid','event_ts','event_hour',
                'click_count','profile_matched','ad_matched','gender_code','age_level','shopping_level',
                'pvalue_level','cate_id','campaign_id','customer_id','brand']
            actual = [c for c in columns if c in base_columns+['occupation','city_level']][:20]
            if actual == base_columns:
                hive_sql(f'ALTER TABLE {args.namespace}_dwd.exposure ADD COLUMNS (occupation STRING, city_level STRING) CASCADE;')
            elif actual != base_columns+['occupation','city_level']:
                raise ValueError('DWD物理列与v2契约不符，停止，禁止通过DROP表迁移')
            definition = {'sql_revision':2,'business_period':period,
                'sql_sha256':{p.name:file_sha256(p) for p in sorted((ROOT/'sql/hive').glob('0[1-7]_*.sql'))}}
            definition_path = f'/warehouse/{args.namespace}/processing/{args.batch}/definition.json'
            found = subprocess.run(['hdfs','dfs','-test','-e',definition_path],env=env,stdout=log,stderr=log)
            if found.returncode == 0:
                if json.loads(hdfs('-cat',definition_path,capture=True)) != definition:
                    raise ValueError('同批次加工版本、SQL或业务期已变化；使用新批次保留旧结果')
            elif found.returncode == 1:
                partitions = hive_sql(f"SHOW PARTITIONS {args.namespace}_dwd.exposure PARTITION(batch_id='{args.batch}');",capture=True).decode()
                if 'batch_id=' in partitions:
                    raise ValueError('已有未登记版本的旧加工分区，请使用新批次；不删除旧数据')
                local_definition = report/'definition.json'
                local_definition.write_text(json.dumps(definition,sort_keys=True))
                hdfs('-mkdir','-p',definition_path.rsplit('/',1)[0])
                hdfs('-put',local_definition,definition_path)
            else:
                raise RuntimeError('无法核对加工版本')
            if args.receipt and receipt.exists():
                receipt.replace(receipt.with_name(receipt.name+'.previous-'+uuid.uuid4().hex))
            current_success_path = definition_path.rsplit('/',1)[0]+'/success.json'
            prior = subprocess.run(['hdfs','dfs','-test','-e',current_success_path],env=env,stdout=log,stderr=log)
            if prior.returncode == 0:
                hdfs('-mv',current_success_path,current_success_path+'.previous-'+uuid.uuid4().hex)
            elif prior.returncode != 1:
                raise RuntimeError('无法核对上次批次完成状态')
            source = []
            for name in HEADERS:
                source.append(f"ALTER TABLE {args.namespace}_ods.{name} ADD IF NOT EXISTS PARTITION(batch_id='{args.batch}') LOCATION '{remote}/{name}';")
            for item in entries:
                table = item['source_file'][:-4]
                source.append(f"SELECT assert_true(COUNT(*)={int(item['rows'])}) FROM {args.namespace}_ods.{table} WHERE batch_id='{args.batch}';")
            for filename in ['03_preflight.sql','04_dim_dwd.sql','05_quality.sql','06_dws_ads.sql','07_reconcile.sql']:
                source.append((ROOT/'sql/hive'/filename).read_text())
            query = report/'pipeline.sql'
            rendered = render('\n'.join(source))
            if '${' in rendered:
                raise ValueError('SQL包含未替换的变量，停止执行')
            query.write_text('SET hive.execution.engine=tez;\nSET hive.tez.container.size=512;\nSET hive.tez.java.opts=-Xmx384m;\n'+rendered)
            run(['beeline','--force=false','-u','jdbc:hive2://','--hivevar',f'ns={args.namespace}',
                 '--hivevar',f'batch={args.batch}','-f',str(query)])
            success = {'batch_id':args.batch,'namespace':args.namespace,
                       **definition,
                       'run_id':uuid.uuid4().hex,
                       'technical_validation':args.namespace.startswith('validation_'),
                       'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'manifest':manifest}
            (report/'success.json').write_text(json.dumps(success,ensure_ascii=False,indent=2))
            temporary_success = current_success_path+'.upload-'+uuid.uuid4().hex
            hdfs('-put',report/'success.json',temporary_success)
            hdfs('-mv',temporary_success,current_success_path)
            if args.receipt:
                receipt.parent.mkdir(parents=True,exist_ok=True)
                temporary_receipt = receipt.with_name(receipt.name+'.tmp-'+uuid.uuid4().hex)
                temporary_receipt.write_text(json.dumps(success,ensure_ascii=False,indent=2))
                temporary_receipt.replace(receipt)
        print(f'批次执行及校验通过；日志：{report}')

if __name__ == '__main__':
    main()
