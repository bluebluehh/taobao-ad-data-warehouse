# 第四步：分层、运行环境与实现选择

状态：自主推进记录，V0.1。

## 环境选择

当前本机Python 3.14.3内置SQLite 3.50.4，可直接使用；DuckDB、pandas、Streamlit暂未安装。前序尝试安装DuckDB时执行环境网络受限，因此中期原型使用Python标准库、SQLite和浏览器页面，先完成可运行验证。未创建阿里云资源，不产生云端费用。

这是本阶段明确的工具调整，不表示DuckDB/Parquet或Hadoop/Hive方案已经实现。SQL与业务口径分离，未来迁移需改写引擎函数并重新核对结果。SQLite是单机实现，不称为分布式数仓。学习文档的方法用于模型、分层、装载、质量及报表流程，不要求安装所有组件。

## 分层表清单

| 层 | 实现对象 | 用途 |
| --- | --- | --- |
| META | source_inventory、run_info | 源文件校验值、原始行数、样本选择规则、批次时间、运行版本 |
| ODS | ods_ad、ods_user、ods_exposure、ods_reject | 完整源维度和选中曝光的原始文本字段；格式/语义异常保留原因 |
| DIM | dim_user、dim_ad、dim_date、dim_hour、dim_resource | 公共维度和缺失画像占位成员 |
| DWD | dwd_exposure、v_exposure_detail | 有效曝光事实及便于查询的关联视图 |
| DWS | dws_daily、dws_resource_daily、dws_hourly、dws_ad_daily、dws_audience_daily | 可复用的日、时段、广告、人群汇总；其中UV仅适用于该行的精确粒度 |
| ADS | ads_overview、ads_daily、ads_resource、ads_campaign、ads_gender、ads_cross_age_resource | 默认全样本的概览、日趋势、资源位、计划、人群和交叉结果 |

动态筛选由独立ADS查询服务在明细集合上重新聚合，以确保跨日UV精确。此服务不会对DWS中的UV简单相加；持久化ADS作为默认范围结果与导出展示。当前未采用MySQL同步或DataX导出，不伪称已实现相应链路。

## 采样和装载

开发版本采用按固定规则，根据每条源记录的内容选取约2%的曝光数据（不是前若干行），在每个日期上使用相同概率。扫描一次全源文件以核实行数和SHA-256；仅将被选记录导入本版ODS。广告信息和画像均完整导入。样本不会自动放大为平台全量指标。

对数据源、采样参数和程序版本记录校验值。重跑默认复用已验证结果；显式重建在独立文件中完成，校验通过后原子替换当前数据库，失败保留原库和日志。修改种子或比例视为新版本。全量模式仅作为可运行参数提供，本轮中期先验证样本，未运行不得宣称全量ETL完成。

静态历史文件的首次装载和按日期统计不同于持续业务增量采集。保留批次与业务日期，按依赖顺序执行ODS→DIM→DWD→DWS→ADS；不启动Maxwell/Canal，也不生成虚假数据。

## 运行与协作

源码在warehouse、sql、web目录，运行结果在output/midterm。单写入者负责ETL，其他成员以只读连接或网页查看结果。GitHub只管理代码、SQL、文档及小结果，忽略原始数据和数据库。服务器资源与访问权限未落实，当前页面仅监听127.0.0.1，不向公网发布。

部署时可将同一程序放到Linux服务器验证，调整源数据路径；不硬编码本机绝对路径。若迁移引擎或引入并发写入，需要重新评估，不把本阶段原型当作生产高可用系统。
