#!/usr/bin/env python3
"""Create and start the isolated full-pipeline recovery validation workflow."""
import json
from pathlib import Path
import shlex
from scheduler_api import Scheduler

ROOT=Path(__file__).resolve().parents[2]
api=Scheduler();out=ROOT/'output/scheduler-validation';out.mkdir(exist_ok=True)
record=out/'workflow.json'
if record.exists():raise SystemExit('已有技术工作流记录，保留；使用恢复入口操作，不重复创建。')
projects=api.call('/projects',{'pageNo':1,'pageSize':100})
project=next((p for p in projects['totalList'] if p['name']=='淘宝广告数仓-平台验证'),None)
if project is None:
    project=api.call('/projects',{'projectName':'淘宝广告数仓-平台验证','description':'隔离人工技术样例；真实数据未装载'},'POST')
project_code=project['code']
codes=api.call(f'/projects/{project_code}/task-definition/gen-task-codes',{'genNum':4})
receipt=out/'hive-success.json'
quote=shlex.quote
commands=[
 'python3 '+quote(str(ROOT/'scripts/platform/run_batch.py'))+' --staged '+quote(str(ROOT/'output/technical-fixture/staged'))+' --batch tech_20261122_v1 --namespace validation_pipeline --receipt '+quote(str(receipt)),
 'python3 '+quote(str(ROOT/'scripts/platform/scheduler_fail_once.py')),
 '/opt/taobao/module/superset-6.1.0-venv/bin/python '+quote(str(ROOT/'scripts/platform/export_reports.py'))+' --run-record '+quote(str(receipt)),
 '/opt/taobao/module/superset-6.1.0-venv/bin/python '+quote(str(ROOT/'scripts/platform/verify_published_reports.py'))
]
names=['Hive五层加工与质量检查','首次故障与恢复验证','DataX同步与全字段核对','报表发布及重复记录检查']
tasks=[];relations=[];locations={}
for i,(code,command,name) in enumerate(zip(codes,commands,names)):
    tasks.append({'code':code,'name':name,'version':1,'projectCode':project_code,'taskType':'SHELL',
      'taskParams':json.dumps({'rawScript':'set -euo pipefail\n'+command,'localParams':[],'resourceList':[]},ensure_ascii=False),
      'flag':'YES','taskPriority':'MEDIUM','workerGroup':'default','environmentCode':-1,'failRetryTimes':0,
      'failRetryInterval':1,'timeoutFlag':'CLOSE','timeout':0,'timeoutNotifyStrategy':'WARN','delayTime':0,
      'taskExecuteType':'BATCH','cpuQuota':-1,'memoryMax':-1})
    relations.append({'name':'','preTaskCode':0 if i==0 else codes[i-1],'preTaskVersion':0 if i==0 else 1,
       'postTaskCode':code,'postTaskVersion':1,'conditionType':'NONE','conditionParams':'{}'})
    locations[str(code)]={'x':200,'y':100+i*120}
workflow=api.call(f'/projects/{project_code}/workflow-definition',{'name':'历史批次全流程-技术故障恢复验证',
 'description':'人工技术数据：Hive加工→故障点→DataX同步→报表核对；不代表真实广告数据已处理。',
 'globalParams':'[]','locations':json.dumps(locations),'timeout':0,'taskDefinitionJson':json.dumps(tasks,ensure_ascii=False),
 'taskRelationJson':json.dumps(relations),'executionType':'SERIAL_WAIT'},'POST')
workflow_code=workflow['code']
result={'project_code':project_code,'workflow_code':workflow_code,'task_codes':codes,'namespace':'validation_pipeline',
 'batch_id':'tech_20261122_v1','technical_validation':True,'receipt':str(receipt)}
record.write_text(json.dumps(result,ensure_ascii=False,indent=2))
api.call(f'/projects/{project_code}/workflow-definition/{workflow_code}/release',{'releaseState':'ONLINE'},'POST')
api.call(f'/projects/{project_code}/executors/start-workflow-instance',{'workflowDefinitionCode':workflow_code,
 'scheduleTime':'','failureStrategy':'END','taskDependType':'TASK_POST','execType':'START_PROCESS','warningType':'NONE',
 'warningGroupId':0,'runMode':'RUN_MODE_SERIAL','workflowInstancePriority':'MEDIUM','workerGroup':'default','tenantCode':'default',
 'environmentCode':-1,'startParams':json.dumps({'batch_id':'tech_20261122_v1','data_start':'2017-05-06','data_end':'2017-05-13'})},'POST')
(out/'definition.json').write_text(json.dumps({'tasks':tasks,'relations':relations,'workflow':workflow},ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2));print('技术工作流已提交；必须检查实际执行状态，不能以提交成功当作运行成功。')
