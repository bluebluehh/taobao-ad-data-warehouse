# SQL v2更新与三人后续操作

2026-11-23。本轮已修复SQL复核中的八类缺项，并在旧开发机Hive 4.0.1 / Tez 0.10.4隔离空间运行验证。原始真实CSV未上传，三台分发虚拟机尚未联机验收；以下“已通过”只指合成技术测试。

## 只有负责人在线时的独立操作顺序

2026-11-23用户确认：三台目前均关机，仍停留在软件工具环境准备阶段；只有负责人节点已登录Tailscale，另两台未登录。登录状态来自用户确认，本轮没有远程复验。可先只启动自己的adw101，另外两台暂不需要开机。

1. 将本次更新包、对应SHA256和本指南留一份在自己的电脑；保存原虚拟机副本及原有输出。暂未确认其他成员已接收，不记录为已分发。
2. 只启动adw101，确认`hostnamectl --static`为adw101，再按下节合并源码，执行源码哈希核验和本地测试。这一步不需要HDFS、YARN或其他节点。
3. 仅在adw101运行`python3 scripts/platform/upgrade_sql_v2.py`。它会启动本机项目MySQL并核对目标实例，再扩展报表结构；不需要另两台。保存终端结果，单独记录结构升级是否成功。
4. 在adw101执行`tailscale status`和`tailscale ip -4`，确认自己的登录仍有效即可。其他节点关机时不要执行要求三台互通的team_network verify，不要为了取得NETWORK_VERIFIED而手工造标记。共同地址表等另两台独立登录后再定稿。
5. 若真实CSV在自己的Windows或其他磁盘，可以先把三张主体CSV完整复制到adw101的`/home/student/taobao-input`，运行下面的整理命令。此步骤只用本机Python，不需要集群，也不会将数据加载到Hive。若CSV尚不在自己手上，保留为待交接，不用样例代替。

```bash
cd /home/student/taobao-ad-warehouse
python3 scripts/platform/stage_csv.py \
  --source /home/student/taobao-input \
  --out output/staged/real_handover_v1 \
  --start-date 2017-05-06 --end-date 2017-05-13
```

执行前确认磁盘空间可容纳原始CSV和新增TSV；整理完整读取大文件，需要时间。成功后保留`manifest.json`及三个TSV。清单提供源表头、字节数、记录数和SHA256；它不代表已检查维度唯一性、业务期内分布、关联覆盖率或完成真实入仓验收，这些由后续加工与质量检查确认。已有输出目录不覆盖，失败时检查原因并选择新的输出目录。

负责人可以独立阅读模型和SQL、整理报告中的架构/指标/实现章节，以及安排演示步骤。真实指标分析、集群截图和运行性能章节保留“待运行填写”，不要套用合成数字。旧create_scheduler_workflow.py固定技术批次并会立即提交执行，暂不作为真实流程入口运行。

本阶段完成标准：自己的源码一致、本地测试通过、adw101结构升级有结果；若真实CSV已到位，则另有源清单和完整整理目录。需等待组员的事项：两台独立Tailscale登录、源码更新、三节点互通、首次集群启动和分布式验收。不要在关机工作节点的情况下初始化或启动完整三节点验收流程。

## 先更新三台虚拟机中的项目文件

三台虚拟机之前交付的副本仍是旧代码，本轮不会自动出现在其中。无需重装Ubuntu或重新克隆。

1. 从本次交付目录取得`sql-v2-vm-update.zip`，分别发给两位组员并保留一份。ZIP只含代码、手册和技术检查摘要，不含数据或密码。
2. 每人在自己的虚拟机关闭项目任务，备份现有项目目录中的代码和`output`。确认没有正在运行的批次或调度，再将压缩包中`taobao-ad-warehouse`文件夹里的内容合并到`/home/student/taobao-ad-warehouse`，允许覆盖同名源码。保留现有`output`、数据和机器私有配置。
3. 不复制其他人的`/opt/taobao/data`、`/etc`、SSH私钥或Tailscale登录状态；不格式化HDFS。
4. 三台都运行本地检查；只有adw101额外运行报表结构扩展。该扩展保留原有表和记录。

```bash
cd /home/student/taobao-ad-warehouse
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

仅adw101：

```bash
python3 scripts/platform/upgrade_sql_v2.py
```

三台不需要同时做源码更新或本地检查。联网、HDFS/YARN集群运行及跨节点任务执行时，相关机器须同时在线，按[团队指南](17_team_operations_guide.md)配置各自独立的Tailscale身份并自检。不要因升级SQL重复初始化已经有数据的HDFS。

## 更新后的源码核验与回执（2026-11-23续接）

新增`verify_source_update.py`用于核对三台是否实际更新到同一交付版本。它不覆盖源码、不连接远端、不启动服务、不升级数据库。源码不一致或测试失败时退出非零，回执明确限定为本地检查，不能证明组网、分布式运行或真实数据验收。

负责人向组员提供同一份最新`sql-v2-vm-update.zip`及其`.sha256`，两者通过可信交付渠道分发。先按前节合并源码，再在每台以student执行以下整组命令。将路径换成实际ZIP位置，将哈希换成负责人提供的64位SHA256；每次使用新的回执文件名：

```bash
cd /home/student/taobao-ad-warehouse
python3 scripts/platform/verify_source_update.py \
  --archive /home/student/Downloads/sql-v2-vm-update.zip \
  --expected-sha256 替换为负责人提供的64位SHA256 \
  --receipt output/source-update-check-01.json --run-tests
```

只有`source_matches=true`且`local_tests=passed`才表示源码核对及本地工具测试通过。`differences`会列出缺失、修改或不安全路径；保留自己的改动并人工合并，不通过删除数据或修改哈希让检查通过。脚本检查清单中所有文件，额外的本机文件不被删除。测试日志与回执写在output，不进GitHub。

三人共享回执中的hostname、archive_sha256、expected_files、source_matches、local_tests即可。负责人确认三台哈希相同，并单独记录adw101结构升级结果；本工具不证明MySQL已升级。源码全部一致后，再按团队指南完成Tailscale与集群验收。

本次续接实测：执行环境主机名为student-VMware-Virtual-Platform，仍为旧开发机；原24项测试再次通过。历史SQL v2成功回执、Hive日志及DataX成功回执文件存在。调度与报表MySQL服务active，Superset inactive。三台远程授权已撤销，尚无新维护方式及节点回执，因此没有声称三台已更新。需求文件中的早期真实文件核查数字仅为历史记录，不等于当前实施环境已收到真实CSV或完成正式平台真实数据验收。

## 本轮新增行为

- 清单明确业务期，默认2017-05-06至2017-05-13，时区Asia/Shanghai。两端日期均包含，期外记录进入拒绝表，原始CSV不改写。
- 仅兼容已记录的`new_user_class_level `末尾一个空格别名，同时保留源表头、规范表头和原文件SHA256；其他未知表头变化仍拒绝。
- occupation、city_level贯通DIM、DWD、日汇总和期间组合分析，共13个分析轴。
- Q01画像曝光覆盖率、Q02画像去重用户覆盖率、Q03广告曝光覆盖率，以及六项Q04属性曝光加权缺失率形成日表、期间查询、MySQL和原生看板接口。
- Q04分母仅为已匹配画像的曝光。质量范围S0保留时间和非画像筛选，移除画像筛选，避免筛掉未匹配人群后虚高覆盖率。结果中的`quality_scope_filters`可核查实际口径。
- 空范围计数为0，比率为NULL；有曝光无点击时CTR为0，点击贡献率为NULL。
- 期间用户数和广告数从DWD精确去重。多维分组最多三个维度；贡献率分母在曝光门槛与Top N之前计算。默认点击量降序，CTR排行默认最小曝光1000，可显式调整。
- DWS、ADS六张结果表核对唯一键、缺失行及全部字段，NULL使用安全比较；整轴缺失也会失败。

## 真实数据到位后的完整流程（adw101执行）

先按团队指南启动并验证集群，再进行以下操作。将`/实际主体CSV目录`换成自己机器上的真实路径，里面有raw_sample.csv、ad_feature.csv、user_profile.csv。原始数据通常只交给负责导入的adw101，不必让每个组员各自重复加载同一个批次。

```bash
cd /home/student/taobao-ad-warehouse
python3 scripts/platform/stage_csv.py \
  --source /实际主体CSV目录 \
  --out output/staged/full_201705_v2 \
  --start-date 2017-05-06 --end-date 2017-05-13
python3 scripts/platform/run_batch.py \
  --staged output/staged/full_201705_v2 \
  --namespace taobao --batch full_201705_v2 \
  --receipt output/full_201705_v2-success.json
/opt/taobao/module/superset-6.1.0-venv/bin/python \
  scripts/platform/export_reports.py \
  --run-record output/full_201705_v2-success.json
```

检查源文件数量、记录数、SHA256、日期分布、关联覆盖率和拒绝原因，保留日志与清单。不要直接使用本文的技术样例数字作为真实数据验收标准。

新批次名必须没有旧版DWD分区。旧批次保留；同一v2批次、相同输入和相同01—07加工SQL可重跑，结果覆盖计算而不累加。改变源输入、业务期或加工SQL要用新批次。执行器会检查HDFS不可变定义和本次成功ID；失败重跑不能借用旧成功回执继续发布。

同一命名空间的写入由本机文件锁串行保护；组内统一由adw101负责导入和发布，不从多台机器同时提交同一空间任务。日表仅用于按日展示，多日去重人数不能在Superset直接求日表SUM。

## 期间查询、筛选、排行与看板

下面按展示位置、广告单元和性别组合分析。日期可以取业务期子区间，超出已装载业务期的部分只会得到空数据，不会读取其他批次。

```bash
/opt/taobao/module/superset-6.1.0-venv/bin/python \
  scripts/platform/query_metrics.py \
  --run-record output/full_201705_v2-success.json \
  --start-date 2017-05-06 --end-date 2017-05-13 \
  --group-by pid,adgroup,gender --limit 100 --publish
```

程序打印本次`output/metric-query-...`目录。将下面的“本次目录”换成这个实际目录：

```bash
/opt/taobao/module/superset-6.1.0-venv/bin/python \
  scripts/platform/setup_analysis_dashboard.py \
  --result output/本次目录/result.json
```

终端打印新看板地址。虚拟机内浏览器可直接打开；组员远程访问按团队指南的报表连接方式操作。每个看板绑定一个完整分析范围ID，包含日期、筛选、分组、排行门槛和查询SQL哈希。更改范围时重新执行查询并创建对应看板，不把日表合计冒充新的全期去重结果。当前入口使用命令选择范围，尚无网页自助筛选重算功能。

其他例子：

```bash
# occupation与城市等级组合，仅看某一性别；质量覆盖率仍采用画像筛选前的S0
python3 scripts/platform/query_metrics.py \
  --run-record output/full_201705_v2-success.json \
  --group-by occupation,city --filter gender=1
# 按CTR排行，仅比较至少1000次曝光的广告单元
python3 scripts/platform/query_metrics.py \
  --run-record output/full_201705_v2-success.json \
  --group-by adgroup --sort ctr --min-impressions 1000 --limit 20
```

可选分组/筛选：hour、pid、adgroup、campaign、customer、category、brand、gender、age、shopping、pvalue、occupation、city。只接受原始匿名编码；未匹配画像用`__unmatched_profile__`，未匹配广告用`__unmatched_ad__`，已匹配但属性缺失用`__missing_attribute__`。不编造匿名编码的中文含义。使用`--publish`需上述虚拟环境中的MySQL依赖；纯查询使用python3即可。

MySQL精确期间接口为published_analysis_overview、published_analysis_quality、published_analysis_groups，必须按request_id选择完整范围。daily_quality与published_daily_quality是新增日质量接口。新看板包含期间概览、覆盖与缺失率、分组表、曝光与点击柱状图；发布前核对全部字段，并在同一数据库事务中提交。

## 可独立重跑的技术回归

只允许在旧开发测试环境或已正常启动的集群中执行，预留运行时间及磁盘。以下人工输入禁止写入taobao正式空间。每次替换为新的测试目录和批次名；测试组员先协调，避免同时占用集群。

```bash
python3 scripts/platform/create_sql_v2_fixture.py --out output/v2-test-input
python3 scripts/platform/stage_csv.py \
  --source output/v2-test-input --out output/v2-test-staged
python3 scripts/platform/run_batch.py \
  --staged output/v2-test-staged --namespace validation_sql_v2 \
  --batch regression_v2_local --receipt output/v2-test-success.json
python3 scripts/platform/validate_sql_v2.py \
  --namespace validation_sql_v2 --batch regression_v2_local
```

回归预期：17条源曝光→有效9、拒绝8、点击4、全期去重用户4、全期广告单元3；画像曝光覆盖7/9，画像用户覆盖2/4。测试还覆盖空范围、零点击、全部未匹配、画像筛选口径、Top N分母、CTR门槛和人为损坏。底层最后一条SQL故意失败，包装程序只有同时发现两组成功标记及预期断言失败才返回整体通过；不能把任意执行错误当成功。

## 分工与仍待验收事项

三人可分别完成源码更新、文档/模型、SQL阅读、本地工具测试及报告准备。主节点负责人统一执行批次、发布和看板，工作节点负责人保障自己的节点网络、磁盘及服务状态；无需三人重复编写或运行相同SQL。

本轮旧开发机技术验证已完成：24项工具测试、完整加工与同批次重跑、Hive边界与反例、三张日表DataX全部字段对账、精确期间范围MySQL发布、四张原生看板的真实浏览器渲染，以及重复维度键拒绝。真实CSV规模、真实关联情况、三节点跨网络性能和故障恢复尚待组内实际验收。新代码尚未自动同步进三台分发副本，也尚未推送GitHub；GitHub同步见[协作指南](18_data_and_github_collaboration.md)。

## 2026-11-23 adw101远程续接：真实源本地预检

用户已完成adw101源码更新、本地测试、报表结构升级和真实CSV全量整理；另两台尚未联机验收。代理已使用本次专用维护公钥连接adw101，核对主机名、machine-id及固定SSH主机公钥。原始数据保持在adw101，未复制回旧开发机。

实测Tailscale为NeedsLogin，没有尾网IP，与此前口头登录状态不同；当前维护经过本机VMware NAT地址，不代表跨网络组网通过。需后续在adw101本机重新登录，并等待另两台独立登录后组网。

新增本地预检入口（不依赖Hadoop）：

```bash
python3 scripts/platform/audit_source_csv.py \
  --source /home/student/taobao-input \
  --staged output/staged/real_handover_v1 \
  --out output/real-source-audit-新的检查编号
```

输出目录必须是新目录。先核对三份原CSV、三份TSV的SHA256及大小，再检查维度空键和重复键、全量曝光的关键字段/时间/点击标签、日期分布、精确期间去重、广告/画像覆盖及匹配曝光的画像属性缺失计数。保留未匹配曝光，不按用户及时间戳删除记录；发现维度重复键即停止关联核查。该脚本不检查完全重复曝光行，也不证明Windows源文件与Ubuntu副本哈希一致。

结果在`audit.json`，失败在`failure.json`。`local_preflight_passed`仅表示这组本地检查完成，`warehouse_real_data_accepted`及`cluster_verified`始终为false；只有后续Hive/Tez入仓、层间对账和三节点验收完成才能更新项目验收结论。

本次新工具及回归测试已同步adw101，两端28项工具测试通过（包含合成数据计数、TSV篡改、重复维度键拦截）。这是149文件更新包之后新增的两个文件，不改写之前源码核验回执；后续交付应使用重新构建的源码包。

### 本轮实际结果

adw101上`output/real-source-audit-20261123/audit.json`已生成，执行退出码0，用时630.66秒。无原始CSV回传，汇总证据保存在`examples/platform_checks/adw101-real-source-preflight.json`。

| 项目 | 真实源本地预检结果 |
| --- | ---: |
| 曝光原记录/本次有效记录 | 26,557,961 / 26,557,961 |
| 点击记录 | 1,366,056 |
| 期间精确触达用户/点击用户 | 1,141,729 / 491,647 |
| 期间曝光广告单元 | 846,811 |
| 广告/画像维度行数 | 846,811 / 1,061,768 |
| 两张维度空键及重复键 | 均0 |
| 匹配广告曝光 | 26,557,961 |
| 匹配画像曝光/用户 | 25,029,435 / 1,061,768 |
| 画像未匹配曝光/用户 | 1,528,526 / 79,961 |
| 匹配画像曝光中消费档次缺失 | 13,024,272 |
| 匹配画像曝光中城市等级缺失 | 6,696,303 |

以上为Python直接检查真实源文件的对账基线，不是Hive加工产出或正式发布报表。按当前规则未发现拒绝记录；并不意味着所有可能的数据质量问题均不存在。完整重复曝光行未在本轮检查，禁止据此声称全行无重复。

三张原CSV及TSV的大小、哈希全部匹配清单。两端28项工具测试通过；adw101再次运行SQL v2增量结构升级成功，日志在`output/sql-v2-schema-remote-check-20261123.log`。本轮保留项目专用SSH维护授权以便后续工作；未执行HDFS格式化、启动三节点加工或发布真实看板。下一阶段须先完成三台各自Tailscale登录及联机验收。
