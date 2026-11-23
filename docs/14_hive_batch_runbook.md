# Hive历史批次装载与分层加工

2026-11-23。SQL v2完整入口与迁移方法见[更新指南](20_sql_v2_usage.md)。正式输入为三张主体CSV；没有原始数据时仅在validation_命名空间做技术验证，禁止把人工数据作为课程真实分析结果。

## 分层和粒度

| 层 | 表 | 粒度和用途 |
|---|---|---|
| ODS | raw_sample/ad_feature/user_profile | 保留全部原始业务字段、文件名、物理行号；按不可变批次分区 |
| DIM | ad/user_profile | 一批次一业务键一行；重复或空键必须先报错，不能任意选一行 |
| DIM | calendar/hour/resource | 业务日期、24个小时、展示位置；时间统一UTC+08:00 |
| DWD | exposure | 一条有效源曝光一条事实，允许用户和时间戳相同；保留点击标记及追溯字段 |
| DWD | rejected_exposure | 无效曝光及其原字段和明确拒绝原因，不能静默丢弃 |
| DWS | daily_stats | 单批次单日总体统计，包含精确去重用户数 |
| DWS | axis_stats | 单批次单日单分析维度单取值统计；不代表所有维度的完整笛卡尔组合 |
| DWS/ADS | daily_quality | 质量计数和Q01—Q04日结果；期间去重需另算 |
| ADS | daily_overview/daily_axis | 面向报表的日汇总及比率、贡献率 |

DWD保留常用维度属性以减少下游大表关联。画像未匹配用profile_matched=false；已匹配但性别等属性为空时保留null，并按独立类别汇总。广告未匹配仍保留曝光。匿名编码不替换成编造的品牌或商家名称；campaign_id仅在真实文件包含该字段且核对说明后解释。

## 装载

1. 保持源CSV只读；可由Windows共享目录提供文件。先确认空间，TSV会额外占本机磁盘，HDFS与ORC也占空间。behavior_log不是主体前置条件。
2. `python3 scripts/platform/stage_csv.py --source /实际主体CSV目录 --out output/staged/唯一批次`
3. 检查新目录manifest.json、三表记录数、源SHA256与预期字段。生成失败的目录没有完成清单，禁止导入。
4. `python3 scripts/platform/run_batch.py --staged output/staged/唯一批次 --batch full_201705_v1`
5. 每次执行保留output/batch-*/中的实际pipeline.sql和run.log；只有全部SQL和检查通过才写success.json。批次内容与HDFS已有清单不同时拒绝覆盖。

该过程是历史静态装载，不是实时增量采集。每个批次包含完整的日志与维度快照；查询必须指定一个批次，不能把重复加载的多个批次一起求和。

HDFS先上传到独立临时路径，再移动为固定批次路径；已有相同批次允许重跑。Hive分层按同一不可变批次覆盖计算，不追加累积。运行期间并非跨全部表的数据库事务，禁止在success.json产生前向报表发布该批次。需要修改输入时创建新批次，不能手动改旧ODS分区。本机命名空间锁防止共享维度和批次并发写入；扩为多机器调度时还需调度平台串行约束。

## 必须检查

- CSV表头、字段数量、跨行/分隔符、源文件读取期间是否变化。
- ODS记录数与整理清单一致；维度键非空且无重复。
- 源曝光=有效事实+拒绝记录；事实源文件/行号唯一；有效点击合计守恒。
- 日期/小时转换；点击标记满足0/1且clk+nonclk=1。
- DWS各分析维度的曝光/点击合计等于日总量；ADS与DWS一致。
- 全期精确用户数从DWD重算，使用08_period_query.sql，不相加日或分组去重人数。
- CTR=总点击/总曝光；分母为0时null。贡献率在Top N截取前计算；查询排行同时显示曝光量。

当前拒绝规则优先报告一项原因；价格无法解析时转为null，仍需真实数据到位后补充价格质量报告。工具拒绝错误格式整批导入，禁止悄悄跳行。

## 测试与范围

`python3 -m unittest discover -s tests -p test_platform_tools.py -v`检查文件整理与三节点配置工具。完整Hive技术验证使用validation_pipeline命名空间，样例含重复曝光、未知画像、已匹配属性缺失、未匹配广告及错误点击标记。最终通过情况以实际执行日志和接手记录为准。

三节点准备见platform/cluster/README.md。三台节点已逐台配置，尚未跨网络联机验收。旧开发机Superset、MySQL报表库、DataX和DolphinScheduler已用技术样例验证。旧机MariaDB是既有Hive元数据库；新adw101使用独立MySQL，按团队手册操作。

08/09/10分别提供期间概览、组合和质量SQL模板。通过query_metrics.py验证参数并渲染执行，最多三个维度，贡献率在门槛与Top N之前计算，可精确发布MySQL并创建对应Superset看板。完整命令与质量口径见第20手册。不要直接用旧模板的四个变量渲染新版09。

HiveServer2：`bash scripts/platform/hiveserver2.sh start`在前台运行，另外一个终端使用`bash scripts/platform/hiveserver2.sh status`检查；`stop`只停止本脚本记录且身份核对一致的进程。开发端口绑定127.0.0.1:10000，不代表组员电脑可访问。网络查询连接`jdbc:hive2://127.0.0.1:10000/default`，用户名student。集群部署时再单独配置地址及访问方式。
