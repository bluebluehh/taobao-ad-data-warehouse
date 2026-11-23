#!/usr/bin/env python3
"""Verify one actual Quartz trigger using a read-only technical report check, then take it offline."""
import datetime
import json
from pathlib import Path
import shlex
import time
from zoneinfo import ZoneInfo
from scheduler_api import Scheduler

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'output/scheduler-validation';marker=folder/'timer-definition.json'
if marker.exists():raise SystemExit('已有定时验证记录，保留；不重复创建定时任务。')
api=Scheduler();project=json.loads((folder/'workflow.json').read_text())['project_code']
code=api.call(f'/projects/{project}/task-definition/gen-task-codes',{'genNum':1})[0]
raw='set -euo pipefail\n/opt/taobao/module/superset-6.1.0-venv/bin/python '+shlex.quote(str(ROOT/'scripts/platform/verify_published_reports.py'))
task={'code':code,'name':'定时只读报表验收','version':1,'projectCode':project,'taskType':'SHELL',
 'taskParams':json.dumps({'rawScript':raw,'localParams':[],'resourceList':[]}),'flag':'YES',
 'taskPriority':'MEDIUM','workerGroup':'default','environmentCode':-1,'failRetryTimes':0,
 'failRetryInterval':1,'timeoutFlag':'CLOSE','timeout':0,'timeoutNotifyStrategy':'WARN',
 'delayTime':0,'taskExecuteType':'BATCH','cpuQuota':-1,'memoryMax':-1}
relation={'name':'','preTaskCode':0,'preTaskVersion':0,'postTaskCode':code,'postTaskVersion':1,'conditionType':'NONE','conditionParams':'{}'}
workflow=api.call(f'/projects/{project}/workflow-definition',{'name':'一次性定时触发验收（只读技术数据）',
 'description':'单次Quartz定时触发；不改写业务数据，完成后下线该定时计划。','globalParams':'[]','locations':json.dumps({str(code):{'x':100,'y':100}}),
 'taskDefinitionJson':json.dumps([task]),'taskRelationJson':json.dumps([relation]),'executionType':'SERIAL_WAIT'},'POST')
wc=workflow['code'];api.call(f'/projects/{project}/workflow-definition/{wc}/release',{'releaseState':'ONLINE'},'POST')
now=datetime.datetime.now(ZoneInfo('Asia/Shanghai'))
trigger=(now+datetime.timedelta(minutes=2)).replace(second=0,microsecond=0)
cron=f'0 {trigger.minute} {trigger.hour} {trigger.day} {trigger.month} ? {trigger.year}'
schedule={'startTime':now.strftime('%Y-%m-%d %H:%M:%S'),'endTime':(trigger+datetime.timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),'crontab':cron,'timezoneId':'Asia/Shanghai'}
created=api.call(f'/projects/{project}/schedules',{'workflowDefinitionCode':wc,'schedule':json.dumps(schedule),
 'warningType':'NONE','warningGroupId':0,'failureStrategy':'END','workerGroup':'default','tenantCode':'default',
 'environmentCode':-1,'workflowInstancePriority':'MEDIUM'},'POST')
# The create API may return an integer id or a Schedule object depending on controller serialization.
sid=created['id'] if isinstance(created,dict) else created
if sid is None:
 schedules=api.call(f'/projects/{project}/schedules',{'workflowDefinitionCode':wc,'pageNo':1,'pageSize':10})['totalList']
 sid=schedules[0]['id']
record={'project_code':project,'workflow_code':wc,'schedule_id':sid,'schedule':schedule,'trigger_at':trigger.isoformat(),'technical_validation':True}
marker.write_text(json.dumps(record,ensure_ascii=False,indent=2))
api.call(f'/projects/{project}/schedules/{sid}/online',{},'POST')
print('一次性只读定时任务已上线，等待实际触发：'+trigger.isoformat(),flush=True)
try:
    for _ in range(42):
        rows=api.call(f'/projects/{project}/workflow-instances',{'workflowDefinitionCode':wc,'pageNo':1,'pageSize':10})['totalList']
        if rows:
            row=rows[0]
            (folder/'timer-latest-instance.json').write_text(json.dumps(row,ensure_ascii=False,indent=2))
            if row['state']=='FAILURE':raise RuntimeError('定时只读任务失败，查看日志')
            if row['state']=='SUCCESS':
                if row.get('commandType')!='SCHEDULER':raise RuntimeError('任务成功但来源不是定时调度，不记为通过')
                (folder/'timer-success.json').write_text(json.dumps({'technical_validation':True,'scheduled_trigger_confirmed':True,'instance':row,'definition':record},ensure_ascii=False,indent=2))
                print('SCHEDULER_TIMER_VALIDATION_PASS instance='+str(row['id']),flush=True);break
        time.sleep(10)
    else:raise RuntimeError('7分钟内未观察到实际定时任务成功，不记为通过')
finally:
    api.call(f'/projects/{project}/schedules/{sid}/offline',{},'POST')
    print('本次临时定时计划已下线，避免后续自动运行。',flush=True)
