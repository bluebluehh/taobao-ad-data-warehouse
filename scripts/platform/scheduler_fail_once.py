#!/usr/bin/env python3
"""Isolated recovery probe. First invocation fails; subsequent recovery succeeds."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
marker=root/'output/scheduler-validation/intentional-failure-once.marker'
marker.parent.mkdir(exist_ok=True)
try:
    with marker.open('x') as out:out.write('Technical failure/recovery validation only.\n')
except FileExistsError:
    print('技术故障点已存在，本次恢复继续执行。')
else:
    raise SystemExit('技术故障点：首次执行按预期失败；上游结果保留，供失败后重跑验证。')
