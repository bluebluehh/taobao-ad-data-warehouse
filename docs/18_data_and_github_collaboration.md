# 原始数据交接与GitHub协作

本指南补充三人操作手册，分别处理在线协作、原始数据和代码进度。GitHub用于同步代码、原创文档和经过检查的阶段摘要；完整数据与虚拟机使用组内文件传输方式交接。本轮本地进度已经整理，尚未提交或推送到GitHub。

## 1 哪些工作可以分开完成

| 工作 | 是否要求三人同时在线 |
|---|---|
| 导入自己的虚拟机、修改密码、登录Tailscale | 不要求，可各自完成 |
| 本地软件检查、数据整理、字段核对、SQL编写、报告整理 | 不要求 |
| 设计图表、准备PPT和录屏脚本 | 不要求 |
| 在adw103打开adw101上的Superset编辑图表 | 负责人和组员B的虚拟机在线、报表服务运行即可；数据已同步到MySQL时无需启动Hadoop |
| 三台首次网络验收、工具verify、首次HDFS初始化 | 按现有工具要求，三台都在线 |
| 验收3个DataNode和3个NodeManager、三副本、分布式加工 | 三台都在线 |
| 集群恢复和联合演示 | 约定时间，三台同时在线 |

“不同时操作键盘”不等于“节点可以关机”。你们可以异步做各自任务，但运行分布式任务时相关虚拟机和宿主电脑需要持续在线，不能休眠。为了按三节点课程方案验收，不用两台在线的结果冒充三节点通过。

目前已有的team_network.py verify会检查全部三台，单人调试时失败通常只是其他节点尚未上线；本地独立工作不需要每次运行它。组内只同步里程碑和必要地址，不向代理逐步回报。

> 2026-11-23更新：真实CSV已由负责人在adw101全量整理和本地预检，A当前任务改为规则审阅和入仓对账。下文数据传输步骤保留备用，不再要求重复交接。第四名同学负责汇报材料，可以完全不接收虚拟机；具体见新增第9节。

## 2 原始数据按职责交接

主体文件只需三张完整CSV：raw_sample.csv、ad_feature.csv、user_profile.csv。behavior_log暂不作为主体批次前置数据分发。保留原文件、文件名、编码和内容，不先抽样、删重或修改表头。

建议安排：

- 负责人保留原始文件备份，并掌握实际装载批次。
- 组员A取得三张完整CSV，负责字段、缺失、唯一键和整理清单。
- 组员B主要使用发布后的MySQL视图和Superset，不必为制作图表先复制全部原始CSV。若需要审查源数据，可独立取得同一份文件，但不另建口径不同的正式批次。

HDFS会在数据导入后自行切块并放置副本，无需人为把三张CSV分别放到三个节点来“分布式存储”。负责人装载的是一个完整批次。

## 3 Windows打包和指纹核对

在Windows准备一个独立文件夹，例如D:\taobao-data-transfer，仅将三张CSV复制进去，原始文件继续保留。以下路径为你自己创建的交接文件夹示例，不是声称数据已在那里。

在Windows PowerShell执行：

```powershell
Set-Location "D:\taobao-data-transfer"
$taobaoSourceNames = @("raw_sample.csv", "ad_feature.csv", "user_profile.csv")
$taobaoSourceNames | ForEach-Object {
    $taobaoSourceFile = Get-Item -LiteralPath $_ -ErrorAction Stop
    [PSCustomObject]@{
        File = $taobaoSourceFile.Name
        Bytes = $taobaoSourceFile.Length
        SHA256 = (Get-FileHash -LiteralPath $taobaoSourceFile.FullName -Algorithm SHA256).Hash
    }
} | Export-Csv -LiteralPath "source_sha256.csv" -NoTypeInformation -Encoding UTF8
```

将三张CSV与source_sha256.csv一起压缩，通过你们已有的组内网盘、文件传输或移动硬盘交组员A。接收方完整解压后，在解压目录的PowerShell执行：

```powershell
Import-Csv -LiteralPath ".\source_sha256.csv" | ForEach-Object {
    $taobaoReceivedFile = Get-Item -LiteralPath $_.File -ErrorAction Stop
    $taobaoReceivedHash = (Get-FileHash -LiteralPath $taobaoReceivedFile.FullName -Algorithm SHA256).Hash
    if (($taobaoReceivedFile.Length -ne [Int64]$_.Bytes) -or ($taobaoReceivedHash -ne $_.SHA256)) {
        throw ("文件不一致：" + $_.File)
    }
    Write-Output ("PASS " + $_.File)
}
```

三张均PASS后再复制进组员A的Ubuntu/home/student/taobao-input，执行三人操作手册第10节。也可以先在Windows核对后通过共享文件夹传入Ubuntu，保持完整内容。不要将大文件强行粘贴进聊天。

A整理成功后，将包含manifest.json与三个TSV的整个source-v1目录交负责人。负责人必须保留完整清单，run_batch.py会再次检查文件长度、记录数和SHA256。需要传原始CSV还是已整理目录，在组内选定一种明确交接；不要把不同版本混在同一个批次。

数据传输完成后，群里只需记录“source-v1、三文件校验PASS、来源及交付时间”。无需把数据或哈希核对过程逐项发给代理。

## 4 GitHub保存什么

继续使用原仓库：

https://github.com/bluebluehh/taobao-ad-data-warehouse

此前公开页面是main分支和中期Python/SQLite原型说明；本次尚未重新核查远端最新提交，不据此判断当前网页内容。本地已整理正式Hadoop/Hive平台与三台VMware的后续进度，本次同步要保留原仓库历史。

上传：Python和Shell脚本、Hive/MySQL SQL、公开配置模板、原创操作指南、测试、经过筛选的无凭据阶段摘要。

不上传：三张原始CSV、TSV明细、数据库、HDFS目录、虚拟机磁盘、安装包、密码文件、私钥、已认证的VPN状态。实际Tailscale地址表platform/team/nodes.json只在组内同步，仓库保留nodes.example.json。

GitHub普通Git仓库阻止超过100MiB的单文件，浏览器上传还有25MiB限制；大数据使用文件传输，不能把仓库作为虚拟机或数据库备份。

## 5 当前电脑的Git状态

旧开发机/home/student/taobao-ad-warehouse尚未建立独立.git。直接在这里运行Git会向上找到/home/student中的另一个Gitee项目。因此本轮不用这个上级仓库提交，也不修改其远端。

使用本次github-project-source.zip代码包，将代码导入原GitHub仓库的独立克隆。代码包不含.git，不会替换远端历史。请不要运行旧scripts/publish_github.cmd来同步这一轮正式平台，它属于此前原型的一键流程。

## 6 负责人用GitHub Desktop首次同步

在Windows完成，适合不熟悉命令行的情况。

1. 安装或打开GitHub Desktop，登录对原仓库有写入权限的本人GitHub账号。
2. 选择File → Clone Repository → URL，输入https://github.com/bluebluehh/taobao-ad-data-warehouse.git。
3. 克隆到独立目录，例如D:\GitHub\taobao-ad-data-warehouse，不是D:\虚拟机。
4. 创建本轮分支codex/three-node-handover。如果该分支已存在，使用其他明确的新名称；不要强制覆盖旧分支。
5. 解压github-project-source.zip。打开其中project-source文件夹，将里面的全部文件和子目录复制到刚克隆的仓库根目录。选择更新同名项目文件，保留克隆目录中的.git，保留远端其他已有文件。
6. 在GitHub Desktop的Changes查看差异。应出现正式平台scripts、sql、platform、docs、tests、examples及更新后的README；不应出现原始CSV、VMDK、数据库或密码。
7. 写提交说明，例如“同步三节点准备、正式平台代码与组内操作指南”，点击Commit。
8. 点击Publish branch或Push origin完成上传。需要GitHub登录时在应用的正常登录流程中完成，不把令牌写进项目文件。
9. 在仓库网页创建从该分支到main的Pull Request，检查差异后合并。刷新main，确认README显示三节点当前状态和新操作指南。

如果仓库要求保护分支或不允许合并，按仓库已有规则由有权限的人合并；不要使用force push绕过。若克隆或Push网络失败，保留本地克隆与提交，恢复网络后重试，不重新初始化远端、不删历史。

本轮本地工作不等于已经上传。只有GitHub网页能看到对应提交和文件，才记为同步成功。

## 7 三人后续协作

负责人在仓库Settings中的协作者页面邀请两位组员，各自用自己的GitHub账号接受。每人克隆一份代码，不提交自己的虚拟磁盘或本机地址表。

建议每个任务单独分支，例如：

- 负责人：codex/platform-batch
- 组员A：codex/data-quality
- 组员B：codex/reporting

开始工作先Fetch/Pull最新main，再从main创建任务分支。完成一项任务后Commit并Push，发起Pull Request，在组内核对后合并。其他人合并后同步main。避免三人同时直接修改main，也避免把整个旧目录复制回去覆盖别人新提交。

GitHub只同步文件，不会自动更新正在运行的Hadoop、MySQL或Superset。各自拉取新代码后，需要按变更说明应用相应配置；含数据库变更的内容由负责人先核对。无法确认冲突的业务口径时先在组内讨论，不盲目选择“全部保留我的”。

进度可放在README阶段表和简短任务记录中，只写实际完成的范围：

- 三台准备完成，不等于集群互通验收完成。
- 人工样例通过，不等于真实全量处理完成。
- 代码Push成功，不等于虚拟机配置或数据库已同步。
- 新批次的数据、清单和运行证据按同一batch_id对应，报表明确筛选批次。

## 8 官方参考

- GitHub Desktop克隆：https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-and-forking-repositories-from-github-desktop
- 本地代码导入GitHub：https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
- GitHub大文件限制：https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github


## 9 第四名同学无需虚拟机的中期汇报协作

### 9.1 协作方式与当前进度入口

三台计算节点仍由负责人、A、B维护。第四名同学负责梳理资料、制作PPT、汇总分工及排练，不需要接收虚拟机、登录数据库或复制原始CSV。GitHub文件可在浏览器直接阅读；仓库私有时负责人邀请其本人GitHub账号为协作者。GitHub不会运行本项目的Hive或Superset，静态文档及截图可以离线看，实时看板需adw101在线。

按下列顺序阅读，避免旧文档中的历史数字混入最新汇报：

| 入口 | PPT用途 | 当前性质 |
| --- | --- | --- |
| README.md顶部续接说明 | 当前阶段及总架构 | 最新状态入口 |
| docs/17_team_operations_guide.md中期清单 | 四人分工、联机待办 | 待执行清单，不能当完成记录 |
| docs/01_requirements_scope.md | 需求背景和范围 | 含早期状态，进度以README及本文为准 |
| docs/02_metric_dictionary.md | 指标、分母、去重和缺失规则 | 设计口径 |
| docs/03_model_design.md | 分层、模型、事实粒度及维度 | 当前实现设计 |
| examples/platform_checks/sql-v2-validation.json | 合成链路验证成果 | 旧开发机人工技术数据 |
| examples/platform_checks/adw101-real-source-preflight.json | 真实数据准备及质量结果 | adw101直接检查源文件，非Hive加工结果 |
| docs/20_sql_v2_usage.md末尾结果 | 本地预检完整解释及限制 | 最新实施证据说明 |

第四人不应以docs/07_midterm_report.md或docs/10_current_status.md为最新正式平台进度，这两份是旧Python/SQLite样本阶段材料。

### 9.2 可直接用于本次中期PPT的状态表

| 事项 | 截至2026-11-23的可证明状态 | 汇报时如何说 |
| --- | --- | --- |
| 需求与模型 | 指标及Hive分层实现已有 | 已完成设计并实现加工代码 |
| 完整加工、导出与看板 | 旧开发机合成数据已验证 | 人工技术数据链路通过，不能冒充真实报表 |
| adw101准备 | 结构升级复核、28项工具测试及源码核验通过 | 主节点本地准备已验证 |
| 真实三表 | 全量整理，源CSV/TSV哈希核对通过 | 已完成真实数据接入准备 |
| 真实源预检 | 26,557,961曝光，广告846,811，画像1,061,768；维度空键/重复键均0 | 本地真实源预检完成 |
| 源文件基线 | 点击1,366,056，触达1,141,729，画像未匹配曝光1,528,526 | Python直接全表核查结果，用于后续Hive对账 |
| 三节点 | 软件环境已准备，互通和运行未联合验收 | 三节点配置准备完成，联机验收待完成 |
| 真实Hive及报表 | 尚未执行验收 | 下一阶段任务 |
| Tailscale | 最新现场adw101为NeedsLogin，后续登录未确认 | 组网进行中，不声称三台已联网 |

此表是日期快照。后续状态变化须由负责人提供新回执、批次号及证据，第四人再更新PPT，不能自行把待办改为完成。

### 9.3 建议的9页中期PPT

1. 题目与四人分工：负责人平台和集成，A质量及adw102，B图表及adw103，第四人汇报与材料整合。
2. 背景与范围：淘宝展示广告曝光/点击；三张主体表；不涉及广告费用或购买归因。
3. 真实数据：三表记录数、业务期2017-05-06至13日、时区Asia/Shanghai、SHA256追溯方法。
4. 需求和指标：曝光、点击、CTR、精确触达，以及画像/广告覆盖；说明跨日人数不能求和。
5. 总架构：CSV→HDFS→Hive on Tez五层→DataX→MySQL→Superset，调度由DolphinScheduler负责。
6. 维度模型：一条有效曝光一条事实；用户、广告、日期、小时、资源位；自然键、批次和未知成员处理。
7. 已完成的技术验证：合成样例有效9/拒绝8/点击4、边界与损坏拦截、导出和看板；每张技术图显著标注“合成数据”。
8. 真实源质量与当前差距：维度唯一、广告全匹配、画像未匹配1,528,526；标注“本地源预检”，列三节点/真实入仓待验收。
9. 接下来计划及分工：三台组网→集群与Tez→技术批次→真实入仓及对账→真实看板→调度与最终交付。

如果联机验收在汇报前完成，将第8页补入同次验收的节点/作业截图，并更新状态；若没有，保留待完成。无需为了页面好看伪造看板或集群截图。

### 9.4 截图与文件怎么交接

- 负责人提供当前架构、模型及未来集群证据；A提供质量说明；B提供标注清楚的图表截图。第四人按上述页序整合。
- 图注写清执行节点、数据性质、日期、批次/分析范围及验证范围。屏蔽密码、认证链接、数据库连接串和个人信息。
- 当前源码包以文本源码/文档/检查JSON为主，不承诺包含看板截图。截图可另用组内共享文件夹交付；如要纳入GitHub，可放examples/presentation/并单独审查提交，现有构建脚本不会自动打包PNG/PPTX。
- 第四人的PPT可以先通过组内文件传输交负责人。在现有仓库根目录忽略规则下，随意新建presentations文件夹可能不会被Git跟踪；需负责人明确调整规则并复核，或使用私有共享目录，不要用git add -f强塞包含敏感信息的文件。

### 9.5 负责人怎样把这一版放上GitHub

按第6节在Windows的独立克隆操作：克隆原仓库→从最新main建立codex/midterm-progress分支→将本次github-project-source.zip中的project-source内容合并至克隆根目录→审查Changes→Commit→Publish/Push→创建并核对PR→合并main。已克隆者先同步main，不再新建仓库或更改远端。

这次提交应包含本节、最新三人指南、当前README及两种数据性质的检查摘要。完成后将main分支的README及本指南网页链接发给第四人，他直接在浏览器阅读即可；不必把ZIP上传为仓库里的一个压缩包，不必传虚拟机。

只有远端网页能看到本次提交及文件，才记为GitHub已同步。若操作前尚未上传，则把最新源码ZIP先交给第四人阅读，说明这是本地快照，不声称GitHub已更新。
