#!/usr/bin/env bash
# Run locally with sudo on each unused clone; never run on the original template.
set -euo pipefail
node=${1:-}
case "$node" in adw101|adw102|adw103) ;; *) echo '用法：sudo bash personalize_clone.sh adw101|adw102|adw103'; exit 1;; esac
[[ $EUID == 0 && $(hostname -s) == "$node" ]] || {
  echo '请先设置正确节点主机名，并在对应副本使用sudo执行'; exit 1;
}
[[ ! -e /opt/taobao/data/hadoop && ! -e /opt/taobao/cluster-data ]] || {
  echo '发现集群数据路径，停止；本脚本仅用于尚未初始化的副本'; exit 1;
}
marker=/etc/taobao-clone-identity
if [[ -f $marker ]]; then
  [[ $(cat "$marker") == "$node" ]] || { echo '已有其他节点身份，停止'; exit 1; }
  echo '该节点已处理，保留已有独立身份'
  exit 0
fi
scratch=$(mktemp -d /etc/ssh/.taobao-new-hostkeys-XXXXXXXX)
trap 'rm -rf "$scratch"' EXIT
for type in rsa ecdsa ed25519; do
  ssh-keygen -q -t "$type" -N '' -f "$scratch/ssh_host_${type}_key"
done
new_id=$(systemd-id128 new)
[[ $new_id =~ ^[0-9a-f]{32}$ ]] || exit 1
printf '%s\n' "$new_id" > /etc/machine-id
if [[ -e /var/lib/dbus/machine-id && ! -L /var/lib/dbus/machine-id ]]; then
  printf '%s\n' "$new_id" > /var/lib/dbus/machine-id
fi
for type in rsa ecdsa ed25519; do
  install -m 600 "$scratch/ssh_host_${type}_key" "/etc/ssh/ssh_host_${type}_key"
  install -m 644 "$scratch/ssh_host_${type}_key.pub" "/etc/ssh/ssh_host_${type}_key.pub"
done
python3 - "$node" <<'PY'
from pathlib import Path
import sys
p = Path('/etc/hosts')
lines = p.read_text().splitlines()
lines = [line for line in lines if not line.split('#', 1)[0].split()[:1] == ['127.0.1.1']]
lines.append('127.0.1.1\t'+sys.argv[1])
p.write_text('\n'.join(lines)+'\n')
PY
/usr/sbin/sshd -t
printf '%s\n' "$node" > "$marker"
chmod 644 "$marker"
echo "已生成 $node 的独立身份，请重启以生效。"
echo "新的机器ID：$new_id"
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
