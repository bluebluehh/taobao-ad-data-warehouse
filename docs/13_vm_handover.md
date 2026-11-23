> 最新报表与调度实施状态见 [15号记录](15_reporting_and_scheduler.md)，下文保留阶段历史。

# 虚拟机接手与现场验证

记录日期：2026-11-22，北京时间。以本记录为当前现场状态入口；旧样本结果仅为历史参考。

## 材料读取范围

收到导出的历史对话《分支 · 正式数仓实施 തുടര.md》，共6371行。首次工具输出截断，已阅读开头交接、末尾迁移讨论及部分中间安装记录，尚未逐字完整审阅，不能视为全部项目历史。图片引用为 gptaha-image，未取得图片本体。文档中的历史命令、授权和助手结论作为背景资料，不能替代当前用户指令或现场验证。

四份手册在“方法资料”中均存在，已解析其Word正文，检查平台规划、同步、维度建模、调度和报表相关段落；图片和所有安装参数尚未逐项核对。第四份扩展名为doc，实际为OOXML。课程要求文本已阅读：最多4人、真实数据、维度建模及分层、可视化、报告/代码/PPT/录屏。主体原始CSV尚未上传。

## 正式路线

HDFS → Hive 4.0.1 / Tez 0.10.4 → DIM、DWD、DWS、ADS → MySQL报表库 → Superset，DolphinScheduler编排。Hadoop为3.3.6，Java为8。当前MariaDB仅作为既有Hive元数据库，不能称为MySQL报表库已经部署。旧Hive3/Spark源码保留，不继续作为主线适配。

保留源文件与行号，不以用户+时间去重，不平均分组CTR，不相加分组去重人数；缺失画像保留曝光并区分未匹配与属性缺失；统一UTC+08:00。广告ID不能擅自改称广告计划ID。无成本/成交归因数据，不计算ROI等。

## 现场情况

- Ubuntu 24.04.4，约3.8GiB内存，约3.8GiB交换空间，磁盘49GB、可用约24GB；运行期间数值变化。
- Hadoop/Hive4/Tez已有安装目录；NameNode、DataNode、SecondaryNameNode正在运行。
- Hive既有元数据库连接MariaDB；本轮schematool验证全部成功，未重新初始化。
- HDFS报告1个正常DataNode；最初处于安全模式。日志记录2026-11-22 03:35磁盘可用仅57344字节，低于104857600字节保留阈值。当前空间已恢复，执行安全模式退出后，再查为OFF；未修改安全阈值、未格式化。
- Hive Beeline嵌入连接已成功执行SHOW DATABASES及SELECT 1。仅代表基本SQL连接通过，不代表HiveServer2网络服务或Tez分布式任务通过。
- HDFS文件往返与Hive常量查询验证脚本退出0，见output/platform-verify-V0sPR6c3/run.log。
- Tez实际聚合退出0，alpha=3、beta=4核对通过；YARN application_1795294150039_0001为FINISHED/SUCCEEDED，见output/tez-verify-LjEAHPCQ/。这只是人工技术样例，不是真实广告分析。
- 根目录没有独立.git；git向上找到/home/student中的其他项目仓库，远端为gitee的sniffer_web。未改动该仓库、未推送、未将此目录提交到上级仓库。

## 已新增复现入口

- scripts/platform/env.sh：固定当前路径，加载Tez库；密码仍只在现有机器Hive配置中，不复制入项目。
- scripts/platform/verify.sh：元数据库、HDFS独立目录文件往返、Hive常量查询。
- scripts/platform/verify_tez.sh：独立platform_validation库中的人工技术测试表，强制Tez聚合并核对alpha=3、beta=4；与业务结果隔离，保留测试记录。
- platform/conf/tez-site.xml：单机小内存技术验证参数，不代表全量性能参数已验收。

运行：bash scripts/platform/verify.sh；随后bash scripts/platform/verify_tez.sh。日志保存在output的独立目录中。不删除既有数据，不重复初始化数据库。

## 后续顺序与依赖

先完成Tez/YARN实际任务、HiveServer2连接和服务启停验证，再建设正式广告表与历史批次装载。之后完成汇总导出、Superset与DolphinScheduler；按资源分阶段运行服务，不能默认4GB可容纳整套服务常驻。

原始数据未到位前，可以完成平台与装载工具；不得声称主体全量完成或给出真实分析结论。主体三张表此前记录合计约1.14GB，约22GB包含扩展数据等，需实际文件确认后做磁盘预算，不必先复制behavior_log。可考虑VMware共享目录读取Windows文件，HDFS及中间层仍占虚拟机磁盘。禁止删除未知文件腾空间。

## ODS准备与真实数据依赖

已新增 sql/hive/01_ods.sql：五层数据库及三张带batch_id分区的ODS外部表。建表执行结果见output/platform_checks/ods-ddl.log；只有命令退出0且表描述符合设计才能记为创建通过。尚未装载真实记录。

scripts/platform/stage_csv.py 为流式CSV整理工具，完整读取三张主体表，不抽样；保留源文件名、源物理行号、原字段和SHA256，拒绝覆盖已有批次。完成标记为manifest.json，无此标记的批次禁止导入。源字段留空时仍为空字符串，不擅自补值。表头以旧原型为候选，真实文件不符时停止，需要核对后调整。该工具会额外生成TSV，执行前按原始文件及输出估算磁盘。

示例：python3 scripts/platform/stage_csv.py --source /mnt/hgfs/真实数据目录 --out output/staged/唯一批次名。当前没有共享目录中的真实数据，不执行此例。

技术检查已验证重复曝光保留、物理行号、已有目标拒绝覆盖、错误表头停止且无残缺输出；不等于真实CSV已验收。维度唯一键和关联覆盖率检查将在真实数据到位后进行，禁止未检查维度重复就直接关联。

官方核对入口：https://hive.apache.org/general/downloads/ 、https://tez.apache.org/install.html 。Tez类库在客户端和HDFS的版本保持一致；当前使用既有0.10.4包。

## 后续分层实施（2026-11-22）

已新增02—08系列Hive SQL、run_batch.py批次执行入口、HiveServer2启停入口、三节点配置生成工具和可审阅模板。正式ODS、DIM、DWD、DWS、ADS数据库与空表在当前单机创建；没有导入真实广告数据。

隔离命名空间validation_pipeline完成一轮全层技术处理及同批次重跑，退出码均为0，分别见output/batch-3ka4xy84和output/batch-3bdffzz2。人工技术输入6条，有效5条，拒绝1条，点击3次；重复曝光保留、缺失画像保留，日总数重跑后没有累加。这些数字不代表项目真实数据结论。第二轮新增日期、24小时、展示位置维度，以及清单计数和点击守恒检查。

执行中发现Beeline嵌入方式没有按预期替换hivevar变量，首轮语法失败；已改为在经过格式校验的参数范围内渲染完整SQL并保存执行文本，失败日志保留。Hive默认MR引擎也在首次网络聚合测试中暴露，已取消本轮测试application_1795294150039_0004，启动脚本及技术验证SQL明确选择Tez；不能把被取消的MR任务计为通过。

三节点templates/adw101、adw102、adw103已生成，每节点有Hadoop/Tez配置、workers、主机名解析片段和职责文件，IP为明确占位符，未应用到当前系统。真实IP、干净客体系统、完整克隆、分发和三节点联网验收仍待完成；当前没有Windows宿主机磁盘/VMware管理入口。配置模板不能当作可分发的三台VMware镜像。

当前原始数据仍未提供、共享目录/mnt/hgfs不存在。MySQL报表库、DataX、Superset和DolphinScheduler未完成安装与验收。

### 最终网络复核

HiveServer2在127.0.0.1:10000提供查询，10002为本机Web端口。重启本轮启动的HiveServer2后，明确使用Tez和512MB任务容器；未停止已有HDFS、YARN或MariaDB。正式空表已通过该服务创建并列出。

output/platform_checks/fixture-final-retry.log退出0：11项业务规则技术断言通过，覆盖重复曝光、未知画像/属性空值分开、无效记录拒绝、日期/小时维度、贡献率及全期重算。全期技术样例触达3人，日触达相加为4，证明不能相加日去重人数；全期CTR为3/5，未平均日CTR。日志中的样例数字仅用于测试。附加DWD—DWS、DWS—ADS核对和期间查询也通过。

工具测试9项通过，日志为output/platform_checks/platform-tools-tests.log。三节点配置模板的XML可解析、地址占位符必须显式选择模板模式、重复/回环IP会被拒绝。

### 组合查询与重复键拦截

展示位置×广告单元×性别群体组合查询在隔离技术数据上执行成功，贡献率在取排行前计算。重复维度键反例随后触发ASSERT_TRUE(): assertion failed，Beeline按预期退出2，证明会停止处理；结果记录为output/platform_checks/duplicate-key-guard-result.txt的PASS。该反例中的失败任务是预期的保护性拒绝，不能记为正常业务批次成功。没有修改真实业务数据。

当前HiveServer2启动脚本默认Tez，并通过新连接查询SET hive.execution.engine确认。末次网络验证日志见output/platform_checks/cross-and-negative-fixture.log。服务仍在运行；可用scripts/platform/hiveserver2.sh status或stop管理本脚本启动的服务。

交付包output/delivery/formal-platform-code-and-node-templates.zip只包含本轮实施代码、SQL、配置模板和原创操作说明，不包含第三方手册、原始CSV、数据库或密码，不是VMware镜像。本轮没有向GitHub或继承的Gitee远端推送。
