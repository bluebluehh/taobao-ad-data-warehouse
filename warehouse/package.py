"""Record completed stages, create midterm report and archive deliverables."""
import csv
import io
import json
import zipfile
from pathlib import Path

from .build import ROOT, now, write_json
from .metrics import connect


def main():
    out=ROOT/'output/midterm'
    report=json.loads((out/'run_report.json').read_text(encoding='utf-8'))
    integration=json.loads((out/'integration_checks.json').read_text(encoding='utf-8'))
    snap=json.loads((out/'ads_snapshot.json').read_text(encoding='utf-8'))
    reuse=json.loads((out/'reuse_check.json').read_text(encoding='utf-8'))
    if not report['checks_passed'] or not integration['passed'] or not reuse['reused']:
        raise ValueError('Required checks not passed; do not package as completed')
    with connect(out/'warehouse.sqlite3') as db:
        tables=[dict(r) for r in db.execute("SELECT name,type FROM sqlite_master WHERE type IN('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts={r['name']:db.execute('SELECT COUNT(*) FROM "'+r['name']+'"').fetchone()[0]
                for r in tables if r['type']=='table'}
    m=report['metrics']
    def num(v): return f'{v:,}'
    def pct(v): return '—' if v is None else f'{v*100:.4f}%'
    stages=[
      ('01','需求与范围','已确认','用户此前审核并同意进入指标阶段。主体三表，行为日志扩展。','docs/01_requirements_scope.md'),
      ('02','指标字典','默认同意并落实','沿用10项业务与4类质量指标，补充原子/派生/衍生指标；CTR排行门槛可调。','docs/02a_metric_method_notes.md'),
      ('03','维度模型','已设计并实现','单曝光事实，用户、广告、日期、小时、资源位五种维度，画像未知占位用户保留ID。','docs/03_model_design.md'),
      ('04','分层及环境','已设计并实现','本机Python+SQLite标准库；明确未实现DuckDB/Hadoop/Hive或云端部署。','docs/04_layers_and_environment.md'),
      ('05','样本ETL','校验通过',f"{num(m['impressions'])}条有效样本，五层完成，{len(report['checks'])}项ETL检查通过。",'output/midterm/run_report.json'),
      ('06','看板与查询服务','SQL服务验证通过，HTTP与视觉待验收','实现日期、资源位、画像筛选及排行、交叉结果；静态结果已生成；浏览器会话失败且HTTP套接字受限，未完成端到端验收。','web/index.html'),
      ('07','复现和边界检查','数据及函数检查通过',f"两次构建指标一致，相同配置复用；{len(integration['checks'])}项数据及服务函数检查通过；HTTP状态另列。",'output/midterm/integration_checks.json'),
      ('08','中期材料与交付','已整理','保留本记录、源码、SQL、结果、检查报告、运行说明和演示提纲。','docs/07_midterm_report.md')]
    journal=out/'progress.jsonl'
    records=[{'recorded_at':now(),'step':i,'title':title,'status':status,
              'approval':'用户明确授权：继续自行逐步推进，每步默认同意，但是要保留记录',
              'result':detail,'evidence':path} for i,title,status,detail,path in stages]
    # A snapshot journal is regenerated with this package; build histories are retained separately.
    journal.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in records)+'\n',encoding='utf-8')
    progress=['# 项目推进记录', '', '记录时间：'+now(), '',
      '本轮按用户“继续自行逐步推进，每步默认同意，但是要保留记录”授权执行。此前需求和指标文件的待审核文字保留为历史版本，本记录给出当前状态，不将历史记录改写为当时已经完成。', '',
      '| 步骤 | 内容 | 状态 | 结果与依据 |','| --- | --- | --- | --- |']
    for i,title,status,detail,path in stages:
        progress.append(f'| {i} | {title} | {status} | {detail} 见 `{path}` |')
    progress += ['', '## 关键决策与原因', '',
      '1. 主体保留三张表，行为日志暂不纳入：核心曝光点击分析已有足够字段，行为时间窗口与归因不能凭空假设。',
      '2. 先开发样本流程：固定种子、逐行哈希约2%抽样，而非各表截前50万行；完整广告和画像维度保持关联覆盖。',
      '3. 暂用Python标准库和SQLite：当前可直接运行，前序依赖安装受网络限制。未伪称此前候选DuckDB和Streamlit已经部署。',
      '4. 单机星型模型并保留DWS：参考金融学习案例的方法，未套用审批累积快照和省略DWS的特例。',
      '5. 未创建付费或免费云服务器，没有接受云端试用协议，也未向GitHub发布原始数据或代码。',
      '6. 浏览器预览连接返回会话错误；本地HTTP请求又被执行环境以WinError 10013阻止。保留错误原因，改用SQL与查询服务函数检查，不以其通过冒充HTTP或视觉验收。',
      '7. 增加查询临时范围复用以减少反复维度关联；优化后重新构建并保留首次运行报告，源数据和统计结果一致。', '',
      '## 本轮执行证据', '',
      '- 首次完整样本运行：`output/midterm/history/run_01_report.json`。',
      '- 优化后完整样本运行：`output/midterm/run_report.json`。',
      '- 同配置复用：`output/midterm/reuse_check.json`。',
      '- 边界、查询服务函数检查及HTTP阻塞记录：`output/midterm/integration_checks.json`。',
      '- 全量源文件核查基线：`output/data_check/audit.json`。', '',
      '## 尚未完成', '',
      '全量正式ETL、行为日志全量检查与扩展、远程部署、生产调度、多人Git仓库设置、本地HTTP端到端和浏览器目视验收、关键操作录屏。中期可展示已完成的模型、真实样本流程及结果，不能把这些未完事项写为已实现。', '',
      '后续顺序：先由用户查看实际页面并完成视觉验收→录制中期演示→确认正式运行环境和资源→执行全量主体ETL→按需要评估行为扩展。']
    (ROOT/'docs/06_progress_log.md').write_text('\n'.join(progress)+'\n',encoding='utf-8')
    daily=['| 日期 | 源曝光记录数 | 样本曝光数 | 实际保留比例 | 样本点击率 |','| --- | ---: | ---: | ---: | ---: |']
    source=json.loads((ROOT/'output/data_check/audit.json').read_text(encoding='utf-8'))['tables']['raw_sample']
    for row in snap['daily']:
        day=row['group_key']; count=source['daily_utc8'][day]
        daily.append(f"| {day} | {num(count)} | {num(row['impressions'])} | {row['impressions']/count*100:.3f}% | {pct(row['ctr'])} |")
    resources=['| 资源位编码 | 样本曝光量 | 样本点击量 | 样本点击率 |','| --- | ---: | ---: | ---: |']
    for row in snap['resources']:
        resources.append(f"| {row['group_key']} | {num(row['impressions'])} | {num(row['clicks'])} | {pct(row['ctr'])} |")
    text=['# 淘宝展示广告投放表现分析数仓系统：中期汇报稿', '',
      '整理时间：'+now(), '',
      '## 一、项目名称与阶段目标', '',
      '项目名称：淘宝展示广告投放表现分析数仓系统的设计与实现。', '',
      '阶段目标：完成需求与指标口径、维度及分层设计，并用真实开发样本跑通ODS到ADS和初版可视化。当前是一人推进的中期原型，未部署云端，不声称完成正式全量ETL。', '',
      '## 二、小组成员与后续分工', '',
      '成员姓名与学号待填写。以下为计划职责，尚非成员已完成工作的证明：', '',
      '| 角色 | 后续职责 |','| --- | --- |',
      '| A | 需求与模型、公共维度与DDL、项目协调 |',
      '| B | 数据接入、DIM和DWD清洗、质量检查 |',
      '| C | DWS、ADS、指标校验与可选行为汇总 |',
      '| D | 看板、部署、集成测试及演示录屏 |', '',
      '## 三、项目背景与分析需求', '',
      '使用天池淘宝展示广告数据，围绕曝光到点击进行离线分析。四个主题为投放概览、广告表现、人群分析、资源位与时段。支持跨主题比较，如不同资源位中不同年龄群体的点击响应。', '',
      '主体使用广告日志、广告信息和用户画像；行为日志作为扩展。无广告费用及归因订单，不计算CPC、ROI、ROAS或广告购买转化。所有匿名编码保持原样，不构造真实名称。', '',
      '## 四、开发工具与运行环境', '',
      '| 工具 | 本阶段用途及实际状态 |','| --- | --- |',
      '| Python 3.14.3 | CSV接入、稳定抽样、调度、质量检查和HTTP接口，已运行 |',
      '| SQLite 3.50.4 | 单机分层数仓、SQL聚合和只读查询，已运行 |',
      '| HTML/CSS/JavaScript、SVG | 默认结果预览及交互页面；JavaScript语法检查通过，HTTP端到端与浏览器视觉验收受环境限制未完成 |',
      '| GitHub | 计划用于多人代码协作，尚未建立或推送本项目远程仓库 |',
      '| 云服务器 | 已了解试用资源，未创建或部署 |', '',
      '参考四份尚硅谷学习文档的数据调研、维度建模、分层开发、装载和报表方法，因业务与资源不同，未复制其整套集群、模拟数据和审批快照。', '',
      '## 五、模型与数据流', '',
      '核心事务事实表每行对应一条有效源曝光，包含曝光计数1和点击计数。周围为用户、广告、日期、小时、资源位五种维度；代理键连接用户和广告，源行号及文件哈希用于追溯。', '',
      'ODS保存源记录→DIM整理维度并补未知画像占位成员→DWD生成曝光事实→DWS复用各粒度统计→ADS形成概览、趋势、排行、人群和交叉分析结果。比率重算、用户按目标范围精确去重。', '',
      '## 六、已完成的工作和验证', '',
      f"- 全量源广告日志核查：{num(source['rows'])}条；广告信息846,811条，画像1,061,768条。该核查不等同于全量数仓ETL。",
      f"- 稳定抽样保留{num(m['impressions'])}条有效曝光，实际占源日志{m['impressions']/source['rows']*100:.4f}%，覆盖全部8天。种子为dw2026-midterm。",
      f"- 样本点击{num(m['clicks'])}次，CTR {pct(m['ctr'])}；触达用户{num(m['reached_users'])}人，点击用户{num(m['clicked_users'])}人，曝光广告单元{num(m['exposed_ads'])}个。",
      f"- 样本画像行覆盖率{pct(m['profile_row_coverage'])}，用户覆盖率{pct(m['profile_user_coverage'])}，广告信息行覆盖率100%。未知画像保留，不丢曝光。",
      f"- 已生成{sum(r['type']=='table' for r in tables)}张物理表和{sum(r['type']=='view' for r in tables)}个视图，数仓文件约{report['database_bytes']/1e6:.1f}MB。",
      f"- 优化后样本完整构建耗时{report['elapsed_seconds']:.2f}秒，是本机本次测量，不能当作云服务器或全量处理性能承诺。",
      f"- {len(report['checks'])}项ETL核对通过，{len(integration['checks'])}项复现、边界及查询服务函数检查通过。HTTP请求状态为{integration['http_status']}。首次与优化后结果相同，同配置再次运行复用，未重复插入。", '',
      '### 按日样本覆盖与结果', '', *daily, '',
      '## 七、初步分析结果', '', *resources, '',
      '两资源位在该样本中存在观察到的CTR差异，但投放人群、广告组成和时段可能不同，不能据此直接断定某个资源位具有因果优势。页面提供资源位与年龄群体的交叉结果，可进一步查看差异分布。', '',
      f"样本中已匹配画像的曝光，其消费档次属性缺失率为{pct(m['pvalue_missing_rate'])}，城市等级属性缺失率为{pct(m['city_missing_rate'])}。这是曝光加权口径，与源画像表按用户计数的54.24%、32.49%不同，不应混用。", '',
      '## 八、当前问题与后续计划', '',
      '当前样本ETL与查询服务函数已验证，HTTP请求被执行环境套接字权限阻止，浏览器预览会话连接也失败，端到端页面验收与操作录屏未完成。尚未验证正式全量ETL、服务器资源、生产调度和小组共享环境。', '',
      '后续先查看页面并录制样本演示，落实组员职责及代码仓库；再验证正式运行环境，执行全量主体ETL；最后视需求与资源评估历史购物行为扩展。', '',
      '## 九、五分钟演示顺序', '',
      '1. 介绍选题、主体三表与分析边界（约40秒）。',
      '2. 展示星型模型、五层职责及画像未知处理（约60秒）。',
      '3. 展示run_report和检查记录，说明真实抽样、总量守恒及复现（约50秒）。',
      '4. 打开看板展示概览、日趋势、资源位差异；选一天和资源位，查看响应变化（约80秒，实际查询等待时间另计，可提前缓存或录屏剪除等待）。',
      '5. 展示资源位与年龄交叉结果、质量信息及分析限制（约40秒）。',
      '6. 说明全量、协作和部署等后续任务（约30秒）。', '',
      '演示页面：运行python -m warehouse.serve后访问http://127.0.0.1:8765；静态结果可直接打开output/midterm/dashboard_preview.html，但该版本不执行筛选。']
    (ROOT/'docs/07_midterm_report.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    write_json(out/'table_inventory.json',counts)
    # Export small, directly inspectable analysis results, not raw business files.
    exports=out/'exports';exports.mkdir(exist_ok=True)
    for name, rows in [('daily',snap['daily']),('resources',snap['resources']),
                       ('age_audience',snap['audience']),('campaign_ranking',snap['ranking']),('age_resource_cross',snap['cross'])]:
        if rows:
            with (exports/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    # Keep the report snapshots small and source-independent; the database is reproducible.
    bundle_path=out/'midterm_project_bundle.zip'
    files=[ROOT/'README.md',ROOT/'.gitignore']
    for folder in ['docs','warehouse','sql','web']:
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT/'scripts/check_data.py',ROOT/'scripts/write_check_report.py',ROOT/'scripts/start_dashboard.cmd',
              ROOT/'output/data_check/audit.json',ROOT/'output/data_check/data_check_report.md']
    files += [p for p in out.rglob('*') if p.is_file() and p.suffix in ['.json','.jsonl','.csv','.html']]
    with zipfile.ZipFile(bundle_path,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(set(files)):
            z.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(bundle_path) as z:
        if z.testzip(): raise ValueError('Archive CRC check failed')
    print(json.dumps({'bundle':str(bundle_path),'bytes':bundle_path.stat().st_size,
                      'etl_checks':len(report['checks']),'integration_checks':len(integration['checks']),
                      'tables':counts},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
