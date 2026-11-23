# 三台VMware数仓节点：模板、克隆与分发完整指南

2026-11-22。当前旧Ubuntu是已验证的开发环境，新taobao-template已完成系统安装。目标是把干净模板配置一次，再完整克隆成adw101、adw102、adw103；原始数据在三节点联网并验证后导入。

## 1. 在新模板完成基础接入

只在taobao-template中操作。先重启并登录student，确保不是ISO试用桌面。主机名应为taobao-template，软件配置期间网络保持NAT。

```bash
sudo apt update
sudo apt install -y openssh-server open-vm-tools open-vm-tools-desktop ca-certificates curl rsync unzip
sudo systemctl enable --now ssh
sudo mkdir -p /opt/taobao/{software,module,data,checks}
sudo chown "$USER:$(id -gn)" /opt/taobao /opt/taobao/{software,module,data,checks}
```

sudo密码在本机输入，不发送到聊天。open-vm-tools用于VMware客体集成，不等于已经完成集群网络。

为本次模板配置加入专用公钥（不是私钥）：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
template_setup_pubkey='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP1r6MxMMwZY0SC79Zm+ThoZmRzm8BVT0zvuCcHMzSj3 taobao-template-setup'
grep -qxF "$template_setup_pubkey" ~/.ssh/authorized_keys 2>/dev/null || printf '%s\n' "$template_setup_pubkey" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

这把公钥对应的私钥只保存在旧开发机，用于当前配置。副本交付组员前撤销这项临时授权，不把私钥放入模板。

```bash
hostnamectl --static
systemctl is-active ssh
ip -br -4 addr
```

将这三条输出一次性提供。预期主机名taobao-template、SSH为active、有非127.0.0.1的IPv4。SSH服务启动本身不代表代理已能登录；公钥授权及实际连接检查通过后才能远程配置。

## 2. 由代理在接入后准备公共软件

从旧Ubuntu复用/opt/taobao/software中的已下载包，按校验文件复核，不逐节点重新下载。传输期间旧Ubuntu与新模板需在线。

公共基础是Java8、Hadoop3.3.6及必要的Hive4.0.1/Tez0.10.4客户端、项目脚本和环境配置。仅验证版本、文件完整性和本地运行能力。MySQL、Superset、DolphinScheduler等按节点职责安装，不在每台都运行一整套。

不初始化HDFS，不复制旧开发机的HDFS/YARN数据、数据库、私钥或登录状态。需要管理员权限的操作集中成可审阅脚本，由用户在新模板终端执行，不要求发送密码或设置通用免密sudo。

模板准备通过后记录版本、包校验及验证结果，正常关机再克隆。

## 3. 在Windows的VMware制作三个完整克隆

模板必须已关机，不是挂起。在VMware选中taobao-template，进入“虚拟机→管理→克隆”，选择当前关闭状态，选择“创建完整克隆”。完整克隆不依赖模板虚拟磁盘，适合分发；不使用链接克隆。

三个克隆分别保存：

- adw101：D:\虚拟机\adw101
- adw102：D:\虚拟机\adw102
- adw103：D:\虚拟机\adw103

逐个创建即可，无须同时开机。保留原taobao-template和旧开发环境。只创建或克隆没有开机的虚拟机，不会按配置预占4GB运行内存。

## 4. 逐个配置节点身份和职责

逐台启动，设置不同主机名，检查MAC地址，重新生成各自的Linux机器身份与SSH主机密钥。VMware的“我已复制该虚拟机”只处理虚拟硬件身份，不能替代Linux身份配置。身份更改和检查应在正确副本上完成，不在旧开发机上操作。

| 节点 | 职责 |
|---|---|
| adw101 | NameNode、ResourceManager、Hive及元数据库；也作为DataNode/NodeManager |
| adw102 | DataNode、NodeManager、SecondaryNameNode |
| adw103 | DataNode、NodeManager |

报表与调度放在哪台及同时启动哪些服务，按组员机器资源现场确定。配置生成器现有默认角色仅为准备模板，不能据此称三节点已经可用。

配置期间可保留专用临时公钥；在三个副本都完成配置、准备交付前撤销临时授权，清理本次配置产生的凭据和登录信息。分发前使用项目专用初始密码，组员接收后更改。每个节点保留自身唯一的SSH主机密钥，不把三个节点再次做成相同身份。

此阶段仍不初始化HDFS或装载正式数据。

## 5. 关机打包并交给组员

正常关机后，压缩对应节点的整个文件夹。必须包含.vmx和全部.vmdk分段，不能只发.vmx，也不要复制正在运行的虚拟机。

组员解压后用VMware打开.vmx；如被询问，选择“我已复制该虚拟机”。同一个节点的本地备份和组员副本不要同时作为两个节点运行。接收方网络和硬件条件可能不同，仍需实际检查。

## 6. 决定并验证三台之间的网络

同一局域网时优先测试桥接网络和设备互访；校园网或不同Wi-Fi不保证能直接互访。不同地点需先确定可靠的互联方式。各自NAT网络中的私有IP不能直接视为跨电脑可达地址。

收集三台的hostname和ip -br -4 addr输出，以及组员的物理内存、可给虚拟机分配的内存、是否同一网络。确认地址稳定后再生成实际hosts和Hadoop配置，核对SSH、HDFS/YARN端口和时间同步。不要把尚未确认的IP提前写死进模板。

网络验证通过后，才在adw101检查全新NameNode目录为空并首次初始化HDFS。只做一次，不在每台各自格式化，更不能格式化旧开发环境来凑集群。

## 7. 验收集群，再接入真实数据

- 3个正常DataNode、3个NodeManager，角色及配置一致。
- HDFS实际写入、读回及副本检查通过。
- Hive/Tez真实执行关联与聚合，YARN有任务记录。
- 报表同步和任务调度符合节点分工，失败后重跑不重复累计。
- 三张真实CSV到位后才核对字段、记录数、关联覆盖并进行全量分层；behavior_log不是主体前置条件。

只有上述运行证据齐全，才把相应阶段记为完成。技术样例看板不代表真实数据已经分析。

## 当前需要用户做的事

2026-11-23更新：已实际通过专用公钥登录student@192.168.109.129，主机名为taobao-template。公共软件准备完成：Java/Javac 8u514、Hadoop 3.3.6、Hive 4.0.1及Tez 0.10.4。三个Apache包按原有校验文件复核，并在传输后重新校验。Java安装在用户可管理的/opt/taobao/module/java-8-openjdk-amd64，复制时展开系统配置链接，无需免密sudo。

新模板已运行Hadoop本地模式Pi任务，2个输入分片、每个1000个采样，成功结束，估算值3.144；这是软件运行检查，不是集群验收或真实业务分析。新模板原始记录：/opt/taobao/checks/common-template-Ytj3Dx1V/run.log及SUCCESS；旧开发项目备份位于output/template-validation。项目代码、SQL、配置模板和操作文档已复制至新模板/home/student/taobao-ad-warehouse。交互终端自动加载/opt/taobao/common-env.sh。

没有初始化HDFS，没有复制旧数据库或运行数据，也没有在新模板启动Hadoop集群服务。尚未创建adw101、adw102、adw103实际虚拟机。临时配置公钥目前保留，须在交付前撤销。

后续进度：用户已完成三个完整克隆，并逐台启动配置。adw101、adw102、adw103均已设置各自主机名，运行personalize_clone.sh更换机器ID和SSH主机密钥，并重启后由代理实际登录验证。三台机器ID、MAC地址及ED25519主机指纹分别唯一；检查证据在output/template-validation/*-access.json及identity-summary.json。

本机NAT环境逐台观察到adw101=192.168.109.130、adw102=192.168.109.129、adw103=192.168.109.131。这些地址只用于当前配置接入，不是组员电脑上的最终网络配置。尚未进行三台同时联网验证、节点服务部署或HDFS初始化，也尚未清理临时配置公钥、制作最终分发包。第3部分克隆及第4部分身份处理已完成，节点职责服务仍需继续准备；暂不直接分发。

官方依据：
- https://ubuntu.com/server/docs/how-to/security/openssh-server/
- https://knowledge.broadcom.com/external/article?legacyId=2030609

## 8. adw101主节点准备记录与运行入口

2026-11-23已在实际adw101上准备独立MySQL 8.0.46，绑定127.0.0.1:3307，数据和独立随机凭据仅存于本节点/opt/taobao/data/reporting。Hive使用专用hive_metastore数据库和最小范围账号；initSchema及validate均通过，重启MySQL后再次validate通过。没有复制旧开发机的数据库或密码。用于命令行连接的是从旧机复用的MariaDB 10.11兼容客户端及认证插件，安装在用户目录/opt/taobao/module/mysql-ubuntu-8.0.46/usr内；数据库服务端仍为MySQL 8.0.46。

已准备Superset 6.1.0、DolphinScheduler 3.3.2和DataX选定插件。Superset使用本节点新建元数据库；调度器也使用新建元数据库，管理员默认密码已改为本节点随机密码并重新登录验证。未迁移旧技术看板、旧工作流或旧业务数据。DataX独立技术流自检3条、0失败，不代表正式数据同步已验收。

配置位于/opt/taobao/node-conf，终端环境入口为/opt/taobao/node-env.sh。Hadoop使用adw101等稳定主机名，不把当前NAT接入IP当作分发后地址；尚未修改跨节点hosts解析。已配置NameNode、ResourceManager、DataNode、NodeManager、HiveServer2的手动用户服务入口，均不启用开机自启。联网标记缺失时拒绝启动；NameNode还要求已有初始化后的VERSION文件，不会自动格式化。已有拒绝启动验证，HDFS数据目录保持不存在。

需要本机报表/调度时，在adw101登录student后手动执行：

```bash
source /opt/taobao/node-env.sh
systemctl --user start taobao-node-mysql taobao-superset taobao-dolphinscheduler
python3 /home/student/taobao-ad-warehouse/scripts/platform/verify_master_node.py
```

调度器在2虚拟CPU上启动可能需要数分钟，systemctl显示active不等于API已就绪。上述验证入口等待应用端口，再验证两个管理员登录及数据库对象，不输出密码或会话令牌。报表和调度界面分别仅供节点本机访问：http://127.0.0.1:8089/ 和 http://127.0.0.1:12345/dolphinscheduler/ui/ 。登录信息仅在节点私有的superset-login.txt及scheduler-login.txt中，勿复制到公共项目包或聊天。

为节省内存，使用后停下两个应用：

```bash
systemctl --user stop taobao-dolphinscheduler taobao-superset
```

HDFS/YARN及HiveServer2必须等三节点实际网络互通、地址稳定、身份和资源检查通过后再启动。正式分层数据库/表也尚未在这个新集群建立。当前内存预算是准备值，不代表4GB下整套平台并行运行已经验收。

下一阶段逐台完成adw102、adw103职责配置，再制定跨网络互联及交付检查。组员通常位于不同局域网，三台的VMware NAT地址不能直接作为跨电脑集群地址。正式集群加工和演示时，三台必须实际互通并同时在线；仍不在分发前初始化HDFS。

## 9. adw102工作节点准备记录

2026-11-23已实际登录adw102，复核独立身份，并完成DataNode、NodeManager、SecondaryNameNode职责配置。配置位于/opt/taobao/node-conf，环境入口为/opt/taobao/node-env.sh。没有给工作节点额外安装数据库、报表或调度服务。

verify_worker_node.py已在节点实际通过以下检查：XML配置可解析、主节点及检查点主机名正确、三个用户服务文件通过systemd验证、缺少NETWORK_VERIFIED标记时三个服务均在启动前被拒绝。三个服务最终均inactive、disabled。通过临时覆盖本地文件系统、MapReduce本地模式和临时目录执行Pi计算，结果3.144；没有生成HDFS运行目录。该本地任务不能替代三节点分布式任务验收。

节点检查记录：/opt/taobao/checks/worker-preparation/result.json、unit-validation.log、local-pi.log。旧开发项目保存无凭据的摘要副本output/template-validation/adw102-worker-result.json。YARN内存额度仍是待实际集群验证的准备值。

后续网络部署必须统一处理每台/etc/hosts中的节点映射：不能把各自127.0.1.1对应的节点名当作集群可访问地址，也不能保留同一节点名的冲突映射。必须依据三台最终可互访地址配置并验证本机及其他节点解析，之后才生成联网验收标记。当前尚未修改该项网络配置。

下一阶段：正常关闭adw102，启动adw103，提供实际主机名、IP、SSH状态及内存/磁盘输出；代理完成第三台职责配置及同类本地验证。之后集中准备跨网络互联和分发清理，不提前格式化HDFS。

## 10. adw103及三节点阶段汇总

2026-11-23已实际登录adw103，身份复核通过，完成DataNode、NodeManager配置。XML、systemd服务文件验证、联网前启动拦截、本地MapReduce Pi任务均通过；两个服务最终均inactive、disabled。没有初始化HDFS或创建其运行目录。摘要位于output/template-validation/adw103-worker-result.json，节点原始证据在/opt/taobao/checks/worker-preparation。

三台现在均已完成独立身份及各自职责的离线准备。adw101另外完成本机MySQL/Hive元数据、Superset及DolphinScheduler登录和重启复查、DataX人工流自检。三节点集群、跨电脑网络、正式分层和真实业务数据均尚未验收。VMware最终交付压缩包尚未制作，临时配置公钥也尚未撤销，不将此阶段记为“可直接分发的最终成品”。

针对组员通常位于不同局域网的情况，下一阶段拟先试用Tailscale私有互联，仍需由用户本人创建/登录账号并邀请组员。官方Linux安装说明：https://tailscale.com/docs/install/linux 。邀请方式：https://tailscale.com/docs/features/sharing/how-to/invite-any-user 。设备连接机制：https://tailscale.com/docs/reference/device-connectivity 。用户各自登录自己的账号，设备加入同一个tailnet；不共享个人登录密码。使用何种套餐以实际账号显示和官方当前条款为准。

已在adw103实际发起公开HTTPS检查：login.tailscale.com和pkgs.tailscale.com/stable返回200，tailscale.com首页请求未成功。这仅说明两个必要网页端点当前可访问，不代表VPN已安装、账号已登录或三台已经互通。摘要在output/template-validation/adw103-network-prerequisites.json。跨网络互通、直连/中继方式、速度及稳定性仍需三位组员实际联网测试。

实施顺序为：账号及同一私有网络准备→客户端安装准备和分发清理→关机打包交付→接收方启动各自节点并完成各自设备认证→收集最终私有地址→统一主机解析和互访验证→首次初始化新HDFS并启动集群。不要为了提前完成而将当前NAT地址固化、跳过认证或复制已登录的VPN状态到不同节点。

## 11. Tailscale脚本地址超时时的本地安装

用户在adw103访问https://tailscale.com/install.sh时连接超时，尚未执行安装脚本。代理已从可访问的官方https://pkgs.tailscale.com/stable/ubuntu/软件源取得Ubuntu noble签名元数据，gpgv验证签名通过，按签名中的SHA256校验软件包索引，再校验实际deb。已下载tailscale 1.104.7 amd64，SHA256为a41efd469875e27b4d8f313e07476f9bae459bafab305a3f2621ff5b5254a885。依赖iptables在adw103已安装，iproute2也已存在。

文件位于adw103的/opt/taobao/software/tailscale-offline，manifest.json记录来源、版本和校验值。已准备install_tailscale_offline.py供用户在本节点输入sudo密码后执行：

```bash
sudo python3 /home/student/taobao-ad-warehouse/scripts/platform/install_tailscale_offline.py
hostnamectl --static
tailscale version
systemctl is-active tailscaled
```

安装工具核对节点身份和包SHA256，安装已下载的本地包，启用tailscaled服务；不执行tailscale up或设备认证。不再依赖超时的install.sh地址。软件源仓库尚未添加到系统APT配置中，这一阶段仅进行已验证包的本地安装。其他两台需要先同步同一安装包目录和安装工具，不能假定它们已有文件。

adw103已由用户实际执行本地安装。代理随后通过SSH独立核实：版本1.104.7、tailscaled为active、BackendState为NeedsLogin、Tailscale地址数量为0。即客户端已安装但设备尚未登录。无凭据摘要位于output/template-validation/adw103-tailscale-install.json。adw102和adw101的客户端安装仍待进行，须先分别开机并同步离线包及安装工具。

## 12. 三台客户端完成后的交付收尾

最新进度：adw101、adw102、adw103均已安装Tailscale 1.104.7，代理逐台实际确认服务active、BackendState为NeedsLogin、设备地址数量为0。三个无凭据安装摘要位于output/template-validation/adw10*-tailscale-install.json。

收尾工具为scripts/platform/finalize_node_delivery.py，以student用户执行，不使用sudo。默认仅检查；加--finalize后停止项目用户服务，并仅移除本项目taobao-template-setup公钥对应的授权项，保留其他授权。保留节点各自机器身份、SSH主机密钥、软件及必要数据库/凭据；不清空用户历史，不删除未知目录，不修改或注销Tailscale账号。检测到HDFS运行状态、已认证的VPN设备、指定个人登录目录或用户SSH私钥时会停止，保留原文件供核实。

```bash
python3 /home/student/taobao-ad-warehouse/scripts/platform/finalize_node_delivery.py --finalize
```

只有输出state为guest_prepared_for_shutdown_and_archive后，才正常关机。节点记录保存于/opt/taobao/checks/delivery/receipt.json。收尾会撤销旧开发机的临时公钥接入，此后再次用该配置密钥建立新SSH连接会被拒绝；student本机登录和其他原有授权不受影响。后续维护需要按用户掌握的授权方式接入，不把临时配置入口留给分发副本。

Windows打包时确认VMware状态为已关机而不是挂起，压缩整个D:\虚拟机\adw102或adw103文件夹，包括.vmx、全部.vmdk分段及其他配套文件。使用现有压缩软件支持大文件的格式，或完整复制文件夹；不能只传.vmx。adw101由本人保留，组员各接收一个对应工作节点。软件已安装，不需要再次安装Ubuntu。

组员收到后解压，在VMware打开.vmx并选择我已复制该虚拟机（如有询问），登录student，首次登录后用passwd设置自己的系统密码。在各自节点运行sudo tailscale up --accept-dns=false，通过浏览器使用本人账号加入同一个项目tailnet，再提供hostnamectl --static、tailscale ip -4、tailscale status输出。副本和本地备份不要同时作为两个节点运行。HDFS仍等最终网络和角色验收通过后才首次初始化。

最终VMware压缩包需由Windows宿主机制作，当前Ubuntu代理不能据节点收尾记录声称压缩包已生成或传输完成。三台同时在线后的互访、HDFS/YARN及Hive/Tez任务仍待实际验收。

adw101已实际执行--finalize，项目服务全部停止，临时配置公钥已撤销，代理随后使用该密钥新建SSH连接被按预期拒绝。节点收尾记录已通过执行时的现有连接保存到旧开发项目output/template-validation/adw101-delivery-receipt.json。主节点可由用户正常关机；adw102、adw103仍需依次传入收尾工具并检查后撤销各自临时授权，不能据主节点的结果视为全部完成。

adw102随后也已完成实际交付收尾，节点身份及机器ID核对通过，项目服务均停止，Tailscale保持NeedsLogin，HDFS未初始化。本次配置公钥已撤销，旧配置密钥新建SSH连接被按预期拒绝；student本机登录保留。摘要位于output/template-validation/adw102-delivery-receipt.json。尚待adw103执行同类收尾，Windows压缩包均未由代理创建或验证。

最终更新：adw103也已完成实际交付收尾，临时授权撤销后的新SSH连接按预期被拒绝。三台收尾记录已统一核对：机器ID各不相同、项目服务均停止、Tailscale均未登录、旧配置密钥在三台均无法新建连接。总摘要为output/template-validation/delivery-summary.json。三台客体已准备好由用户正常关机、在Windows制作完整文件夹压缩包；代理没有创建或验证Windows压缩包，也没有确认组员已接收。三节点实际联网、SSH协作与维护授权、HDFS初始化、分布式运行及真实数据分析仍待继续。

按用户要求，后续自主分工操作统一使用docs/17_team_operations_guide.md及浏览器阅读版，分发工具包为output/delivery/team-operations.zip，内含PDF、手册、新增配置工具、公开节点身份及示例地址表。该更新尚未预装到已收尾虚拟机，三人需按新手册导入工具包。无需逐步向代理提供输出；各自自检，并在组内同步约定里程碑。新工具的本地保护逻辑已测试，三台跨网络实际运行仍由组内执行验收。
