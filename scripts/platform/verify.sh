#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
report=$(mktemp -d "$project_root/output/platform-verify-XXXXXXXX")
exec > >(tee "$report/run.log") 2>&1
trap 'echo "exit=$?"' EXIT
date -Is
hdfs dfsadmin -report
hdfs dfsadmin -safemode get
schematool -dbType mysql -validate
check_path="/user/$(id -un)/checks/$(basename "$report")"
hdfs dfs -mkdir -p "$check_path"
printf 'taobao-platform-check\n' > "$report/input.txt"
hdfs dfs -put "$report/input.txt" "$check_path/input.txt"
hdfs dfs -cat "$check_path/input.txt" > "$report/readback.txt"
cmp "$report/input.txt" "$report/readback.txt"
timeout 120 beeline -u 'jdbc:hive2://' -e 'SHOW DATABASES; SELECT 1 AS platform_check;'
echo 'HDFS roundtrip and Hive constant query PASS; Tez execution is a separate check.'
