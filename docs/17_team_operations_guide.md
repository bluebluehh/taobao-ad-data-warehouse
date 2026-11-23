# 三人分工与三节点独立操作指南

> 2026-11-23续接：新增“中期检查前执行清单”，按最新真实数据进度调整三人任务；本文Markdown为最新版本，同名旧HTML/PDF不会自动更新。SQL与报表接口已有v2修复。先按[SQL v2更新指南](20_sql_v2_usage.md)更新三台源码，仅adw101扩展报表结构，再执行本手册后续批次。旧ZIP/PDF下载副本不会自动更新。

本指南供你、组员 A、组员 B 分别操作自己掌握的虚拟机。各自按“操作与通过标准”前进，不需要把每一步输出发给代理。只有首次联网、首次启动集群和运行分布式任务需要三台同时在线；数据核对、SQL编写、图表设计和材料整理可以分开做。

当前三台均已完成软件准备、独立系统身份、节点职责配置、Tailscale 1.104.7安装和临时配置授权撤销。截至最近一次现场检查，adw101的Tailscale显示NeedsLogin，另两台尚未登录；后续重新登录结果待核实。三节点尚未联机验收。真实CSV已在adw101全量整理并完成本地预检，但尚未完成Hive真实入仓及报表发布。下文是首次分发后的实施流程；三节点整体验收要由你们按步骤实际完成。本工具包的地址校验、hosts处理和存储保护已有本地测试，跨网络操作不视为提前通过。

## 中期检查前执行清单（2026-11-23续接）

本清单根据当前状态和提供的中期汇报范例制定，是本组建议的中期目标，不将其他小组的进度当作老师硬性验收要求。检查日期尚未提供，因此按依赖顺序安排，不虚构截止日期。

### 与旧指南的调整

| 旧指南位置 | 当前变化及本轮做法 |
| --- | --- |
| 第2节虚拟机交接 | 组员接收状态未确认；未接收者先完成交接，已接收者直接核对身份，无需重新克隆 |
| 第3节旧工具包 | 改用最新sql-v2-vm-update.zip和第20份指南；adw101已更新，另两台仍需更新 |
| 第4—8节联网及集群 | 仍待三人执行，是中期前最关键的共同补项 |
| 第9节技术输入 | 改为SQL v2的17条边界样例，不能混用旧6条样例预期 |
| 第10节A整理数据 | 已由负责人完成，A改做规则审阅、质量说明及入仓对账 |
| 第11节真实批次 | 输入目录用已经存在的output/staged/real_handover_v1，不再生成source-v1 |
| 第12节B制作看板 | 先独立准备图表规格；真实发布后连接adw101制作和核对 |
| 第13节调度 | 中期先展示设计和已有技术证据；真实流程调度及故障恢复可列后续任务，不能冒充已完成 |

### 第一轮：三人各自完成，不必同时在线

**负责人/adw101**

- 核实两位组员是否已接收正确虚拟机；若未收到，按第2节关机打包对应节点交付。不得打包含真实数据和维护私钥的旧开发机。
- 分发最新源码包及配套SHA256，不再让组员使用早期team-operations包。
- 在adw101本机完成Tailscale认证（第4节），邀请两位组员加入同一个项目网络，收集三台尾网IPv4。最新现场为NeedsLogin，不能仅凭此前登录经历判定在线。
- 已完成的源码更新、28项工具测试、报表结构升级和真实CSV整理无需重复做。保存manifest和本地预检结果作为后续基线。
- 准备中期汇报的题目、背景、架构、分工、状态与后续计划；安排一次三人都能连续在线的验收窗口。

**组员A/adw102与组员B/adw103**

1. 按第2节导入各自虚拟机，执行`hostnamectl --static`和`cat /etc/machine-id`核对身份；不重新克隆或重装软件。
2. 按第20份指南备份并合并最新源码，用`verify_source_update.py --run-tests`核验。路径用自己实际下载目录，哈希用本次包的配套值；不运行主节点专用upgrade_sql_v2.py。
3. 按第4节用各自账号接受邀请、登录同一Tailscale网络，将节点名和`tailscale ip -4`结果交负责人。
4. A完成第10节的一页字段与质量说明；B完成下文图表清单与汇报素材准备。此时不需要启动Hadoop。

**B独立准备的图表规格**

| 图表 | 要回答的问题 | 数据与口径 |
| --- | --- | --- |
| 日趋势 | 曝光、点击如何随日期变化 | published_daily_overview，固定batch_id |
| 广告排行 | 哪些广告曝光/点击较多 | published_analysis_groups，固定request_id；初期按点击量排行 |
| 画像比较 | 不同编码群体响应如何 | 期间分组查询，保留未匹配/属性缺失，CTR用点击/曝光 |
| 质量概览 | 画像和广告关联覆盖如何 | published_analysis_quality，同一request_id；Q04分母为匹配画像曝光 |

先写图标题、分组、筛选和指标，不编造真实图表结论。全期触达从期间查询取得，不能累加每日去重人数。

### 第二轮：三台同时在线，完成基础联机验收

1. 负责人合成同一份`platform/team/nodes.json`，三人照第5节配置hosts和资源预算，分别verify；三台均PASS才继续。
2. 负责人核实新集群存储状态，满足保护条件时按第6节首次初始化一次。A、B不格式化任何存储。
3. 按第7节顺序启动：负责人启动NameNode/DataNode；A启动DataNode/SecondaryNameNode；B启动DataNode；再启动ResourceManager及三台NodeManager。
4. 负责人保存`hdfs dfsadmin -report`和`yarn node -list -all`，确认3个DataNode与3个RUNNING NodeManager。A/B保留本机服务active截图或日志。
5. 负责人按第8节验收实际HDFS三副本读写与Tez作业；A/B保持在线，检查自己节点日志。网页能打开不等于任务通过。
6. 按第9节完成v2技术批次；A核对有效9、拒绝8、点击4及未知成员保留，B协助保存YARN成功任务及技术报表证据。

中期基础目标：上述验收通过，加上三人的设计/质量/展示材料，即能有证据支持“已组建并验证三节点集群”。如果尚未完成，必须写“软件环境准备完成，联机验收进行中”。

### 第三轮：争取在中期前完成真实链路演示

基础验收后，建议继续完成一个完整真实批次，使汇报同时有真实分析成果。若检查前时间不足，应如实列入后续计划；不把本建议当成已知课程硬性门槛。

- 负责人按第11节从real_handover_v1运行真实批次，保留成功回执；已有批次需先核查定义是否相同，不机械覆盖或改名。
- A对照本地源基线复核Hive结果：曝光26,557,961、点击1,366,056、触达1,141,729、广告单元846,811及画像关联情况；这里是预期对账基线，运行前不能称Hive结果。
- 负责人DataX导出三张日表、完成全字段核对，再按第20份指南发布精确期间查询并生成原生看板。仅在发布成功后将范围ID及批次交B。
- 负责人按第12节开启私有报表访问并给B独立账号；B从自己的Ubuntu浏览器访问adw101，完成至少日趋势、广告/画像比较、质量概览，记录对应批次或request_id，保存截图。
- 全量加工期间先停Superset与调度，按4GB节点资源分阶段运行；A/B全程保障计算节点在线。真实运行耗时由此次执行记录，不套用旧开发机或Python预检时间。

### 中期材料由谁交付

| 人员 | 中期前交付物 | 怎么证明完成 |
| --- | --- | --- |
| 负责人 | 汇报PPT/讲稿；架构与模型；三节点验收汇总；已完成/待办列表 | 截图、日志和回执能相互对应；4类验证状态分别说明 |
| A | 一页数据字段/质量规则；关联及缺失说明；adw102运行记录；真实对账表（若已运行） | 引用源清单、实际SQL及同批次结果；未验收项留空或标待完成 |
| B | 图表规格；adw103运行记录；演示步骤与截图；真实看板（若已发布） | 图表注明数据性质、批次/范围；每张图一条结论及限制 |

三人最后一起试讲：负责人讲需求/模型/架构/进度，A讲数据质量与处理，B讲图表和演示。中期先保证材料一致、集群证据可靠；最终报告、完整录屏、真实流程定时调度与故障恢复作为后续完善项，除非老师另有明确要求。

## 1 分工与协作方式

| 人员 | 掌握节点 | 主责 | 可独立开展的工作 |
|---|---|---|---|
| 你，负责人 | adw101 | 网络地址表、NameNode、ResourceManager、Hive元数据库、批次执行与总验收 | 数据装载、分层SQL集成、运行日志、调度和成果汇总 |
| 组员 A | adw102 | DataNode、NodeManager、SecondaryNameNode | 原始字段核对、完整CSV整理、维度唯一性和业务质量核对 |
| 组员 B | adw103 | DataNode、NodeManager | 报表设计、Superset图表、业务解读、演示截图和录屏素材 |

检查点服务用于合并HDFS元数据，不是NameNode热备。组员 B负责设计和编辑图表，但报表服务及MySQL仍在adw101上，避免重复部署和复制数据库。

三人共享一个项目群或共享表，只同步下面五个里程碑即可：

1. 收到虚拟机，主机名正确。
2. 加入同一个Tailscale网络，提供本节点的Tailscale IPv4给组内地址表。
3. 每台基础网络检查显示PASS。
4. 各自服务已启动；负责人确认3个DataNode、3个NodeManager。
5. 技术批次或真实批次通过，并共享对应日志位置和实际结论。

阅读顺序：负责人按第2至9节完成首次上线，再执行第11至13节；组员A重点执行公共步骤与第10节；组员B重点执行公共步骤与第12节。三人都保留第14节作为排障表。

需要分布式加工时提前约定时间，三台保持开机、联网且不休眠。运行结束前不要擅自关闭自己的节点。负责人不在线时，组员仍可在本机核对数据、编写SQL和设计报告，但不能依赖已关闭的集群做查询。

## 2 分发与导入虚拟机

负责人在三台正常关机后，分别打包整个D:\虚拟机\adw102和D:\虚拟机\adw103文件夹。必须包含.vmx、所有.vmdk分段及配套文件。压缩包尚需你在Windows制作；不要压缩运行或挂起中的虚拟机。

组员完整解压后，在VMware中打开文件夹内的.vmx。如出现询问，选择“我已复制该虚拟机”。每台初始配置为4GB内存、2个虚拟CPU，网络先保持NAT。每人只运行自己分配的一个节点。

用student及负责人告知的初始密码登录Ubuntu，打开终端：

```bash
hostnamectl --static
cat /etc/machine-id
passwd
```

主机名必须与分配一致。passwd用于设置自己掌握的系统密码，不改变Tailscale账号或数据库账号。不要再创建不同角色的克隆，也不要同时启动同一节点的本地备份和接收方副本。

三台交付时的身份如下，机器ID应与此一致：

| 节点 | 机器ID |
|---|---|
| adw101 | 3157d0a1eca94edb8e9db7bc0aaf4d5c |
| adw102 | e7d7c43a4c3549d2b0728ddc6c317a0e |
| adw103 | a76e7e25479841efa5924639c0e4e4fa |

若不一致，先核对是否打开了正确的虚拟机文件夹。不要为了让检查通过而直接修改记录或格式化磁盘。

## 3 三人安装同一份操作工具包

本指南和后续配置工具是新增文件，原虚拟机中尚未预装这份更新。负责人将最新sql-v2-vm-update.zip及配套SHA256交给组员。更新以第20份指南为准；下文team-operations.zip是早期工具包说明，不再作为本轮升级入口。工具包不含数据库密码、个人私钥、原始CSV或虚拟磁盘。

先将ZIP文件放进各自Ubuntu的/home/student/Downloads。可以使用共享文件夹或现有文件传输方式。如果需要从Windows传入，可在Ubuntu执行hostname -I查看本机NAT地址，再在Windows PowerShell执行下例，替换文件路径和本机虚拟机地址：

```powershell
scp "C:\Users\你的用户名\Downloads\team-operations.zip" student@192.168.109.131:/home/student/Downloads/
```

上面的IP只是第三台原先地址示例，接收方必须使用自己当前虚拟机的地址。首次SSH提示可与Ubuntu本机执行ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub得到的指纹核对；输入的是自己刚设置的Ubuntu密码。

然后在Ubuntu执行：

```bash
unzip -o /home/student/Downloads/team-operations.zip -d /home/student
python3 /home/student/taobao-ad-warehouse/scripts/platform/team_network.py --help
```

看到configure、verify、resources、init-namenode、report-access等操作说明即表示工具已到位。解压仅新增或更新本工具包列明的手册、工具和公开身份文件，不含运行配置或数据。

## 4 三人加入同一个Tailscale网络

负责人在Windows浏览器进入https://console.tailscale.com/，登录自己的账号。进入Users，选择Invite external users，为两位组员分别生成普通成员邀请。组员各自用自己的账号接受邀请，加入负责人创建的同一个项目网络。

每人在自己的Ubuntu中执行：

```bash
sudo systemctl enable --now tailscaled
sudo tailscale up --accept-dns=false
```

在浏览器打开终端显示的认证网址，用本人账号登录；如需要选择网络，选择同一个项目网络，而不是各自独立创建的网络。密码、验证码和认证网址不放进群里的公开记录。

认证后执行：

```bash
hostnamectl --static
tailscale ip -4
tailscale status
```

通过标准：有一个100.x.x.x形式的Tailscale IPv4，控制台能看到该节点属于同一个项目网络。本阶段只需向组内共享“节点名和IPv4”，不用把完整输出发给代理。Windows无需安装Tailscale；后续直接在Ubuntu浏览器中访问集群界面。

负责人把三台的实际地址合成同一份地址表。不要填写192.168.109.x等VMware NAT地址，也不要照抄别人的100.x示例地址。

## 5 三人使用同一份地址表

每人首次执行：

```bash
cp -n /home/student/taobao-ad-warehouse/platform/team/nodes.example.json /home/student/taobao-ad-warehouse/platform/team/nodes.json
nano /home/student/taobao-ad-warehouse/platform/team/nodes.json
```

将文件中的三处说明文字替换为本组真实地址，保留引号、逗号和大括号。结构如下：

```json
{
  "adw101": "负责人的实际Tailscale IPv4",
  "adw102": "组员A的实际Tailscale IPv4",
  "adw103": "组员B的实际Tailscale IPv4"
}
```

三人必须使用完全相同的内容。在nano中按Ctrl+O、回车保存，Ctrl+X退出。

每人执行：

```bash
sudo python3 /home/student/taobao-ad-warehouse/scripts/platform/team_network.py configure
python3 /home/student/taobao-ad-warehouse/scripts/platform/team_network.py resources
```

configure会备份并更新本机/etc/hosts，去掉节点名指向127.0.1.1等旧地址的冲突，保留其他主机记录。如果UFW已启用，仅允许本组另外两台通过tailscale0访问；不会关闭整个防火墙。

resources设置初始保守预算：adw101的YARN容器预算512MB，另两台各1024MB，单容器上限1024MB；守护进程和其他服务使用剩余内存。它还让DataNode、NodeManager对外公布项目主机名，避免把VMware NAT地址提供给远程节点。修改前Hadoop/Hive服务必须停止。保留物理内存检查，仅关闭Java容易触发的虚拟内存比率检查。这是首次验收预算，不能据此承诺4GB可同时运行所有应用和全量任务。

首次三人均在线后，各自执行：

```bash
python3 /home/student/taobao-ad-warehouse/scripts/platform/team_network.py verify
```

通过标准：三台均显示“PASS 主机解析、SSH端口、节点身份”，最后显示“PASS 基础网络验收”。工具会核对交付时记录的SSH主机公钥，不需要输入其他组员的系统密码。它不会建立免密登录，也不会恢复已经撤销的临时维护密钥。

通过后，本机生成/opt/taobao/node-conf/NETWORK_VERIFIED。每人只需在群里发“101网络PASS”或对应节点的PASS。失败则按第14节自行排查；禁止手动创建空标记文件绕过检查。此检查覆盖基础连接，Hadoop端口和真实任务要在服务启动后继续验收。

## 6 首次初始化 仅负责人执行一次

必须先满足：三台基础网络均PASS，三人确认可以保持在线；adw101没有旧HDFS数据。组员A、B不执行任何格式化命令。

负责人在adw101执行：

```bash
python3 /home/student/taobao-ad-warehouse/scripts/platform/team_network.py init-namenode --confirm-first-initialization
```

通过标准：显示“PASS 首次NameNode初始化完成”。工具只允许交付身份匹配的adw101执行，只允许指定的新NameNode目录及DataNode目录为空；不会使用-force，也不会操作旧开发机的数据。已有VERSION身份文件时会跳过格式化。

之后永久使用日常启动步骤，不再运行初始化。若初始化中断并留下非空目录，工具会停止；保留目录和/home/student/taobao-ad-warehouse/output/team/first-format.log，先核查，不能删目录强行重来。

## 7 三人按顺序启动HDFS与YARN

首次和以后每次集群启动均按本节执行。先保证三台在线、Tailscale已登录且各自verify通过。

负责人在adw101执行：

```bash
source /opt/taobao/node-env.sh
systemctl --user start taobao-namenode taobao-datanode
systemctl --user is-active taobao-namenode taobao-datanode
```

两项均active后，在群里通知“主节点HDFS已启动”。

组员A在adw102执行：

```bash
source /opt/taobao/node-env.sh
systemctl --user start taobao-datanode taobao-secondarynamenode
systemctl --user is-active taobao-datanode taobao-secondarynamenode
```

组员B在adw103执行：

```bash
source /opt/taobao/node-env.sh
systemctl --user start taobao-datanode
systemctl --user is-active taobao-datanode
```

各自active后通知群内。负责人在adw101执行：

```bash
source /opt/taobao/node-env.sh
timeout 180 hdfs dfsadmin -safemode wait
hdfs dfsadmin -report
```

通过标准：安全模式退出，Live datanodes为3。若不足3，先处理缺失节点，不开展任务。

然后负责人执行：

```bash
systemctl --user start taobao-resourcemanager taobao-nodemanager
```

通知两位组员，各自在自己的节点执行：

```bash
systemctl --user start taobao-nodemanager
systemctl --user is-active taobao-nodemanager
```

最后负责人执行：

```bash
source /opt/taobao/node-env.sh
yarn node -list -all
```

通过标准：3个节点均为RUNNING。可以在adw101的Ubuntu浏览器查看http://adw101:9870/和http://adw101:8088/。Windows浏览器没有加入Tailscale时不要用它测试这些地址。

本方案由每人在本机启动用户服务，不依赖start-dfs.sh或远程免密SSH。需要远程维护时再由组员授权自己的新项目公钥，不恢复旧配置入口。

## 8 负责人验收HDFS副本和Tez

在adw101执行：

```bash
source /opt/taobao/node-env.sh
hdfs dfs -mkdir -p /tmp /user/student /user/hive/warehouse /apps/tez/0.10.4
hdfs dfs -chmod 1777 /tmp
check_file=$(mktemp /tmp/adw-check-XXXXXXXX)
printf 'team-cluster-check\n' > "$check_file"
check_id=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
check_dir="/user/student/checks/$check_id"
hdfs dfs -mkdir -p "$check_dir"
hdfs dfs -put "$check_file" "$check_dir/input.txt"
timeout 180 hdfs dfs -setrep -w 3 "$check_dir/input.txt"
cmp "$check_file" <(hdfs dfs -cat "$check_dir/input.txt") && echo "PASS HDFS读回一致"
hdfs fsck "$check_dir/input.txt" -files -blocks -locations
```

通过标准：读回一致；fsck为HEALTHY，并显示该块实际有3个存活副本。setrep命令卡住或超时通常意味着存储节点不足；不要降低副本数来冒充三节点通过。

准备Tez及Hive元数据连接：

```bash
source /opt/taobao/node-env.sh
if ! hdfs dfs -test -e /apps/tez/0.10.4/tez.tar.gz; then
  hdfs dfs -put "$TEZ_HOME/share/tez.tar.gz" /apps/tez/0.10.4/tez.tar.gz
fi
systemctl --user start taobao-node-mysql
python3 /home/student/taobao-ad-warehouse/scripts/platform/init_node_metastore.py
export HADOOP_HEAPSIZE_MAX=512
bash /home/student/taobao-ad-warehouse/scripts/platform/verify_tez.sh
```

通过标准：Hive元数据validate通过；最后显示Tez grouped totals PASS，同时YARN里有相应成功任务记录。这是人工基础设施测试，不是业务结论。日志保存在/home/student/taobao-ad-warehouse/output/tez-verify-*。

本项目批次脚本使用本地嵌入式Hive入口，此阶段不必额外启动taobao-hiveserver2，避免在4GB主节点上同时保留两个Hive进程。Superset、DolphinScheduler也先保持停止。

## 9 技术批次 负责人执行 组员核对

先在adw101运行完整分层的人工技术批次，验证业务规则后再导入正式数据：

```bash
cd /home/student/taobao-ad-warehouse
source /opt/taobao/node-env.sh
export HADOOP_HEAPSIZE_MAX=512
python3 /home/student/taobao-ad-warehouse/scripts/platform/create_sql_v2_fixture.py --out /home/student/taobao-ad-warehouse/output/team-fixture-01
python3 /home/student/taobao-ad-warehouse/scripts/platform/stage_csv.py --source /home/student/taobao-ad-warehouse/output/team-fixture-01 --out /home/student/taobao-ad-warehouse/output/team-staged-01
python3 /home/student/taobao-ad-warehouse/scripts/platform/run_batch.py --staged /home/student/taobao-ad-warehouse/output/team-staged-01 --batch team_tech_01 --namespace validation_team --receipt /home/student/taobao-ad-warehouse/output/team-validation-success.json
/opt/taobao/module/superset-6.1.0-venv/bin/python /home/student/taobao-ad-warehouse/scripts/platform/export_reports.py --run-record /home/student/taobao-ad-warehouse/output/team-validation-success.json
```

首次执行创建fixture、staged目录。重复验收时不重复创建这两个目录，直接用同一批次重跑run_batch和export_reports；创建工具拒绝覆盖已有目录是正常保护。不要换命名空间把人工数据装入taobao。

通过标准：出现批次成功回执；同步结果published为true、三张日表all_fields_reconciled为true。v2人工输入为17条曝光源记录，有效曝光9条、拒绝8条、点击4次；这些是测试预期，不代表真实数据。组员A核对重复曝光保留、未匹配画像与属性缺失区分、点击和曝光守恒。组员B用技术报表库练习图表，并明确标“技术验证”。

若已有旧6条输入的team-fixture-01或team-staged-01，保留旧目录，改用新的v2目录及批次名；不要把旧输入和新预期混用。

回执和日志留在执行节点，无需提交给代理。负责人在群里同步“技术批次PASS”和本次batch_id即可。

## 10 组员A的数据质量复核任务（按当前进度调整）

真实数据已由负责人在adw101完整整理和本地核查。组员A不需要重新接收三张完整CSV、再整理一次或重复传回TSV；原第10节的重复整理分工由本节替代。

1. 阅读`docs/02_metric_dictionary.md`、`docs/03_model_design.md`和`examples/platform_checks/adw101-real-source-preflight.json`。
2. 按清单核对：曝光26,557,961；广告846,811；画像1,061,768。说明源文件SHA256用途、尾空格表头映射及Asia/Shanghai业务期如何确认。
3. 阅读`sql/hive/03_preflight.sql`、`04_dim_dwd.sql`、`05_quality.sql`和`07_checks.sql`，写清维度唯一性、左关联、拒绝原因、层间守恒及结果唯一性规则。
4. 形成一页数据质量说明，区分“本地源文件核查结果”和“待Hive入仓验证”。引用本次结果：两张维度空键/重复键均0；广告匹配曝光26,557,961；画像匹配曝光25,029,435，未匹配1,528,526；画像匹配用户1,061,768，未匹配79,961。不能把源画像表缺失率写成曝光加权Q04。
5. 联机执行时维护adw102服务，负责人提供Hive批次回执后，对照同批次结果复核曝光、点击、拒绝数及覆盖率，记录差异与处理结果。原文件或口径变化时不能强行套用旧基线。

交付：adw102源码及本地测试回执、网络PASS记录、DataNode/NodeManager/SecondaryNameNode运行证据、一页字段与质量规则说明、真实批次对账结果（若当时未运行则明确待验收）。本次未检查完全重复曝光行，不得写成已验证无完全重复。

## 11 负责人执行真实批次

前提：技术批次通过、组员A的源文件与字段核对完成、三台同时在线、HDFS与YARN检查正常。只运行一个全量批次，先停报表和调度服务：

```bash
systemctl --user stop taobao-superset taobao-dolphinscheduler
cd /home/student/taobao-ad-warehouse
source /opt/taobao/node-env.sh
export HADOOP_HEAPSIZE_MAX=512
python3 /home/student/taobao-ad-warehouse/scripts/platform/run_batch.py --staged /home/student/taobao-ad-warehouse/output/staged/real_handover_v1 --batch real_v1 --namespace taobao --receipt /home/student/taobao-ad-warehouse/output/real-v1-success.json
/opt/taobao/module/superset-6.1.0-venv/bin/python /home/student/taobao-ad-warehouse/scripts/platform/export_reports.py --run-record /home/student/taobao-ad-warehouse/output/real-v1-success.json
```

通过标准：真实批次成功回执存在；ODS、DIM、DWD、DWS、ADS相关断言均通过；报表同步published为true且all_fields_reconciled为true。仅看到进程启动、目录存在或部分表有记录不能记为全量成功。

同一内容失败后重跑仍使用real_v1，禁止随意更换批次名造成多版本累计。源内容变化时采用新批次并保留原始记录，报表明确选择一个批次，不把同一份数据的多个装载版本相加。4GB虚拟机的全量速度和稳定性仍要由真实运行确认。

需要核对全期去重或组合分析时，使用项目已有sql/hive/08_period_query.sql及09_cross_analysis.sql的规则，并正确替换命名空间和批次变量；不能直接把日去重人数相加。未经变量渲染的SQL不直接粘贴执行。

## 12 组员B配置报表并独立制作图表

数据同步完成后，负责人在adw101执行以下一次性私有访问配置：

```bash
systemctl --user stop taobao-superset
python3 /home/student/taobao-ad-warehouse/scripts/platform/team_network.py report-access
systemctl --user start taobao-node-mysql taobao-superset
```

报表同时监听本机127.0.0.1:8089和adw101的实际Tailscale地址，不监听所有公网接口。负责人在自己的Ubuntu浏览器打开http://127.0.0.1:8089/，管理员登录信息仅在本机/opt/taobao/data/reporting/superset-login.txt；自行查看，不把密码文件或凭据JSON放进群文件。

负责人在Superset的用户管理中为组员B创建独立账号，例如report_b，分配Alpha角色，私下交付初始密码。该角色用于本项目图表制作，数据库连接仍采用只读report_reader账号。

组员B在adw103的Ubuntu浏览器打开：

http://负责人实际Tailscale地址:8089/

Windows未安装Tailscale时，用Ubuntu浏览器访问。组员B用自己的报表账号登录，编辑图表，不必向负责人反复索要查询截图。

负责人在Superset的数据库连接页面新建连接，选择Other或SQLAlchemy URI入口。正式数据库选择taobao_reports，技术练习库选择taobao_reports_validation；不要使用旧工具中固定技术批次过滤器创建正式看板。需要生成正式库的只读连接字符串时，仅在adw101本机终端执行下列命令，输出只粘贴到本机Superset的SQLAlchemy URI字段：

```bash
/opt/taobao/module/superset-6.1.0-venv/bin/python - <<'LOCALPY'
import json
from pathlib import Path
from urllib.parse import quote_plus
c=json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
print('mysql+pymysql://report_reader:'+quote_plus(c['report_reader'])+'@127.0.0.1:3307/taobao_reports?charset=utf8mb4')
LOCALPY
```

该输出含只读数据库密码，不上传到共享文档。技术库使用相同方式，将最后的数据库名改为taobao_reports_validation。

建议使用已建的发布视图：

| 数据集 | 用途 |
|---|---|
| published_daily_overview | 逐日曝光、点击、日触达与关联缺失概览 |
| published_daily_axis_labeled | 广告单元、人群、位置、小时等维度分析，带中文缺失标签 |

组员B独立完成以下图表，每张明确过滤batch_id，维度表还要过滤axis，避免重复累计不同分析维度：

1. 按日期展示曝光和点击的趋势。
2. 按广告单元展示曝光、点击及加权点击率。
3. 按性别、购物水平等已有编码比较群体响应。
4. 按展示位置或小时比较曝光与点击表现。
5. 单独展示画像未匹配、广告未匹配及属性缺失的情况。

指标规则：CTR为SUM(clicks)/NULLIF(SUM(impressions),0)，不能平均各组CTR；全期触达不能累加日触达；TopN贡献率分母取完整集合；缺失关联仍保留曝光；不根据本数据虚构ROI、CPC、ROAS或购买归因。没有明确字典的年龄、城市编码不自行编成真实区间或名称。

组员B交付看板地址、筛选批次、每张图的一句话结论和限制、截图及录屏素材。负责人负责核对与真实批次回执一致。看板共用本节点数据库，节点关闭后界面不可访问；截图和报告可离线整理。

## 13 调度与日常启停

先完成一次真实或完整技术批次，再做调度练习。主节点4GB内存下，初期把“全量加工”和“报表展示、调度配置”分阶段进行，不默认整套同时运行。

负责人需要进入调度界面时：

```bash
systemctl --user start taobao-node-mysql taobao-dolphinscheduler
```

在adw101的Ubuntu浏览器打开http://127.0.0.1:12345/dolphinscheduler/ui/。密码仅在本机/opt/taobao/data/reporting/scheduler-login.txt。冷启动可能数分钟，systemctl显示active不等于网页已经就绪。

先在界面建立技术验证项目和一个Shell任务，使用node-env.sh环境，调用已经验收的validation_team批次，再测试失败后的恢复。不要直接运行旧固定批次的技术工作流生成器来当成正式生产调度。三台经常不在线时先手动触发，不启用无人值守的全量定时任务。

每次重新开机都先确保三台Tailscale在线，必要时重新verify，然后按第7节启动。绝不再次格式化。地址变化时，先停服务，更新三人共同地址表，再重复configure、verify；报表私有监听也要重做report-access。

结束加工前由负责人执行yarn application -list -appStates RUNNING,ACCEPTED，确认没有运行中或等待中的作业。按以下顺序关闭：

负责人先在adw101停止计算入口和展示服务：

```bash
systemctl --user stop taobao-dolphinscheduler taobao-superset taobao-hiveserver2
systemctl --user stop taobao-resourcemanager taobao-nodemanager
```

两位组员分别停止各自服务：

```bash
# 仅adw102执行
systemctl --user stop taobao-nodemanager taobao-secondarynamenode taobao-datanode
```

```bash
# 仅adw103执行
systemctl --user stop taobao-nodemanager taobao-datanode
```

两位组员通知停止完成后，负责人停止剩余服务：

```bash
systemctl --user stop taobao-datanode taobao-namenode taobao-node-mysql
```

随后各自sudo poweroff正常关机。不要挂起正在运行的集群作为常规结束方式，不删除/opt/taobao/cluster-data。

## 14 常见问题自行排查

| 现象 | 先检查与处理 | 恢复标准 |
|---|---|---|
| Tailscale显示NeedsLogin | 执行sudo tailscale up --accept-dns=false，确认本人账号加入正确项目网络 | tailscale ip -4有地址，status能看到组内节点 |
| SSH端口检查失败 | 对方是否开机、tailscaled是否active、是否同一网络、地址表是否一致；执行tailscale ping 对方实际IP和ip route get 对方实际IP | 实际路由经过tailscale0，工具verify通过 |
| 三台账号在同网络但仍不能互访 | 负责人检查控制台访问策略是否允许三台之间通信；Hadoop包含动态RPC端口，需要这三台之间完整通信，而非只放行网页或22端口；保留其他网络规则，只添加本组三地址的互访许可 | 三人verify通过，后续Hadoop实际端口也能连接 |
| 主机解析仍是127.0.1.1或192.168地址 | 检查共同地址表后重新sudo执行configure；用getent ahostsv4 adw101检查 | 节点名只解析到约定Tailscale IPv4 |
| SSH主机身份不符 | 核对虚拟机目录、hostname、machine-id；在目标机执行ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub，与platform/team/node-identities.json核对 | 确认正确副本；不自动接受陌生主机身份 |
| 服务提示NETWORK_VERIFIED缺失 | 三台在线后各自运行verify，不手工touch标记 | verify最后显示PASS |
| NameNode已有VERSION | 说明已有身份，使用日常启动，不再初始化 | 保留原数据并正常启动 |
| DataNode不能加入或提示clusterID不同 | 停止该DataNode，对比其日志与主节点身份；检查是否误用了旧数据或错误副本 | 修复配置或使用正确数据目录；禁止直接删目录、重新格式化主节点 |
| Live datanodes不足3 | 缺失节点检查taobao-datanode服务、主机解析、尾网连接；首次已运行resources使DataNode使用主机名 | 3个存活DataNode，实际副本达到3 |
| YARN节点UNHEALTHY或不注册 | 查看NodeManager日志、磁盘空间、hostname映射；不要禁用健康检查掩盖磁盘不足 | 3个RUNNING节点，磁盘状态正常 |
| 容器因内存被终止 | 确认只运行一个批次，停止报表/调度，观察free -h；保留物理内存检查；依据实际物理内存减少并发或调整预算 | 不再被OOM终止，任务成功 |
| Tez卡在ACCEPTED | 先检查3个NodeManager、队列资源和AM内存；resources已给初始AM额度，确认三人都已执行 | 任务进入RUNNING并成功 |
| Hive无法连接元数据库 | adw101启动taobao-node-mysql，运行init_node_metastore.py验证，不删除mysql-data或重设账号 | validate通过 |
| stage_csv拒绝目录或表头 | 已有输出目录不覆盖；核对是否重复整理、真实表头是否与源规范一致 | manifest存在且哈希匹配 |
| 同批次HDFS清单不同 | 核对源内容；不同源使用新批次，不覆盖旧批次 | 清单一致或新批次成功 |
| Superset在组员处打不开 | 确认在Ubuntu浏览器使用负责人当前Tailscale地址；负责人执行过report-access，服务active且启动完成 | 私有地址页面可登录 |
| 看板空白或指标重复 | 是否published成功、连接正式库还是技术库、batch_id和axis过滤是否正确 | 与同批次Hive/MySQL核对一致 |
| 旧配置密钥无法SSH | 这是分发收尾的预期结果；本机student登录保留，需要远程协助时授权新的项目公钥 | 经组内授权的新维护方式可用 |

常用诊断在故障节点本机执行，结果先自己阅读：

```bash
source /opt/taobao/node-env.sh
tailscale status
free -h
df -h /
systemctl --user --failed
journalctl --user -u taobao-datanode -n 80 --no-pager
journalctl --user -u taobao-nodemanager -n 80 --no-pager
```

主节点按需把服务名换为taobao-namenode、taobao-resourcemanager或taobao-node-mysql。批次日志在/home/student/taobao-ad-warehouse/output/batch-*；报表同步日志在output/report-export-*。调度详细日志在/opt/taobao/data/scheduler/logs，避免将含凭据的配置文件作为故障附件。

确实需要求助时，只提交：节点名、正在执行的步骤、第一条明确错误、相关日志末尾30至80行和已经做过的排查。无需提交整段历史、重复IP输出、密码、认证链接或私钥。

## 15 各自交付清单

负责人：三台地址表、HDFS三副本证据、YARN三节点证据、技术与真实批次成功回执、分层SQL、调度验证、最终运行说明。

组员A：完整源清单与SHA256、字段及缺失说明、维度唯一性与关联质量核对、重复曝光与拒绝记录说明、adw102运行证据。

组员B：adw103运行证据、正式看板及对应批次、指标定义、截图、业务结论和限制、录屏与展示材料。

共同结项标准：三台真实互通；3个DataNode和3个NodeManager运行；Hive/Tez实际作业成功；真实CSV全量分层通过；报表按发布批次展示；结论可追溯到同一批次。不能把“软件装好”“人工样例通过”记为真实业务分析完成。

共享代码时只交SQL、脚本、说明和去除凭据后的证据；不提交CSV、数据库目录、虚拟磁盘、密码JSON和私钥。旧开发机项目上层还有其他仓库，未经单独确认不要在那里commit或push；需要Git协作时先为本项目独立建立仓库。

## 16 官方参考

- Tailscale Linux安装及认证：https://tailscale.com/docs/install/linux
- Tailscale邀请用户：https://tailscale.com/docs/features/sharing/how-to/invite-any-user
- Tailscale命令参考：https://tailscale.com/docs/reference/tailscale-cli
- Tailscale设备连接机制：https://tailscale.com/docs/reference/device-connectivity
- Hadoop 3.3.6集群配置与管理：https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/ClusterSetup.html
