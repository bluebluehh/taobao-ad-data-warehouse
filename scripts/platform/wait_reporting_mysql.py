#!/usr/bin/env python3
"""Wait for the existing isolated reporting database to accept an authenticated query."""
import subprocess
import time
for _ in range(30):
    result=subprocess.run(['mysql','--defaults-file=/opt/taobao/data/reporting/admin.cnf','-N','-e','SELECT 1'],capture_output=True,text=True)
    if result.returncode==0 and result.stdout.strip()=='1':
        print('独立报表MySQL已接受验证查询');break
    time.sleep(1)
else:raise SystemExit('独立报表MySQL未在30秒内接受查询')
