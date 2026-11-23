# 业务过程与Hive维度模型

本文件描述当前正式Hive实现。旧Python/SQLite原型使用代理键和数据库外键，其DDL保留在sql/schema.sql供历史参考；正式平台以sql/hive中的表和批次契约为准。

## 1 业务过程与事实粒度

业务过程是一次广告曝光及该条源记录的点击响应。raw_sample一行只有本行点击标签，没有独立点击时间，不能虚构第二类点击事件。

DWD exposure的粒度是一个不可变输入批次中的一条有效源曝光。批次内以source_file和source_line追溯，并校验唯一性；相同用户与时间戳、甚至相同业务字段的不同源行仍保留。曝光量通过COUNT(*)计数，等价于每行impression_count=1，不另存可加性不明的CTR。click_count为0或1。

## 2 分层与物理表

| 层 | 表 | 粒度与键 | 职责 |
|---|---|---|---|
| ODS | raw_sample、ad_feature、user_profile | batch_id与源文件物理行号 | 保留源字符串、来源和不可变输入清单 |
| DIM | ad | batch_id、adgroup_id | 广告、计划、广告主、类目、品牌和源价格快照 |
| DIM | user_profile | batch_id、user_id | 性别、年龄、购物深度、消费档次、occupation、城市等级等源属性 |
| DIM | calendar | batch_id、dt | 年月日与星期，由有效事实日期生成 |
| DIM | hour | hour_key | 固定24小时公共维度 |
| DIM | resource | batch_id、pid | 有效事实中出现的资源位编码 |
| DWD | exposure | batch_id、source_file、source_line；按batch_id和dt分区 | 清洗后事实及常用维度属性 |
| DWD | rejected_exposure | batch_id、source_file、source_line | 无效记录、原始字段和首个拒绝原因 |
| DWS | daily_stats | batch_id、dt | 日曝光、点击、去重及未匹配计数 |
| DWS | axis_stats | batch_id、dt、axis、axis_value | 13个分析轴的日统计 |
| DWS | daily_quality | batch_id、dt | 匹配行、匹配用户及已匹配曝光属性缺失计数 |
| ADS | daily_overview、daily_axis、daily_quality | 对应DWS粒度 | 日级指标、贡献率和质量比率 |

Hive不依赖SQLite的user_sk/ad_sk或物理外键。DIM使用源自然业务键加batch_id保持快照内唯一，空键或重复键会停止批次；不是随意去重。DWD保存源user_id和adgroup_id，关联DIM后保留常用属性形成宽事实，以减少下游重复关联。日期、小时和资源位与公共维度一致，引用关系由SQL质量断言检查，不把数据库外键约束当成已经部署。

## 3 维度关联与未知信息

曝光始终左关联用户和广告维度。源维度未匹配时，DWD仍保留原始匿名用户或广告ID，profile_matched/ad_matched为false，对应属性为NULL。不会把不同未匹配用户合并为同一个真实用户，也不会伪造源画像记录。

DIM本身保存真实提供的快照成员；未匹配事实在宽事实和分析轴中通过标记表达。汇总使用__unmatched_profile__、__unmatched_ad__区分整行未匹配；已匹配行的空属性使用__missing_attribute__。三者不是同一种“未知”。

一个用户在多个日期或广告中出现时，全期触达必须从DWD按源user_id重新去重。未知属性标签不能替代用户ID参与COUNT DISTINCT。原始编码0保留，不能当作NULL。城市、年龄和occupation等编码只有在字典核实后才赋予具体中文含义。

广告的计划、广告主、类目、品牌作为DIM ad属性，不假设它们构成一条单一树状层级。源商品价格只是快照属性，不是成交额或广告花费。源画像和价格没有可靠历史有效期，不实现虚假的SCD2，也不把下载日期当作属性生效日期。

## 4 13个分析轴与组合查询

轴为hour、pid、adgroup、campaign、customer、category、brand、gender、shopping、pvalue、age、occupation、city。每条有效曝光在每个轴恰好归入一组，包括缺失类别，因此每个日期、每个轴的曝光和点击必须与日总量一致。

日级表适合趋势。任意所选期间的精确指标，通过query_metrics.py读取DWD重算，不相加日去重数。入口支持最多三个轴的组合、按编码筛选、默认点击量排行、CTR排行的可调最小曝光门槛，以及在门槛和Top N之前确定贡献率分母。

质量指标使用S0：日期、广告及场景筛选后的有效曝光，先于画像筛选。Q01按曝光、Q02按去重用户、Q03按曝光计算；Q04以已匹配画像曝光为分母，分别计算六项属性缺失。用户按性别筛选时，业务指标使用筛选结果，质量指标仍明确使用S0，不能自然筛成100%后冒充全体覆盖。

## 5 批次与版本

每个批次包含完整源文件及维度快照，不是实时增量。默认业务期为UTC+08:00的2017-05-06至13日；需要其他数据版本时在整理阶段明确起止日期并写入manifest。超范围有效格式时间进入outside_business_period拒绝记录。

manifest保存原文件SHA256、原始表头、受控规范表头、TSV SHA256和业务期。HDFS同名输入清单不可变；processing中的definition.json固定SQL修订、SQL文件SHA256和业务期。不同源、不同SQL或业务期使用新批次，保留旧结果。

v2为DWD追加occupation和city_level列，允许通过显式列契约无损增加旧表元数据，不删除旧ORC或旧批次。没有v2加工定义的旧结果不能静默覆盖，应用新批次重算。当前完成回执包含run_id；开始重跑会保留并撤下原完成指针，只有全层核对通过才写新的HDFS完成指针。读取和发布要求回执与当前指针一致。

## 6 发布接口

DataX发布日概览、日维度、日质量三张表，逐字段核对后更新published_batches。期间/组合查询可用--publish将一个明确请求范围的概览、质量及分组结果在MySQL单事务中发布到analysis表，request_id含筛选、时间、排序门槛和查询SQL哈希。

Superset可以读取published_analysis_overview、published_analysis_quality、published_analysis_groups；必须选择同一request_id。它们是该期间直接从DWD计算的结果，不是日表的二次累加。前端改变日期、筛选或组合时，需要重新生成对应请求，不能通过对旧请求结果任意再筛选而冒充重新计算。

模型、SQL和运行契约据此保持一致。实际全量规模、跨网络性能和三节点验收仍以真实执行证据为准。
