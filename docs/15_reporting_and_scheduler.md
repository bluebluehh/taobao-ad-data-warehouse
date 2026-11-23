# 报表、数据同步与调度实施记录

日期：2026-11-22，北京时间。接续13、14号记录，本页是报表与调度的最新状态入口。

## 实际完成范围

本轮将技术验证链路推进为：HDFS → Hive on Tez 五层加工 → Hive汇总导出文件 → DataX → 独立MySQL报表库 → 原生Superset看板，并由DolphinScheduler编排和记录执行。主体原始CSV尚未提供，所有现有报表和工作流验收均使用隔离的人工技术数据，不能作为课程真实分析结论或全量性能证明。

| 组件 | 现场版本及位置 | 实际验证 |
|---|---|---|
| MySQL | Ubuntu 24.04源的8.0.46，独立用户目录解包，端口3307 | 启动、账号权限、DDL、读写与结果核对 |
| MariaDB | 原有10.11，端口3306 | 保留作为既有Hive元数据库，没有替换 |
| DataX | 官方README所指向202308发行包，选择HDFS/MySQL及流式测试插件 | 流式读写3条无失败；Hive汇总到MySQL实际同步 |
| Connector/J | 8.4.0 | DataX写入及DolphinScheduler访问MySQL；原DataX 5.1.47驱动已保存在compat-backup |
| Superset | 6.1.0，Python3.12独立环境；core 0.1.0 | MySQL元数据库迁移、管理员、数据库连接、4图查询和浏览器渲染 |
| DolphinScheduler | 3.3.2 standalone，Java8，MySQL持久元数据库 | Shell插件、依赖编排、预设失败、失败点恢复、最终成功 |

没有sudo免密权限，因此MySQL及依赖采用已校验Ubuntu包解压到项目软件目录，未通过系统包管理器覆盖现有MariaDB。MySQL最初考察的8.4二进制下载未成功，现场最终验证的是8.0.46；不能把它记成8.4。

## 数据和发布控制

正式报表库为taobao_reports，目前为空。人工技术数据在taobao_reports_validation。Superset自己的元数据位于superset_meta，调度自己的元数据位于dolphinscheduler_meta，均由独立3307实例管理。

技术批次tech_20261122_v1来自validation_pipeline。MySQL日汇总2条、分组汇总43条，与Hive导出逐字段比较，包括空值和浮点比率。只有两张表都一致才提交published_batches标记。看板只查询带发布标记的视图，未完成或失败的批次不进入看板。

DataX使用主键更新模式处理同一不可变批次，未使用TRUNCATE或追加累计。按日期、批次、分析维度和取值定义唯一键。DolphinScheduler恢复执行后复检仍为2/43条，无重复发布。

导出检查曾因MySQL可重复读事务保留旧快照而误报记录数不一致；已在检查每个DataX任务结果前结束前一个读取快照，重跑和调度内再运行均通过。失败时没有写发布标记，日志保留。

## 原生看板

在虚拟机浏览器访问：http://127.0.0.1:8089/superset/dashboard/taobao-platform-validation/

看板标题明确写“技术验证看板（非真实分析）”，包括逐日概览、广告单元曝光/点击柱状图、性别人群响应、展示位置/小时比较。性别有可靠解释的1/2转换为男/女；未匹配画像、属性缺失分开展示；匿名对象保留编码。CTR由点击总量/曝光总量计算，展示为百分比；没有费用或成交归因指标。

看板已通过真实Firefox登录与加载检查，观察到1个绘图canvas和3张原生表格（DOM含6个table），错误提示为空，且两种未知人群类别可见。截图output/screenshots/superset-technical-dashboard.png已读取核对，4个面板正常。范围为登录、加载、渲染和未知类别展示，尚未逐一验收所有筛选、下载、悬停和未来真实数据图表。

浏览器检查发现柱状图将横轴重复放入groupby，接口单独查询成功但页面报重复字段；现已修正并重新截图通过。不能把之前只有接口通过的状态当成页面通过。

Superset依赖采用6.1.0官方requirements/base.txt中关键运行版本约束，并补齐rich、cachetools。完整已安装版本保存于platform/superset/requirements.lock.txt。MySQL查询使用PyMySQL；兼容接口提供Superset类型识别所需MySQLdb常量。会话Cookie按本机HTTP方式配置，服务仅绑定127.0.0.1。

## 调度和恢复证据

本机入口：http://127.0.0.1:12345/dolphinscheduler/

技术项目“淘宝广告数仓-平台验证”中的工作流包含4个依赖任务：

1. Hive全层加工与质量检查，成功后写入下游回执。
2. 明确标注的人工故障点，首次按预期失败。
3. 从失败点恢复后执行DataX同步、全字段核对与发布。
4. 只读验证已发布报表数量及唯一性。

实例1先FAILURE，恢复后SUCCESS，4个任务最终成功。上游Hive成功结果保留，失败任务和后续任务恢复执行。完整状态转移保存在output/scheduler-validation/execution-history.json，预设失败快照在expected-first-failure.json，最终结果在success.json。它不是业务中随机失败，而是可重复检查的故障恢复测试。

DolphinScheduler使用独立MySQL持久元数据库，初始化时检查目标库为空才执行官方建表脚本，后续启动spring.sql.init.mode=never，避免重建调度数据。sudo关闭，使用当前部署用户执行；没有自动创建系统用户。3.3.2包不自带Shell插件，已按该发行版安装同版本shade插件并验证加载。

运行会话曾收到SIGTERM退出（退出码143），未把退出原因猜测为安装失败或内存不足；已配置用户级taobao-dolphinscheduler.service，由独立服务管理。没有设置开机自动启动。重启后继续检查持久记录和一次性定时触发，最终证据以timer-success.json为准，不能只以上线计划当作已触发。

## 启停与凭据

所有以下命令从项目根目录执行；前台服务需保持终端或交给服务管理：

- HDFS/YARN恢复：bash scripts/platform/hadoop_services.sh start。入口检查既有HDFS身份，绝不格式化。
- 报表MySQL：bash scripts/platform/mysql_reporting.sh start；status查看进程。
- 账号与报表结构复核：python3 scripts/platform/bootstrap_reporting.py。保留已有表和调度记录。
- Superset：bash scripts/platform/superset.sh start；status/stop管理本脚本的进程。
- 调度：systemctl --user start/status/stop taobao-dolphinscheduler.service。调度服务需先有3307 MySQL。
- HiveServer2按需：bash scripts/platform/hiveserver2.sh start；查询端口10000。

本机应用管理员用户名均为admin，密码只保存在/opt/taobao/data/reporting/superset-login.txt和scheduler-login.txt（权限600）。不在项目中保存或打印。调度默认管理员密码已替换并重新登录验证。数据库密码、Superset密钥和DataX含密码任务文件均在该机器私有目录中，不加入代码包或Git。

仅在虚拟机本机浏览器使用127.0.0.1地址；Windows上的127.0.0.1不是虚拟机。需要在Windows查看时另行使用SSH端口转发或经过验证的访问配置，不直接把服务对外公开。

## 执行入口

真实CSV到位后先用stage_csv.py整理，再run_batch.py执行。可用--receipt在output中写成功回执供调度后续任务使用。export_reports.py --run-record 成功回执.json完成DataX导出和发布；必须用Superset独立环境中的Python执行该脚本，依赖PyMySQL。

当前技术工作流故意含一次故障测试，不直接作为生产工作流反复定时执行。真实数据任务需要配置实际源目录、批次和业务日期，并去掉技术故障点。历史文件装载不是实时增量，不能用当前日期替代2017年业务日期。

## 尚未完成

- 三张真实CSV的字段复核、全量装载、数据质量报告及真实分析结论。
- 三台VMware的干净模板、完整克隆、分发、联网与集群验收。现有adw101/102/103仅为配置模板。
- 当前4GB单机服务组合使用交换空间，完整数据性能、三节点资源和容错尚未验证。
- 真实数据报表筛选与交互、最终报告/PPT/录屏及组员贡献。

三节点部署时应重配服务地址、凭据和调度任务所在节点。env.sh提供TAOBAO_HADOOP_CONF_DIR、TAOBAO_HIVE_CONF_DIR和TAOBAO_TEZ_CONF_DIR覆盖入口；DataX读取当前HDFS地址。MySQL/Superset/调度当前仍按本机开发方式部署，不能直接把含凭据、已初始化HDFS和登录状态的整台客体分发给组员。

官方核对入口：

- https://github.com/apache/superset/blob/6.1.0/pyproject.toml
- https://github.com/apache/superset/blob/6.1.0/requirements/base.txt
- https://github.com/alibaba/DataX
- https://archive.apache.org/dist/dolphinscheduler/3.3.2/
- https://dev.mysql.com/doc/refman/8.0/en/binary-installation.html

## 最终定时触发与服务管理复核

2026-11-22 16:45（Asia/Shanghai），调度器自动触发只读报表检查，实例2状态SUCCESS、commandType=SCHEDULER，证据为output/scheduler-validation/timer-success.json。临时定时计划已下线，没有留下每日重复触发。它使用固定历史技术批次，不把当前执行日期当业务日期。

MySQL、Superset和DolphinScheduler现在由用户级服务管理：taobao-report-mysql.service、taobao-superset.service、taobao-dolphinscheduler.service。三个服务文件在platform/systemd，已安装到当前用户的.config/systemd/user中；没有enable开机自动启动。Superset和调度声明MySQL依赖。前述前台脚本仍可用于诊断，已有后台服务运行时不要另起一套。

推荐启停：systemctl --user start taobao-report-mysql taobao-superset taobao-dolphinscheduler；status查看状态，stop按需停止。MySQL服务会先验证实际查询，其他服务随后启动。迁移期间正常停止的是本项目3307实例，3306 MariaDB保留运行。

本轮10项工具测试、Python语法、Shell语法和Superset依赖一致性检查通过。交付目录检查未发现本机生成的私有凭据值。尚未建立独立Git仓库或推送远端。

新增create_technical_fixture.py用于重新生成有明确标记的人工测试输入。新整理清单会继承该标记，run_batch.py拒绝将已标记的技术数据导入taobao正式命名空间。历史已运行的不可变批次清单保持原样，不为补标记去改写HDFS历史文件。新增保护检查后，工具测试共10项通过。

### 三项服务重启后的最终结果

三个用户级服务均active：MySQL、Superset、DolphinScheduler。Superset健康检查返回OK；报表复检仍为2条日汇总和43条分组汇总；调度实例1（失败后恢复）与实例2（定时触发）均保留SUCCESS，证明元数据库重启后记录仍在。原3306 MariaDB保持active。完整复核见output/platform_checks/next-stage/service-restart-recheck.json。

服务迁移中发现系统MariaDB客户端mysqladmin的shutdown协议不能用于该MySQL版本，已改用对独立实例发送SQL SHUTDOWN，用户级服务ExecStop也采用该方式。没有重建数据库、格式化HDFS或删除已有数据。
