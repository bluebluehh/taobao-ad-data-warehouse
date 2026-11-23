# 文档导航

先读根目录README和当前状态，再按下列顺序查阅。

| 文件 | 作用 |
| --- | --- |
| [当前状态](10_current_status.md) | 最新成果、检查范围和待办 |
| [需求与范围](01_requirements_scope.md) | 使用者、主题和数据边界 |
| [指标字典](02_metric_dictionary.md) | 指标公式、分母、去重与缺失规则 |
| [指标方法补充](02a_metric_method_notes.md) | 原子、派生与衍生指标 |
| [维度模型](03_model_design.md) | 粒度、事实、维度与未知成员 |
| [分层与环境](04_layers_and_environment.md) | 分层职责和工具选择 |
| [代码说明](05_code_walkthrough.md) | 模块职责与执行逻辑 |
| [推进记录](06_progress_log.md) | 决策、检查与后续修改 |
| [中期汇报稿](07_midterm_report.md) | 原始阶段汇报稿 |
| [参考方法](08_reference_methods.md) | 学习资料方法及项目调整 |
| [连接排查](09_dashboard_troubleshooting.md) | 启动、自检与故障 |

历史文档保留形成时的状态；最新进展以当前状态和后续推进记录为准，不把历史检查日期改写为新验收日期。本机output生成文件不提交，仓库examples目录提供必要汇总快照与检查证据。

## 虚拟机正式平台实施

- [现场接手和运行证据](13_vm_handover.md)
- [Hive批次装载与分层加工](14_hive_batch_runbook.md)
- [三节点配置准备](../platform/cluster/README.md)（配置模板，不是虚拟机镜像）

- [报表、同步与调度最新实施记录](15_reporting_and_scheduler.md)
- [三节点虚拟机准备及交付记录](16_three_vm_template_guide.md)
- [三人分工与独立操作指南](17_team_operations_guide.md)
- [原始数据交接与GitHub协作](18_data_and_github_collaboration.md)
- [现有SQL与项目要求复核](19_sql_requirements_review.md)

- [SQL v2更新与完整操作](20_sql_v2_usage.md)：修复清单、节点升级、期间查询、发布和回归。
