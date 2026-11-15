"""Turn completed audit results into a readable report and reproducible bundle."""
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'output' / 'data_check'
r = json.loads((out / 'audit.json').read_text(encoding='utf-8'))
t = r['tables']
a, u, f, b = (t[k] for k in ['ad_feature', 'user_profile', 'raw_sample', 'behavior_log'])
assert sum(f['daily_utc8'].values()) == f['rows'] - f['bad_width'] - f['invalid_timestamp_rows']
assert sum(f['label_pairs_nonclk_clk'].values()) == f['rows'] - f['bad_width']
assert f['extra_exact_duplicate_rows'] <= f['user_timestamp_extra_rows']
for d in [a, u]:
    assert d['distinct_keys'] + d['extra_duplicate_keys'] == d['rows'] - d['bad_width']

lines = ['# 淘宝展示广告数据核查报告', '',
    '检查对象：项目目录中现有的实际文件。三张主体表为全量扫描；行为表仅检查压缩包首个文件元数据和前四行。原始数据未修改。', '',
    '## 1. 文件与表头', '',
    '| 表 | 数据行数（不含表头） | 文件实际表头 |', '| --- | ---: | --- |']
for name in ['raw_sample', 'ad_feature', 'user_profile']:
    d = t[name]
    lines.append(f"| {name} | {d['rows']:,} | `{','.join(d['header_original'])}` |")
lines += ['', '实际命名修正：`nonclk` 对应背景中的 `noclk`；`customer` 对应广告主标识；用户画像最后一个列名有末尾空格。ODS 保留原始信息，DWD/DIM 中清理列名，并明确映射为 `user_id`、`customer_id` 等统一名称。', '',
    '## 2. 主体日志与标签', '',
    f"- 原始记录：{f['rows']:,}；字段数异常：{f['bad_width']:,}；非法标签：{f['invalid_label_rows']:,}；时间戳转换失败：{f['invalid_timestamp_rows']:,}。",
    f"- 标签组合（nonclk,clk）：`{json.dumps(f['label_pairs_nonclk_clk'], ensure_ascii=False)}`。",
    f"- 有效点击标签数：{f['valid_clicks']:,}；以原始数据行为分母的点击率：{f['ctr_before_duplicate_policy']:.6%}。此处是核查基线，正式曝光口径还要记录重复处理政策。",
    f"- 去重用户：{f['distinct_users']:,}；被曝光广告单元：{f['distinct_ads']:,}。", '',
    '## 3. 重复与关联', '',
    f"- 广告信息重复键多余行：{a['extra_duplicate_keys']:,}；用户画像重复键多余行：{u['extra_duplicate_keys']:,}。",
    f"- 全部六列完全一致的重复组：{f['exact_duplicate_groups']:,}；每组保留一行时的多余行数：{f['extra_exact_duplicate_rows']:,}。",
    f"- 用户＋时间戳重复组：{f['user_timestamp_duplicate_groups']:,}；对应多余行数：{f['user_timestamp_extra_rows']:,}。",
    '- 完全相同的日志不一定是技术错误。秒级时间戳可能无法区分多次事件，当前只标记并量化，不擅自删除。用户＋时间戳不能未经论证作为曝光唯一键。后续以文件标识＋源行号追溯每条源记录。',
    f"- 未匹配广告信息的日志行：{f['unmatched_ad_rows']:,}；涉及广告单元：{f['unmatched_ad_ids']:,}；行覆盖率：{f['ad_row_coverage']:.6%}。",
    f"- 未匹配画像的日志行：{f['unmatched_profile_rows']:,}；涉及用户：{f['unmatched_profile_users']:,}；行覆盖率：{f['profile_row_coverage']:.6%}；用户覆盖率：{f['profile_user_coverage']:.6%}。",
    '- 关联采用 LEFT JOIN。维度键唯一时不会放大行数；缺失画像进入未知成员，保留原始曝光和点击。人群看板同时展示画像覆盖率。', '',
    '## 4. 缺失值', '', '| 表 | 字段 | 缺失行数 | 缺失率 |', '| --- | --- | ---: | ---: |']
for name in ['raw_sample', 'ad_feature', 'user_profile']:
    d = t[name]
    for col, count in d['missing'].items():
        lines.append(f"| {name} | {col.strip()} | {count:,} | {count / d['rows']:.6%} |")
lines += ['', '缺失画像属性保留为未知，不用 0 冒充一个真实编码；品牌缺失保留未知品牌；商品价格不作为广告费用。', '',
    f"价格值状态：`{json.dumps(a['price_status'], ensure_ascii=False)}`。此项只检查数值可解析性、非有限值和符号，尚未完成价格业务异常值判定。", '',
    '## 5. 时间范围', '',
    f"- Unix 时间戳范围：{f['min_timestamp']} 至 {f['max_timestamp']}。",
    f"- UTC：{f['range_utc'][0]} 至 {f['range_utc'][1]}。",
    f"- UTC+08:00：{f['range_utc8'][0]} 至 {f['range_utc8'][1]}。",
    '- 同时保留原始 Unix 时间戳。UTC+08:00 是项目拟采用的业务分析时区；边界一致仅支持这一选择，不能代替数据提供方的时区说明。', '',
    '| 日期（UTC+08:00） | 原始记录数 |', '| --- | ---: |']
for day, count in f['daily_utc8'].items():
    lines.append(f'| {day} | {count:,} |')
lines += ['', 'UTC 按日计数保存在 audit.json 的 daily_utc 中，可用来核对时区转换造成的日期变化。', '',
    '## 6. 行为日志检查边界', '',
    f"- 压缩包字节数：{b['archive_bytes']:,}。",
    f"- 首个普通文件：`{b['member']}`。",
    f"- tar 元数据声明的解压后文件字节数：{b['uncompressed_bytes_declared']:,}。",
    '- 包内前四行：', '', '```text', *b['first_four_lines'], '```', '',
    '实际开头记录出现 `pv`，与项目背景中的 `ipv` 不同。当前只能确认样例值为 pv，尚未枚举全量 btag；正式映射必须以实际取值和官方说明共同核对。', '',
    '尚未完成：完整解压流读取、CRC 校验、实际总行数、全量时间范围、缺失与重复、和广告用户的交集。上述大小不能证明全量、子集或七亿条。行为日志当前不计入已处理数据规模，不纳入主体广告效果事实表。', '',
    '## 7. 本阶段建议', '',
    '主体范围：使用三张主体表完成投放概览、广告表现、人群分析、资源位与时段四个主题。行为表保留扩展资格。完整实现包含 ODS、DIM、DWD、DWS、ADS，必须有 SQL/ETL 和多维分析，不能只做 CSV 图表。', '',
    '优先技术方案：Python 负责调度与校验，DuckDB 负责离线分析 SQL，Parquet 保存分区明细和汇总，Streamlit 展示 ADS 结果。该方案是根据单机课程项目提出的建议，尚未安装并验证运行，不属于已经完成的实现。', '',
    '当前检查环境可以运行 Python 3.14.3 和标准库。尝试安装分析依赖时，当前执行环境的网络连接受限；不能据此认定用户电脑正常终端也无法联网。正式环境先做依赖安装和一次最小导入验证，再固定版本。', '',
    '技术参考：',
    '- https://duckdb.org/docs/current/guides/performance/environment',
    '- https://docs.streamlit.io/get-started', '',
    '下一阶段先确定记录保留政策、时区和未知维度处理，然后形成业务过程、粒度、维度、事实四步设计与指标字典。订单、花费和广告归因缺失，不能补造 CPC、ROI 或广告成交额。', '',
    '## 8. 如何复查，以及代码执行逻辑', '',
    '在项目根目录用 PowerShell 执行：', '',
    '```powershell', 'python scripts/check_data.py', 'python scripts/write_check_report.py', '```', '',
    '脚本只依赖 Python 标准库。核查时需要为日志临时分块留出约原始日志文件大小的可用空间，运行完成会清理这些临时文件。结果输出到 output/data_check。', '',
    '1. `Path` 定位项目和数据目录，避免写死某位组员的绝对路径。`csv.reader` 按行读取两张维度表，首行单独识别为表头，不计入数据行数。',
    '2. `dimension` 用集合保存已经出现的键，用 `Counter` 统计缺失、画像编码及价格状态。重复键数指同一键第一次出现以后的行数；不能把它误称为重复组数。列名 strip 只作用于检查中的命名，不回写源文件。',
    '3. 广告日志按二进制逐行读取，以逗号拆成六个字段。此快速路径依赖本文件无引号包裹逗号的简单格式，并逐行检查字段数；它不是任意 CSV 的通用解析器。遇到异常宽度单独计数，不静默补齐。',
    '4. 每条日志分别检查用户键与广告键是否在维度键集合中，累计未匹配行数和未匹配键数。前者衡量曝光覆盖率，后者衡量用户或广告覆盖率，两种比例的分母不同。',
    '5. 标签必须是 (nonclk,clk)=(1,0) 或 (0,1)。有效点击数按 (0,1) 累计，非法组合单独统计。原始行分母的点击率仅作为审计基线，正式指标由清洗政策决定。',
    '6. 时间戳按整数处理。整除 86400 得到 UTC 日期编号；加 28800 秒后整除得到 UTC+08:00 的日期编号。用日期编号统计日分布，最后再格式化，避免给每一行创建日期对象。',
    '7. 为检查重复，以用户＋时间戳的稳定哈希把原始记录分进 128 个临时文件。相同候选键一定进入同一文件；哈希碰撞只影响分块位置，不影响判断，因为最终仍比较完整行和完整键。',
    '8. 逐块使用 `Counter` 统计完整行与候选键，分别累加重复组数以及 sum(n-1)。每次只处理一个块，降低内存占用。完整行只统一换行符，空白或其他不同写法不会自动视为同一行。',
    '9. `tarfile` 流式读取行为包的第一个普通文件，只查看开头，不执行解压到磁盘。`member.size` 是包内声明值，不能当作已扫描行数或完整性验证。',
    '10. `json` 保存精确检查结果，`write_check_report.py` 在总行数、标签总数、日期总数和重复计数之间做一致性断言，再生成本报告并打包。复跑会更新结果文件，不会更新源 CSV。', '',
    '## 9. 检查限制', '',
    '本阶段没有验证下载链接与本地包的文件哈希，也没有逐一校验压缩包与现有解压文件内容一致；分析结论针对现有解压文件。画像编码只统计实际取值，未自行翻译性别等含义。正式数据字典仍需保存官方字段说明证据。', '']
report = out / 'data_check_report.md'
report.write_text('\n'.join(lines), encoding='utf-8')
bundle = out / 'data_check_bundle.zip'
with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in [report, out / 'audit.json', root / 'scripts/check_data.py', Path(__file__)]:
        z.write(p, p.relative_to(root))
print(report)
print(bundle)
