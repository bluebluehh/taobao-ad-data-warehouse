#!/usr/bin/env python3
"""Run the synthetic Hive v2 regression, including an intentional final failure."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace',required=True)
    parser.add_argument('--batch',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'validation_[a-z0-9_]+',args.namespace):parser.error('只允许validation_*测试空间')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',args.batch):parser.error('批次名不符')
    sql=(ROOT/'tests/hive/sql_v2_regression.sql').read_text()
    for key,value in [('ns',args.namespace),('batch',args.batch)]:sql=sql.replace('${hivevar:'+key+'}',value)
    output=ROOT/'output';output.mkdir(exist_ok=True)
    report=Path(tempfile.mkdtemp(prefix='sql-v2-regression-',dir=output))
    (report/'regression.sql').write_text(sql)
    env=os.environ.copy()
    env.update(dict(x.decode().split('=',1) for x in subprocess.check_output(
       ['bash','-c','source "$1"; env -0','bash',str(ROOT/'scripts/platform/env.sh')]).split(b'\0') if b'=' in x))
    with (report/'regression.log').open('w') as log:
        completed=subprocess.run(['beeline','--force=false','--silent=true','--showHeader=false',
          '--outputformat=tsv2','-u','jdbc:hive2://','-f',str(report/'regression.sql')],env=env,stdout=log,stderr=log,timeout=1800)
    log=(report/'regression.log').read_text()
    markers=['SQL_V2_POSITIVE_REGRESSIONS_PASS','SQL_V2_DEFECT_DETECTION_PASS']
    passed=completed.returncode!=0 and all(marker in log for marker in markers) and 'ASSERT_TRUE(): assertion failed' in log
    result={'technical_validation':True,'namespace':args.namespace,'batch_id':args.batch,
       'positive_regressions_passed':markers[0] in log,'three_defects_detected':markers[1] in log,
       'intentional_corruption_blocked':passed,'beeline_exit_code':completed.returncode,'passed':passed}
    (report/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({**result,'report':str(report)}))
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
