#!/usr/bin/env python3
"""Create native Superset charts for one published, exact analysis scope."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote_plus
import requests

BASE='http://127.0.0.1:8089'
LABELS={'impressions':'曝光量','clicks':'点击量','ctr':'点击率','reached_users':'触达用户数',
 'clicked_users':'点击用户数','user_click_ratio':'用户点击比例','ad_units':'曝光广告单元数',
 'impressions_per_user':'人均曝光次数','group_label':'分析分组','impression_share':'曝光贡献率',
 'click_share':'点击贡献率','profile_row_coverage':'画像曝光覆盖率','profile_user_coverage':'画像用户覆盖率',
 'ad_row_coverage':'广告曝光覆盖率','matched_profile_impressions':'已匹配画像曝光',
 'matched_profile_users':'已匹配画像用户','gender_missing_rate':'性别属性缺失率',
 'age_missing_rate':'年龄属性缺失率','shopping_missing_rate':'购物属性缺失率',
 'pvalue_missing_rate':'消费档次缺失率','occupation_missing_rate':'occupation属性缺失率',
 'city_missing_rate':'城市等级缺失率'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result',type=Path,required=True,help='query_metrics.py --publish generated result.json')
    args=parser.parse_args()
    result=json.loads(args.result.read_text())
    context=result['request'];rid=result['request_id']
    if not re.fullmatch('[0-9a-f]{64}',rid) or hashlib.sha256(json.dumps(context,sort_keys=True).encode()).hexdigest()!=rid:
        raise SystemExit('查询范围ID与请求内容不符')
    technical=context['namespace'].startswith('validation_')
    target='taobao_reports_validation' if technical else 'taobao_reports'
    if result.get('published_database')!=target:raise SystemExit('该结果尚未发布到对应MySQL库')
    private=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
    session=requests.Session();session.trust_env=False
    def call(path,method='GET',payload=None):
        response=session.request(method,BASE+path,json=payload,timeout=90)
        if response.status_code>=400:
            message=response.text
            for value in private.values():
                if isinstance(value,str):message=message.replace(value,'[REDACTED]')
            raise RuntimeError(path+': '+message[:1000])
        return response.json()
    token=call('/api/v1/security/login','POST',{'username':'admin','password':private['superset_admin'],'provider':'db'})['access_token']
    session.headers['Authorization']='Bearer '+token
    session.headers['X-CSRFToken']=call('/api/v1/security/csrf_token/')['result']
    session.headers['Referer']=BASE+'/'
    database_name='淘宝广告期间分析 '+('技术验证' if technical else '正式数据')
    found=next((d for d in call('/api/v1/database/')['result'] if d['database_name']==database_name),None)
    if found:database_id=found['id']
    else:
        database_id=call('/api/v1/database/','POST',{'database_name':database_name,
          'sqlalchemy_uri':'mysql+pymysql://report_reader:'+quote_plus(private['report_reader'])+'@127.0.0.1:3307/'+target+'?charset=utf8mb4',
          'expose_in_sqllab':True,'allow_dml':False})['id']
    datasets={}
    for table in ['published_analysis_overview','published_analysis_quality','published_analysis_groups']:
        found=next((d for d in call('/api/v1/dataset/')['result'] if d['table_name']==table and d['database']['id']==database_id),None)
        if found:did=found['id']
        else:did=call('/api/v1/dataset/','POST',{'database':database_id,'schema':target,'table_name':table})['id']
        info=call('/api/v1/dataset/'+str(did))['result']
        columns=[{'id':c['id'],'column_name':c['column_name'],'verbose_name':LABELS.get(c['column_name'],c.get('verbose_name'))} for c in info['columns']]
        call('/api/v1/dataset/'+str(did),'PUT',{'columns':columns})
        datasets[table]=did
    filter_={'col':'request_id','op':'==','val':rid}
    overview=['impressions','clicks','ctr','reached_users','clicked_users','user_click_ratio','ad_units','impressions_per_user']
    quality=['profile_row_coverage','profile_user_coverage','ad_row_coverage','matched_profile_impressions',
       'matched_profile_users','gender_missing_rate','age_missing_rate','shopping_missing_rate',
       'pvalue_missing_rate','occupation_missing_rate','city_missing_rate']
    configurations=[
      ('期间概览 精确去重','published_analysis_overview','table',overview,[]),
      ('覆盖率与已匹配属性缺失','published_analysis_quality','table',quality,[]),
      ('组合分组表现','published_analysis_groups','table',['group_label','impressions','clicks','ctr','reached_users','impression_share','click_share'],[]),
      ('分组曝光与点击','published_analysis_groups','echarts_timeseries_bar',['group_label'],[
        {'expressionType':'SQL','sqlExpression':'SUM(impressions)','label':'曝光量','optionName':'impressions'},
        {'expressionType':'SQL','sqlExpression':'SUM(clicks)','label':'点击量','optionName':'clicks'}])]
    chart_ids=[];reports=[]
    existing=call('/api/v1/chart/')['result']
    for label,table,viz,columns,metrics in configurations:
        title=label+' '+rid[:12]
        did=datasets[table]
        adhoc=[{'expressionType':'SIMPLE','subject':'request_id','operator':'==','comparator':rid,'clause':'WHERE','sqlExpression':None,'filterOptionName':'scope'}]
        params={'viz_type':viz,'datasource':str(did)+'__table','time_range':'No filter','adhoc_filters':adhoc,
          'metrics':metrics,'groupby':[],'query_mode':'aggregate' if metrics else 'raw',
          'all_columns':[] if metrics else columns,'row_limit':1000,'x_axis':columns[0],
          'show_legend':True,'rich_tooltip':True,'orientation':'vertical','y_axis_format':',d',
          'column_config':{c:{'d3NumberFormat':'.2%'} for c in quality+['ctr','user_click_ratio','impression_share','click_share'] if 'rate' in c or 'coverage' in c or c in ['ctr','user_click_ratio','impression_share','click_share']}}
        query={'datasource':{'id':did,'type':'table'},'force':True,
          'queries':[{'columns':columns,'metrics':metrics,'filters':[filter_],'time_range':'No filter',
                      'row_limit':1000,'orderby':[],'is_timeseries':False}],
          'form_data':params,'result_format':'json','result_type':'full'}
        payload={'slice_name':title,'viz_type':viz,'datasource_id':did,'datasource_type':'table',
          'params':json.dumps(params,ensure_ascii=False),'query_context':json.dumps(query,ensure_ascii=False)}
        found=next((c for c in existing if c['slice_name']==title),None)
        if found:
            cid=found['id'];call('/api/v1/chart/'+str(cid),'PUT',payload)
        else:cid=call('/api/v1/chart/','POST',payload)['id']
        rows=call('/api/v1/chart/data','POST',query)['result'][0]['data']
        expected=1 if table!='published_analysis_groups' else len(result['groups'])
        if len(rows)!=expected:raise RuntimeError('图表行数与已发布分析范围不一致：'+title)
        reports.append({'chart_id':cid,'rows':len(rows),'title':label});chart_ids.append(cid)
    positions={'DASHBOARD_VERSION_KEY':'v2','ROOT_ID':{'id':'ROOT_ID','type':'ROOT','children':['GRID_ID']},
      'GRID_ID':{'id':'GRID_ID','type':'GRID','children':['ROW-1','ROW-2'],'parents':['ROOT_ID']}}
    for index in range(2):
        row='ROW-'+str(index+1);children=[]
        for cid in chart_ids[index*2:index*2+2]:
            ident='CHART-'+str(cid);children.append(ident)
            positions[ident]={'id':ident,'type':'CHART','parents':['ROOT_ID','GRID_ID',row],'children':[],
              'meta':{'chartId':cid,'width':6,'height':55}}
        positions[row]={'id':row,'type':'ROW','parents':['ROOT_ID','GRID_ID'],'children':children,'meta':{'background':'BACKGROUND_TRANSPARENT'}}
    slug='taobao-scope-'+rid[:16]
    title=('技术验证 非真实分析' if technical else '正式期间分析')+' '+context['start_date']+' 至 '+context['end_date']+' '+rid[:8]
    payload={'dashboard_title':title,'slug':slug,'published':True,'position_json':json.dumps(positions,ensure_ascii=False),
      'json_metadata':json.dumps({'refresh_frequency':0,'timed_refresh_immune_slices':[]})}
    found=next((d for d in call('/api/v1/dashboard/')['result'] if d.get('slug')==slug),None)
    if found:
        dashboard=found['id'];call('/api/v1/dashboard/'+str(dashboard),'PUT',payload)
    else:dashboard=call('/api/v1/dashboard/','POST',payload)['id']
    for cid in chart_ids:call('/api/v1/chart/'+str(cid),'PUT',{'dashboards':[dashboard]})
    receipt={'request_id':rid,'technical_validation':technical,'dashboard_id':dashboard,
             'url':BASE+'/superset/dashboard/'+slug+'/','charts':reports,'browser_verified':False,
             'scope':context}
    (args.result.parent/'dashboard.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print(json.dumps({'dashboard_url':receipt['url'],'request_id':rid,'technical_validation':technical},ensure_ascii=False))
if __name__=='__main__':main()
