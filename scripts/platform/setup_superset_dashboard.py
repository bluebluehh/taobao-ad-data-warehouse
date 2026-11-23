#!/usr/bin/env python3
"""Build a native Superset dashboard using only the isolated technical report database."""
import json
from pathlib import Path
from urllib.parse import quote_plus
import requests

ROOT=Path(__file__).resolve().parents[2]
BASE='http://127.0.0.1:8089'
secret=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
s=requests.Session();s.trust_env=False

def call(path,method='GET',payload=None):
    r=s.request(method,BASE+path,json=payload,timeout=90)
    if r.status_code>=400:
        error=r.text
        for value in secret.values():error=error.replace(value,'[REDACTED]')
        raise RuntimeError(f'{path} HTTP {r.status_code}: {error[:1600]}')
    return r.json()

login=call('/api/v1/security/login','POST',{'username':'admin','password':secret['superset_admin'],'provider':'db','refresh':True})
s.headers['Authorization']='Bearer '+login['access_token']
s.headers['X-CSRFToken']=call('/api/v1/security/csrf_token/')['result']
s.headers['Referer']=BASE+'/'

def database(name,db):
    existing=next((d for d in call('/api/v1/database/')['result'] if d['database_name']==name),None)
    if existing:return existing['id']
    uri='mysql+pymysql://report_reader:'+quote_plus(secret['report_reader'])+'@127.0.0.1:3307/'+db+'?charset=utf8mb4'
    return call('/api/v1/database/','POST',{'database_name':name,'sqlalchemy_uri':uri,'expose_in_sqllab':True,'allow_dml':False})['id']

def dataset(dbid,table):
    existing=next((d for d in call('/api/v1/dataset/')['result'] if d['table_name']==table and d['database']['id']==dbid),None)
    if existing:return existing['id']
    return call('/api/v1/dataset/','POST',{'database':dbid,'schema':'taobao_reports_validation','table_name':table})['id']

prod_id=database('淘宝广告正式报表（待真实数据）','taobao_reports')
validation_id=database('淘宝广告技术验证（人工测试数据）','taobao_reports_validation')
overview_id=dataset(validation_id,'published_daily_overview')
axis_id=dataset(validation_id,'published_daily_axis_labeled')

labels={'dt':'业务日期','impressions':'曝光量','clicks':'点击量','ctr':'点击率','reached_users':'触达用户数',
 'clicked_users':'点击用户数','user_click_ratio':'用户点击比例','ad_units':'曝光广告单元数',
 'impressions_per_user':'人均曝光次数','unmatched_profiles':'画像未匹配曝光量','unmatched_ads':'广告未匹配曝光量',
 'axis':'分析维度','axis_value':'分组编码','group_label':'分析分组','impression_share':'曝光贡献率','click_share':'点击贡献率','batch_id':'历史装载批次'}
for dataset_id in [overview_id,axis_id]:
    info=call('/api/v1/dataset/'+str(dataset_id))['result']
    columns=[{'id':c['id'],'column_name':c['column_name'],'verbose_name':labels.get(c['column_name'],c.get('verbose_name'))} for c in info['columns']]
    call('/api/v1/dataset/'+str(dataset_id),'PUT',{'columns':columns})

metric_impressions={'expressionType':'SQL','sqlExpression':'SUM(impressions)','label':'曝光量','optionName':'metric_impressions'}
metric_clicks={'expressionType':'SQL','sqlExpression':'SUM(clicks)','label':'点击量','optionName':'metric_clicks'}
metric_ctr={'expressionType':'SQL','sqlExpression':'SUM(clicks)/NULLIF(SUM(impressions),0)','label':'点击率','optionName':'metric_ctr'}
base_filter={'col':'batch_id','op':'==','val':'tech_20261122_v1'}
configs=[
 {'title':'投放概览：逐日记录（技术验证）','dataset':overview_id,'viz':'table','columns':['dt','impressions','clicks','ctr','reached_users','clicked_users','unmatched_profiles'],'metrics':[],'filters':[base_filter]},
 {'title':'广告单元曝光与点击（技术验证）','dataset':axis_id,'viz':'echarts_timeseries_bar','columns':['group_label'],'metrics':[metric_impressions,metric_clicks],'filters':[base_filter,{'col':'axis','op':'==','val':'adgroup'}]},
 {'title':'性别人群响应（技术验证）','dataset':axis_id,'viz':'table','columns':['group_label'],'metrics':[metric_impressions,metric_clicks,metric_ctr],'filters':[base_filter,{'col':'axis','op':'==','val':'gender'}]},
 {'title':'展示位置与小时（技术验证）','dataset':axis_id,'viz':'table','columns':['axis','group_label'],'metrics':[metric_impressions,metric_clicks,metric_ctr],'filters':[base_filter,{'col':'axis','op':'IN','val':['pid','hour']}]}
]
existing_charts=call('/api/v1/chart/')['result'];chart_ids=[];query_results=[]
for cfg in configs:
    raw=not cfg['metrics']
    filters=[{'clause':'WHERE','expressionType':'SIMPLE','subject':f['col'],'operator':f['op'],'comparator':f['val']} for f in cfg['filters']]
    params={'viz_type':cfg['viz'],'datasource':f"{cfg['dataset']}__table",'time_range':'No filter','adhoc_filters':filters,
      'metrics':cfg['metrics'],'groupby':[] if raw or cfg['viz']=='echarts_timeseries_bar' else cfg['columns'],'query_mode':'raw' if raw else 'aggregate',
      'all_columns':cfg['columns'] if raw else [],'row_limit':1000,'show_legend':True,'rich_tooltip':True,
      'column_config':{'ctr':{'d3NumberFormat':'.2%'},'点击率':{'d3NumberFormat':'.2%'}},
      'table_timestamp_format':'%Y-%m-%d',
      'orientation':'vertical','x_axis':cfg['columns'][0],'x_axis_time_format':'smart_date','y_axis_format':',d'}
    context={'datasource':{'id':cfg['dataset'],'type':'table'},'force':True,
      'queries':[{'columns':cfg['columns'],'metrics':cfg['metrics'],'filters':cfg['filters'],'time_range':'No filter',
                  'row_limit':1000,'orderby':[],'is_timeseries':False}],
      'form_data':params,'result_format':'json','result_type':'full'}
    existing=next((c for c in existing_charts if c['slice_name']==cfg['title']),None)
    payload={'slice_name':cfg['title'],'viz_type':cfg['viz'],'datasource_id':cfg['dataset'],'datasource_type':'table',
             'params':json.dumps(params,ensure_ascii=False),'query_context':json.dumps(context,ensure_ascii=False)}
    if existing:
        cid=existing['id'];call('/api/v1/chart/'+str(cid),'PUT',payload)
    else:cid=call('/api/v1/chart/','POST',payload)['id']
    result=call('/api/v1/chart/data','POST',context)
    rows=result['result'][0]['data']
    if not rows:raise RuntimeError(cfg['title']+'查询无数据')
    chart_ids.append(cid);query_results.append({'chart_id':cid,'title':cfg['title'],'rows':rows})

positions={'DASHBOARD_VERSION_KEY':'v2','ROOT_ID':{'id':'ROOT_ID','type':'ROOT','children':['GRID_ID']},
 'GRID_ID':{'id':'GRID_ID','type':'GRID','children':['ROW-1','ROW-2'],'parents':['ROOT_ID']}}
for row in range(2):
    rid='ROW-'+str(row+1);children=[]
    for index,cid in enumerate(chart_ids[row*2:row*2+2]):
        ident='CHART-'+str(cid);children.append(ident)
        positions[ident]={'id':ident,'type':'CHART','parents':['ROOT_ID','GRID_ID',rid],
                          'children':[],'meta':{'chartId':cid,'width':6,'height':55}}
    positions[rid]={'id':rid,'type':'ROW','parents':['ROOT_ID','GRID_ID'],'children':children,'meta':{'background':'BACKGROUND_TRANSPARENT'}}
name='淘宝广告数仓 · 技术验证看板（非真实分析）'
existing=next((d for d in call('/api/v1/dashboard/')['result'] if d['dashboard_title']==name),None)
payload={'dashboard_title':name,'slug':'taobao-platform-validation','published':True,
         'position_json':json.dumps(positions,ensure_ascii=False),'json_metadata':json.dumps({'timed_refresh_immune_slices':[],'refresh_frequency':0})}
if existing:
    did=existing['id'];call('/api/v1/dashboard/'+str(did),'PUT',payload)
else:did=call('/api/v1/dashboard/','POST',payload)['id']
# Explicitly associate saved charts with the dashboard, then verify the server relationship.
for cid in chart_ids:
    call('/api/v1/chart/'+str(cid),'PUT',{'dashboards':[did]})
linked=call('/api/v1/dashboard/'+str(did)+'/charts')['result']
if len(linked)!=4:raise RuntimeError('看板关联图表数不是4')
# The dashboard is saved locally; charts and data remain explicitly labeled synthetic.
report={'technical_validation':True,'dashboard_id':did,'dashboard_url':BASE+'/superset/dashboard/taobao-platform-validation/',
        'production_database_id':prod_id,'validation_database_id':validation_id,'charts':query_results,
        'browser_visual_acceptance':False}
(ROOT/'output/platform_checks/next-stage/superset-dashboard.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('Superset本机看板及4个图表查询通过：'+report['dashboard_url'])
print('当前数据为人工技术验证；浏览器完整交互与目视验收尚未完成。')
