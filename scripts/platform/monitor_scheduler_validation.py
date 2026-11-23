#!/usr/bin/env python3
"""Monitor the isolated workflow and recover ONLY its explicitly expected failure gate once."""
import json
from pathlib import Path
import time
from scheduler_api import Scheduler

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'output/scheduler-validation'
record=json.loads((folder/'workflow.json').read_text())
api=Scheduler();history=[];last=None;recovered=False
for _ in range(90):
    instances=api.call(f'/projects/{record["project_code"]}/workflow-instances',
      {'workflowDefinitionCode':record['workflow_code'],'pageNo':1,'pageSize':10})['totalList']
    if not instances:time.sleep(10);continue
    instance=instances[0];ident=instance['id']
    details=api.call(f'/projects/{record["project_code"]}/workflow-instances/{ident}/tasks')
    tasks=details.get('taskList',[]) if isinstance(details,dict) else details
    state=(instance['state'],[(t['name'],t['state']) for t in tasks])
    if state!=last:
        last=state
        history.append({'observed_at':time.strftime('%Y-%m-%d %H:%M:%S'),'instance':instance,'tasks':tasks})
        (folder/'execution-history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2))
        print(json.dumps({'instance_id':ident,'state':state[0],'tasks':state[1]},ensure_ascii=False),flush=True)
    if instance['state']=='FAILURE':
        failed=[t for t in tasks if t['state']=='FAILURE']
        upstream=next((t for t in tasks if t['name']=='Hive五层加工与质量检查'),None)
        if recovered or not upstream or upstream['state']!='SUCCESS' or len(failed)!=1 or failed[0]['name']!='首次故障与恢复验证':
            raise SystemExit('工作流发生非预期失败，保留日志，不自动重试。')
        (folder/'expected-first-failure.json').write_text(json.dumps({'instance':instance,'tasks':tasks},ensure_ascii=False,indent=2))
        api.call(f'/projects/{record["project_code"]}/executors/execute',
                 {'workflowInstanceId':ident,'executeType':'START_FAILURE_TASK_PROCESS'},'POST')
        recovered=True
        print('已从明确的技术故障点提交恢复；上游Hive成功结果保留。',flush=True)
    if instance['state']=='SUCCESS':
        if not recovered:raise SystemExit('工作流成功但没有观察到故障恢复过程，不能算恢复验收通过。')
        (folder/'success.json').write_text(json.dumps({'technical_validation':True,'instance_id':ident,
             'failure_observed':True,'recovery_submitted':True,'final_state':'SUCCESS','tasks':tasks},ensure_ascii=False,indent=2))
        print('SCHEDULER_RECOVERY_VALIDATION_PASS',flush=True);break
    time.sleep(10)
else:raise SystemExit('监测达到15分钟，未宣称成功；服务或任务仍可能运行，查看实际状态。')
