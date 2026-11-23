# 官方发行包部署方案

更新日期：2026-11-16（北京时间）。用户已同意暂停Hive 3.1.3与Spark 3.3.1的源码适配，先核对能够直接使用官方发行包的组合。本文记录核对结果及调整方向，不代表平台运行验收完成。

## 部署目标

| 部分 | 选择 | 当前状态 |
| --- | --- | --- |
| Linux | Ubuntu 24.04.4 LTS x86_64 | 用户提供系统检查结果 |
| Java | 现有OpenJDK 8u512 | 用户提供版本与JAVA_HOME检查结果 |
| 存储和资源调度 | Hadoop 3.3.6的HDFS、YARN | 已解压；用户提供本地单词计数结果；分布式服务未验收 |
| SQL数仓 | Hive 4.0.1官方二进制包 | 官方包存在；本机尚未下载、安装或验证 |
| Hive计算引擎 | Tez 0.10.4官方二进制包 | 官方包存在；本机尚未下载、安装或验证 |
| 报表结果库 | MySQL，版本后续核对 | 现有MariaDB 10.11.14仍保留，不把它当作已部署MySQL |
| 展示与任务编排 | Superset、DolphinScheduler | 后续分别核对版本及依赖 |

Hive官方下载页在4.0.1发行说明中明确列出Hadoop 3.3.6、Tez 0.10.4，并鼓励Hive 4.x工作负载使用Tez。官方4.0时期安装指南说明Java 8、Hadoop 3.3.6及从tar包安装的流程；其中Tez示例仍写0.10.3，因此本项目以4.0.1发行说明为版本依据，不混抄示例。

选择4.0.1是为沿用已经检查过的Java 8和Hadoop 3.3.6，并使用官方说明的配套组合，而非随意选择最新版本。官方列出的兼容组合不保证本机配置自动正确；仍须验证Java启动、元数据库、HDFS读写、YARN上的Tez任务、关联、聚合、分区写入及失败重跑。

## 与原方案的区别

主线改为CSV → HDFS → Hive on Tez → MySQL报表库 → Superset，DolphinScheduler负责依赖编排。Spark不作为主体Hive执行引擎。Tez负责真正运行Hive SQL计算，不是以SQLite或其他本地轻量工具代替数仓。

继续参考尚硅谷手册的环境准备、数据装载、分层建模、数据同步、调度与可视化流程；SQL执行引擎与软件版本按官方兼容组合调整。广告曝光事务事实表及ODS、DIM、DWD、DWS、ADS五层设计不变。

不继续修补旧源码，也不删除旧源码、补丁备份、下载包、Maven缓存或数据库。Maven无需卸载。不要把旧版Hive 3配置或Spark依赖JAR直接复制到Hive 4目录。

## 历史适配结果

以下依据用户在对话中提供的输出记录，尚未把Ubuntu日志完整复制到本地仓库：

- Java 8、SSH与已有MariaDB服务状态检查通过。
- Hadoop 3.3.6本地MapReduce计数结果为ad=3、click=2、view=1。
- Hadoop、Hive 3.1.3二进制包、Hive 3.1.3源码及Spark 3.3.1包校验通过。
- Hive 3.1.3工作副本应用了HIVE-21777思路的LDAP依赖补丁、HIVE-26905思路的Pentaho依赖排除；调整Spark及Scala版本；修改累加器、Shuffle统计接口和一处测试Guava引用。
- 原始构建配置validate通过；修改后的Spark客户端与查询模块compile据用户反馈成功。
- 完整发行包构建在WebHCat认证过滤器的类型检查处失败，未产出已验证的完整安装包；没有执行测试或实际Hive on Spark SQL验收。
- 单模块依赖诊断显示Hadoop 3.1.0及javax.servlet接口；这不能证明整个修改项目编译时不存在类路径冲突。

## 当前下一步

1. 下载Hive 4.0.1和Tez 0.10.4二进制包与官方校验文件，保存退出状态及校验结果。
2. 解压到独立目录，核对包内依赖和启动版本，不沿用旧Hive的类库修改。
3. 准备公共模板。三个节点分散在不同地点，跨网络连接方案仍待实际测试；克隆前不复制已登录的网络身份、不初始化HDFS数据目录。
4. 分别配置并验证HDFS、YARN、元数据库、HiveServer2及Tez。按4GB虚拟机实际资源调整参数，不直接照抄示例的内存值。
5. 通过真实Hive SQL与YARN任务记录验收后，再进入广告数据分层加工。

## 官方依据和下载地址

- 版本组合：https://hive.apache.org/general/downloads/ （4.0.1发行说明）
- 安装步骤：https://hive.apache.org/docs/latest/admin/manual-installation/
- Hive包：https://archive.apache.org/dist/hive/hive-4.0.1/apache-hive-4.0.1-bin.tar.gz
- Hive SHA256：https://archive.apache.org/dist/hive/hive-4.0.1/apache-hive-4.0.1-bin.tar.gz.sha256
- Tez包：https://archive.apache.org/dist/tez/0.10.4/apache-tez-0.10.4-bin.tar.gz
- Tez SHA512：https://archive.apache.org/dist/tez/0.10.4/apache-tez-0.10.4-bin.tar.gz.sha512

本次仅更新本地项目记录，没有推送GitHub，也没有通过工具直接修改Ubuntu。
