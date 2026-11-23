#!/usr/bin/env python3
"""Read-only checks for the isolated scheduler fixture; no real business conclusion."""
import json
from pathlib import Path
import pymysql

c=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
with pymysql.connect(host='127.0.0.1',port=3307,user='report_reader',password=c['report_reader'],database='taobao_reports_validation') as db:
    with db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*),SUM(impressions),SUM(clicks),SUM(reached_users) FROM published_daily_overview WHERE batch_id=%s",('tech_20261122_v1',))
        actual=tuple(int(x) for x in cursor.fetchone())
        if actual!=(2,5,3,4):raise SystemExit('技术报表日汇总不符：'+str(actual))
        cursor.execute("SELECT COUNT(*),COUNT(DISTINCT CONCAT_WS('|',batch_id,dt,axis,axis_value)) FROM published_daily_axis WHERE batch_id=%s",('tech_20261122_v1',))
        rows,keys=cursor.fetchone()
        if rows!=43 or rows!=keys:raise SystemExit('技术报表分组记录数量不符或重复')
        cursor.execute('SELECT COUNT(*) FROM published_batches WHERE batch_id=%s',('tech_20261122_v1',))
        if cursor.fetchone()[0]!=1:raise SystemExit('批次发布标记不唯一')
print('TECHNICAL_REPORT_CHECK_PASS: 2 daily rows / 43 axis rows; no duplicate publication. Not real ad data.')
