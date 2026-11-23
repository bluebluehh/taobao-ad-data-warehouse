#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
export YARN_HEAPSIZE=256
case "${1:-status}" in
 start)
  # This entry point ONLY resumes the existing single-machine instance; it never formats HDFS.
  python3 - <<'PY'
from pathlib import Path
versions=[]
for role in ['name','data']:
 p=Path('/opt/taobao/data/hadoop')/role/'current/VERSION'
 if not p.is_file():raise SystemExit('已有HDFS身份文件缺失，停止；禁止自动格式化：'+str(p))
 values=dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.startswith('#'))
 versions.append(values['clusterID'])
if versions[0]!=versions[1]:raise SystemExit('NameNode与DataNode集群身份不一致，停止')
print('现有HDFS身份检查通过，保留原数据')
PY
  for role in namenode datanode secondarynamenode; do
   if ! "$HADOOP_HOME/bin/hdfs" --daemon status "$role" >/dev/null 2>&1; then
    "$HADOOP_HOME/bin/hdfs" --daemon start "$role"
   fi
  done
  timeout 90 "$HADOOP_HOME/bin/hdfs" dfsadmin -safemode wait
  for role in resourcemanager nodemanager; do
   if ! "$HADOOP_HOME/bin/yarn" --daemon status "$role" >/dev/null 2>&1; then
    "$HADOOP_HOME/bin/yarn" --daemon start "$role"
   fi
  done
  "$HADOOP_HOME/bin/hdfs" dfsadmin -report
  ;;
 status)
  jps -l
  "$HADOOP_HOME/bin/hdfs" dfsadmin -safemode get
  ;;
 *) echo '使用：bash scripts/platform/hadoop_services.sh start|status' >&2;exit 2;;
esac
