#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
report=$(mktemp -d "$project_root/output/tez-verify-XXXXXXXX")
exec > >(tee "$report/run.log") 2>&1
trap 'echo "exit=$?"' EXIT
# Synthetic infrastructure test only; never include in business analysis.
printf 'alpha\t1\nalpha\t2\nbeta\t4\n' > "$report/input.tsv"
name="probe_$(date +%Y%m%d%H%M%S)_${RANDOM}"
path="/user/$(id -un)/checks/$name"
hdfs dfs -mkdir -p /apps/tez/0.10.4 "$path"
if ! hdfs dfs -test -e /apps/tez/0.10.4/tez.tar.gz; then
 hdfs dfs -put "$TEZ_HOME/share/tez.tar.gz" /apps/tez/0.10.4/tez.tar.gz
fi
hdfs dfs -put "$report/input.tsv" "$path/input.tsv"
cat > "$report/query.sql" <<SQL
SET hive.execution.engine=tez;
SET hive.fetch.task.conversion=none;
SET hive.tez.container.size=512;
SET hive.tez.java.opts=-Xmx384m;
SET hive.auto.convert.join=false;
CREATE DATABASE IF NOT EXISTS platform_validation;
CREATE EXTERNAL TABLE platform_validation.$name (label STRING, amount INT)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\\t' STORED AS TEXTFILE LOCATION '$path';
SELECT label, SUM(amount) AS total FROM platform_validation.$name GROUP BY label ORDER BY label;
SQL
timeout 240 beeline --silent=true --showHeader=false --outputformat=tsv2 -u 'jdbc:hive2://' -f "$report/query.sql" > "$report/result.tsv" 2> "$report/query.log"
cat "$report/result.tsv"
printf 'alpha\t3\nbeta\t4\n' > "$report/expected.tsv"
cmp "$report/expected.tsv" "$report/result.tsv"
echo 'Tez grouped totals PASS. Test artifacts retained in platform_validation and HDFS checks.'
