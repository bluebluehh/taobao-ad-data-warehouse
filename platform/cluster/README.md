# 三节点配置准备

这些文件用于之后制作可分发的VMware节点，不能视为三台虚拟机已配置完成。

当前用户已在Windows完成三个完整克隆，代理逐台完成独立身份、职责配置、Tailscale安装与交付清理。三节点联网及HDFS初始化尚未完成，运行步骤见[三人操作指南](../../docs/17_team_operations_guide.md)。本目录仍保存可复现的占位配置模板，不能替代节点内/opt/taobao/node-conf配置或实际网络验收；Windows完整压缩包仍由用户制作。

以下是准备及复现流程。原单机开发环境已有HDFS、MariaDB及个人账号配置，不作为分发副本复制。

1. 使用干净Ubuntu模板，安装同版本Java8、Hadoop3.3.6、Hive4.0.1、Tez0.10.4。拷贝软件时不要拷贝当前HDFS/YARN数据、Hive密码配置、个人SSH私钥、Codex登录信息和历史记录。
2. 模板正常关机，从VMware创建三个完整克隆。分别配置唯一MAC、主机名、系统身份；不复制已经运行过的DataNode状态。保留当前单机供开发核对。
3. 依据组员实际网络填写nodes.example.json的副本。NAT的192.168.*地址不保证跨电脑可达；必须实际互访验证，不能假设地址相同就能联网。
4. 运行 `python3 scripts/platform/render_cluster.py --nodes 本地节点文件.json --out output/cluster-唯一版本` 生成配置。命令只生成文件，不改当前系统。占位地址会被拒绝。
5. 审核配置后，分别在三个目标节点备份原配置，再部署。hosts.fragment是补充内容，不是可覆盖/etc/hosts的完整文件。Hive元数据库密码在目标节点独立配置，不放入分发包。
6. 三节点时间、SSH、主机名、端口互通后再初始化全新HDFS。初始化必须检查新name目录为空、目标集群身份正确，不反复格式化。再导入Tez包、启动YARN并验收。
7. 分别检查三台DataNode、三台NodeManager、HDFS文件副本、真实Tez任务及节点重启恢复，保存日志后才能称集群完成。

节点职责：adw101承担NameNode/ResourceManager/Hive/元数据库，同时可运行DataNode和受限NodeManager；adw102承担SecondaryNameNode、DataNode、NodeManager；adw103承担DataNode、NodeManager。报表与调度服务之后按实测内存分配，不默认整套服务同时运行。

生成器使用独立`/opt/taobao/cluster-data`路径，不引用当前单机`/opt/taobao/data`目录；没有自动应用或删除功能。生成配置不等于机器身份、凭据整理、VMware克隆、分发或联网验证已经完成。

目录templates/adw101、adw102、adw103已生成可审阅配置模板，地址明确标为CHANGE_ME。它们不能直接部署；填写真实可互访IP后，应由生成器重新生成正式配置。模板目录没有私钥、密码或HDFS数据。
