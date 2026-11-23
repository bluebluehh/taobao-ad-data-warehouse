#!/usr/bin/env bash
# Run as student on the clean template, after copying the verified archives and JDK.
set -euo pipefail
[[ $(hostname -s) == taobao-template ]] || { echo '仅允许在taobao-template运行'; exit 1; }
base=/opt/taobao
[[ ! -e "$base/data/hadoop" && ! -e "$base/cluster-data" ]] || {
  echo '检测到集群数据路径，停止模板准备'; exit 1;
}
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('/opt/taobao/software')
items = json.loads((root/'common-template-checksums.json').read_text())
assert len(items) == 3
for item in items:
    path = root/item['file']
    assert path.parent == root
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, item['algorithm']).hexdigest()
    if actual != item['digest']:
        raise SystemExit('校验失败: '+path.name)
    print('校验通过:', path.name)
PY
for archive in hadoop-3.3.6 apache-hive-4.0.1-bin apache-tez-0.10.4-bin; do
  target="$base/module/$archive"
  if [[ -e "$target" ]]; then
    [[ -f "$target/.common-template-extracted" ]] || { echo "目录已存在，需检查：$target"; exit 1; }
  else
    tar -xzf "$base/software/$archive.tar.gz" -C "$base/module"
    touch "$target/.common-template-extracted"
  fi
done
cat > "$base/common-env.sh" <<'ENV'
export JAVA_HOME=/opt/taobao/module/java-8-openjdk-amd64
export HADOOP_HOME=/opt/taobao/module/hadoop-3.3.6
export HIVE_HOME=/opt/taobao/module/apache-hive-4.0.1-bin
export TEZ_HOME=/opt/taobao/module/apache-tez-0.10.4-bin
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HIVE_HOME/bin:$PATH"
ENV
if ! grep -qxF 'source /opt/taobao/common-env.sh' "$HOME/.bashrc"; then
  printf '\nsource /opt/taobao/common-env.sh\n' >> "$HOME/.bashrc"
fi
source "$base/common-env.sh"
check=$(mktemp -d "$base/checks/common-template-XXXXXXXX")
exec > >(tee "$check/run.log") 2>&1
java -version
javac -version
hadoop version
hive --version
timeout 120 hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" pi 2 1000
[[ ! -e "$base/data/hadoop" && ! -e "$base/cluster-data" ]]
date -Is > "$check/SUCCESS"
echo "公共软件验证通过：$check（仅本地任务，HDFS尚未初始化）"
