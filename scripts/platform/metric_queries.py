"""Validated SQL rendering for exact period metrics, quality scope and ranked groups."""
import re
import hashlib
from pathlib import Path
from stage_csv import business_period

ROOT = Path(__file__).resolve().parents[2]
AXES = {
 'hour':('CAST(event_hour AS STRING)',False), 'pid':('pid',False), 'adgroup':('adgroup_id',False),
 'campaign':('campaign_id','ad'), 'customer':('customer_id','ad'), 'category':('cate_id','ad'), 'brand':('brand','ad'),
 'gender':('gender_code','profile'), 'age':('age_level','profile'), 'shopping':('shopping_level','profile'),
 'pvalue':('pvalue_level','profile'), 'occupation':('occupation','profile'), 'city':('city_level','profile'),
}
PROFILE_AXES = {k for k,v in AXES.items() if v[1]=='profile'}
METRICS = ['impressions','clicks','ctr','reached_users','clicked_users','user_click_ratio','ad_units','impressions_per_user']
ATTRIBUTES = {'gender':'gender_code','age':'age_level','shopping':'shopping_level','pvalue':'pvalue_level','occupation':'occupation','city':'city_level'}
QUALITY_COUNTS = ['impressions','matched_profile_impressions','reached_users','matched_profile_users','matched_ad_impressions']+[a+'_missing' for a in ATTRIBUTES]
QUALITY_RATES = ['profile_row_coverage','profile_user_coverage','ad_row_coverage']+[a+'_missing_rate' for a in ATTRIBUTES]

def literal(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,255}',value):
        raise ValueError('筛选值应为原始匿名编码或缺失标签，仅允许字母、数字、下划线、点、冒号和横线')
    return "'"+value+"'"

def axis_expression(axis):
    if axis not in AXES:raise ValueError('不支持的分析维度：'+axis)
    column,kind=AXES[axis]
    if not kind:return column
    missing='__unmatched_profile__' if kind=='profile' else '__unmatched_ad__'
    matched='profile_matched' if kind=='profile' else 'ad_matched'
    return f"CASE WHEN NOT {matched} THEN '{missing}' ELSE coalesce({column},'__missing_attribute__') END"

def render_template(filename,values):
    text=(ROOT/'sql/hive'/filename).read_text()
    for name,value in values.items():text=text.replace('$'+'{hivevar:'+name+'}',str(value))
    if '$'+'{' in text:raise ValueError('查询模板中还有未替换的变量')
    return text

def build_queries(namespace,batch,start,end,axes,filters,sort='clicks',minimum=None,limit=100):
    if not re.fullmatch(r'taobao|validation_[a-z0-9_]+',namespace):raise ValueError('命名空间不符')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',batch):raise ValueError('批次名不符')
    business_period(start,end)
    if len(axes)>3 or len(set(axes))!=len(axes):raise ValueError('组合分析支持最多三个不同维度')
    for axis in axes:axis_expression(axis)
    if sort not in ['clicks','impressions','ctr']:raise ValueError('排行指标不符')
    if minimum is None:minimum=1000 if sort=='ctr' else 0
    if not isinstance(minimum,int) or not 0<=minimum<=10**12:raise ValueError('最小曝光门槛不符')
    if not isinstance(limit,int) or not 1<=limit<=1000:raise ValueError('排行条数为1至1000')
    extra=''.join(' AND ('+axis_expression(key)+')='+literal(value) for key,value in sorted(filters.items()))
    quality_filters={key:value for key,value in filters.items() if key not in PROFILE_AXES}
    quality_extra=''.join(' AND ('+axis_expression(key)+')='+literal(value) for key,value in sorted(quality_filters.items()))
    values={'ns':namespace,'batch':batch,'start_date':start,'end_date':end}
    overview=render_template('08_period_query.sql',values).rstrip().removesuffix(';')+extra+';'
    quality=render_template('10_quality_query.sql',{**values,'extra_filters':quality_extra})
    groups=None
    if axes:
        expressions=[axis_expression(a) for a in axes]
        aliases=[f'group_value_{i+1}' for i in range(len(axes))]
        order=sort+' DESC,'+('clicks DESC,' if sort=='impressions' else '')+('impressions DESC,' if sort!='impressions' else '')+','.join(aliases)
        groups=render_template('09_cross_analysis.sql',{**values,'extra_filters':extra,
           'group_select':','.join(expr+' AS '+alias for expr,alias in zip(expressions,aliases)),
           'group_by':','.join(expressions),'group_columns':','.join(aliases),
           'minimum':minimum,'limit':limit,'sort_columns':order})
    context={'namespace':namespace,'batch_id':batch,'start_date':start,'end_date':end,
             'axes':axes,'filters':filters,'quality_scope_filters':quality_filters,
             'sort':sort,'min_impressions':minimum,'limit':limit,'sql_revision':2}
    context['query_sha256']={name:hashlib.sha256(sql.encode()).hexdigest() for name,sql in
                            [('overview',overview),('quality',quality),('groups',groups)] if sql}
    return {'overview':overview,'quality':quality,'groups':groups},context
