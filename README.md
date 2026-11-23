# 淘宝展示广告投放表现分析数仓系统

正式实施路线：三张历史CSV → HDFS → Hive on Tez → DIM/DWD/DWS/ADS → DataX → MySQL报表库 → Superset，DolphinScheduler负责任务编排和执行记录。

> 2026-11-23远程续接：adw101已更新源码并有本地测试成功回执，用户已执行报表结构升级；真实三张CSV已在adw101全量整理（曝光26,557,961、广告846,811、画像1,061,768），代理已完成真实源本地质量预检（维度无空键/重复键、全部曝光通过本次格式/时间/标签检查，画像未匹配曝光1,528,526条）。此前“真实CSV尚未提供”指旧开发机及旧阶段，不能当作当前adw101状态。三节点运行及真实Hive入仓仍未验收。adw101实测Tailscale为NeedsLogin，需重新登录；当前SSH维护使用本机NAT连接。


当前已在旧开发机跑通隔离技术数据的完整链路，完成失败后恢复及原生看板渲染验证；三台VMware完整克隆adw101、adw102、adw103已分别完成独立身份、职责配置、Tailscale安装及交付清理。用户最新确认（2026-11-23）：三台目前均关机，配置停留在软件工具环境准备完成；仅负责人节点已登录Tailscale，另两台未登录。三节点HDFS初始化与联机验收仍待完成；Windows打包和组员接收状态尚待确认。真实CSV尚未提供给实施环境，不能将技术样例作为真实数据分析或全量验收。

| 阶段 | 实际状态 |
| --- | --- |
| 旧开发机完整技术链路 | 已验证，使用人工样例 |
| 三台虚拟机身份与节点职责 | 已逐台验证、清理临时配置授权 |
| 新主节点MySQL及Hive元数据、报表与调度 | 本地初始化、登录与重启检查通过 |
| 两台工作节点 | 配置、启动拦截与本地任务通过 |
| Tailscale客户端 | 已安装1.104.7；用户确认仅负责人节点已登录，另两台未登录，当前均关机 |
| 三节点互通与分布式运行 | 待组内实际验收 |
| 真实数据全量处理与业务结论 | 待原始数据交接及执行 |

续接新增：三台更新后可用`verify_source_update.py`对照交付包核验源码并运行本地测试，生成限定验证范围的回执，详见第20份指南。此回执不代表三节点或真实数据验收。

## 最新入口

- [第四位同学制作PPT和GitHub进度阅读入口](docs/18_data_and_github_collaboration.md#9-第四名同学无需虚拟机的中期汇报协作)：无需虚拟机，含9页中期PPT提纲和证据索引。

- [SQL v2更新和完整操作指南](docs/20_sql_v2_usage.md)：八类复核缺项已修复，含三台源码更新、真实数据导入、期间筛选、排行、发布和看板步骤。
- [SQL与项目要求复核](docs/19_sql_requirements_review.md)：保留原缺项及本轮修复、回归证据；真实数据和三节点验收仍待完成。
- [三人分工与独立操作指南](docs/17_team_operations_guide.md)：组内协作、自检、联网、首次启动、数据处理与排障。
- [原始数据交接与GitHub协作](docs/18_data_and_github_collaboration.md)：数据分发、代码同步与分支流程。
- [虚拟机准备及交付记录](docs/16_three_vm_template_guide.md)：克隆、角色、客户端安装和收尾证据。
- [报表与调度实施记录](docs/15_reporting_and_scheduler.md)：版本、运行结果、服务入口、启停和待办。
- [Hive批次操作说明](docs/14_hive_batch_runbook.md)：整理、导入、分层、检查和重复执行。
- [接手及历史验证记录](docs/13_vm_handover.md)。
- [三节点配置准备](platform/cluster/README.md)：模板与真实虚拟机分发的界限。
- [文档导航](docs/README.md)。

## 旧开发机技术验证入口

在虚拟机浏览器中访问：

- Superset：http://127.0.0.1:8089/superset/dashboard/taobao-platform-validation/
- DolphinScheduler：http://127.0.0.1:12345/dolphinscheduler/

当前看板明确标注为人工技术验证。生产报表库仍为空；账号密码只保存在机器私有目录，位置见实施记录。3307是新增MySQL，3306仍为原MariaDB/Hive元数据库。

新adw101独立使用MySQL 3307保存Hive元数据和应用数据；其运行方式以三人操作指南为准，不照搬旧开发机3306配置。已筛选的无凭据阶段摘要见examples/platform_checks，完整日志和数据库保留在各执行节点。

## 代码

- sql/hive：建表、预检、明细、汇总、核对、期间和组合查询。
- sql/mysql：报表结构及仅显示已发布批次的视图。
- scripts/platform：服务、批次、导出、看板、调度及验证入口。
- platform：Tez配置、Superset版本约束、服务单元和三节点模板。
- tests：工具检查及隔离技术SQL反例。
- output：本机日志、结果、截图，禁止将原始数据或凭据提交到Git。

工具检查：`python3 -m unittest discover -s tests -p 'test_*.py' -v`。当前24项本地工具测试通过；新增团队联网工具仍需三台真实在线执行，不能把本地测试记为集群验收。

## 历史原型

原Python/SQLite代码保留在warehouse和原sql/schema.sql，供计算规则参考，不作为正式数仓方案。原首页已保存在[旧版原型说明](docs/legacy_sqlite_readme.md)，旧样本数字不能代替正式平台全量结果。

本次快照从旧开发机的源文件夹整理，该文件夹尚未建立独立Git仓库，上级目录的远端属于其他项目。同步到原GitHub仓库时请使用独立克隆，按[数据与GitHub协作指南](docs/18_data_and_github_collaboration.md)导入本轮文件，保留原有历史。
