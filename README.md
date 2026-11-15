# 淘宝展示广告投放表现分析数仓

数据仓库课程项目，基于真实公开的广告曝光点击日志、广告信息与用户画像，实现分层ETL、维度建模、多维查询和交互看板。目前为中期样本原型。

## 当前成果

| 项目 | 结果 |
| --- | --- |
| 日期 | 2017-05-06至2017-05-13，UTC+08:00 |
| 抽样 | 按固定规则抽取约2%的曝光数据；广告表与画像表保留全量 |
| 曝光 / 点击 | 530,224 / 27,258 |
| 点击率 / 触达用户 | 5.14% / 273,340人 |
| 分层 | ODS → DIM → DWD → DWS → ADS |
| 技术 | Python标准库、SQLite、HTML/CSS/JavaScript、SVG |

看板提供日期趋势、小时分布、展示位置比较、性别/购物深度/消费档次比较、Top 10排行、曝光×点击率散点图、展示位置×年龄层级热力图、画像覆盖图和CSV明细导出。

## 成果与文档入口

- [文档导航](docs/README.md)：需求、指标、模型、实现和推进记录。
- [当前状态与验收范围](docs/10_current_status.md)：最新成果和待办。
- [中期汇报稿](docs/07_midterm_report.md)：原始阶段稿，后续进展以当前状态为准。
- [静态看板](examples/dashboard_preview.html)：下载后双击HTML即可查看，无须数据库；固定快照不能筛选。
- [汇总快照](examples/ads_snapshot.json)及 [检查证据目录](examples/checks/)：不含原始用户明细。

## 运行交互看板

需要Python 3.11及以上，运行无需第三方Python依赖；Node.js仅用于可选前端检查。

从[天池数据集页面](https://tianchi.aliyun.com/dataset/56)自行取得数据，按发布方要求使用。准备解压后的raw_sample.csv、ad_feature.csv、user_profile.csv；源目录可含子目录，每个文件名应只有一份。

在项目根目录执行：

```powershell
python -m warehouse.build --source 'D:\datasets\taobao_ad' --rate 0.02 --seed dw2026-midterm
python -m warehouse.serve --self-check
```

出现HTTP CHECK OK后访问 <http://127.0.0.1:8765/>，保持服务运行。已有数据库时可双击scripts/start_dashboard.cmd启动。后端修改后需要重启，前端修改后Ctrl+F5刷新。

仓库不提供SQLite数据库，首次克隆必须先构建，不能直接启动交互服务。原始CSV只读；相同输入和配置可复用结果。需要重建时先保存旧结果，再显式加--rebuild。

正式全量运行尚未验收；资源评估后可用独立目录：

```powershell
python -m warehouse.build --source 'D:\datasets\taobao_ad' --rate 1 --out output/full_run
python -m warehouse.serve --db output/full_run/warehouse.sqlite3
```

## 检查与复现

无原始数据也能检查源码和已提交快照：

```powershell
python -m warehouse.static_check
node tests/dashboard_checks.cjs
```

本机已有数据库时，可运行以下检查。真实SQL检查耗时高于语法检查；HTTP受限时单独记录，不当作通过。

```powershell
python -m warehouse.check
python -m warehouse.export_preview
```

历史45项ETL检查、20项数据及查询函数检查的证据保存在examples/checks。后续图表检查另行记录；历史报告不代表新增页面交互全部验收。

## 目录

| 目录 | 内容 |
| --- | --- |
| docs | 需求、指标、模型、分层、代码说明及进度 |
| warehouse | 构建、指标计算、只读服务和检查工具 |
| sql | 建表与关联视图 |
| web | 无外部CDN依赖的前端 |
| scripts | 数据核查与Windows启动入口 |
| tests | 使用汇总快照的前端检查 |
| examples | 汇总快照、离线HTML与整理后的检查证据 |
| output | 本机生成结果，不提交Git |

## 分析边界

- 2017年历史样本，原型又进行了约2%抽样，不代表淘宝全平台。
- 广告对象以匿名ID定位，不能还原真实名称。
- 性别、购物深度、消费档次按已核对字典解释；年龄、城市具体映射尚未可靠核实。
- 未匹配画像与属性缺失分开保留；人群结论说明覆盖范围，消费档次缺失较多。
- 点击率由总点击÷总曝光重算，去重用户数不能跨组相加。
- 不计算广告费用、CPC、ROI、ROAS和广告归因购买转化；观察差异不等于因果关系。
- behavior_log尚未接入，Hadoop/Hive/Spark、云端部署和自动调度尚未实现。

## 数据与参考

数据：[阿里云天池](https://tianchi.aliyun.com/dataset/56)。字段参考：[厦大数据库实验室案例](https://dblab.xmu.edu.cn/blog/5589/)。学习方法见[参考记录](docs/08_reference_methods.md)。

仓库仅附项目代码、原创说明及必要汇总结果，不附原始数据、课程模板或第三方学习文档。数据与参考材料权利归原权利人，本仓库不额外授予其再分发许可。

## GitHub发布

仓库地址：https://github.com/bluebluehh/taobao-ad-data-warehouse 。首次发布准备情况见[发布记录](docs/11_github_publication.md)。本机可双击scripts/publish_github.cmd执行检查、提交和推送；是否上传成功以Git输出与远端文件为准。
