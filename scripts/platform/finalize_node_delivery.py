#!/usr/bin/env python3
"""Check a distributable node and revoke only this project's temporary setup key."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import xml.etree.ElementTree as ET

SETUP_KEY = 'AAAAC3NzaC1lZDI1NTE5AAAAIP1r6MxMMwZY0SC79Zm+ThoZmRzm8BVT0zvuCcHMzSj3'


def without_setup_key(text):
    kept = []
    removed = 0
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith('#'):
            kept.append(line)
            continue
        fields = line.split()
        matches = any(fields[i] == 'ssh-ed25519' and fields[i+1] == SETUP_KEY for i in range(len(fields)-1))
        if matches:
            removed += 1
        else:
            kept.append(line)
    return ''.join(kept), removed


def main(finalize=False):
    node = socket.gethostname().split('.')[0]
    if node not in ['adw101', 'adw102', 'adw103']:
        raise SystemExit('仅允许在三个项目节点执行')
    if os.getuid() == 0:
        raise SystemExit('请以student用户执行，不使用sudo')
    base = Path('/opt/taobao')
    home = Path.home()
    if Path('/etc/taobao-clone-identity').read_text().strip() != node:
        raise SystemExit('节点独立身份不符')
    for path in [base/'cluster-data', base/'data/hadoop']:
        if path.exists():
            raise SystemExit('发现HDFS运行目录，停止分发清理，不删除数据')
    if (base/'node-conf/NETWORK_VERIFIED').exists():
        raise SystemExit('已有联网验收标记，需核实分发状态')
    for relative in ['.codex', '.aws', '.azure', '.config/gcloud', '.config/gh']:
        if (home/relative).exists():
            raise SystemExit('发现需核实的个人配置目录，保留并停止：'+relative)
    ssh = home/'.ssh'
    for path in ssh.glob('*'):
        if path.is_file():
            head = path.read_bytes()[:2048]
            if b'PRIVATE KEY-----' in head:
                raise SystemExit('发现用户SSH私钥，保留并停止：'+path.name)
    for path in (base/'node-conf/hadoop').glob('*-site.xml'):
        ET.parse(path)
    state = json.loads(subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, check=True).stdout)
    if state.get('BackendState') != 'NeedsLogin' or state.get('TailscaleIPs'):
        raise SystemExit('Tailscale已有设备认证或状态不符，停止，不自动退出账号')
    roles = ['datanode', 'nodemanager']
    if node == 'adw101':
        roles += ['namenode', 'resourcemanager', 'hiveserver2', 'superset', 'dolphinscheduler', 'node-mysql']
    if node == 'adw102':
        roles += ['secondarynamenode']
    units = ['taobao-'+r for r in roles]
    if finalize:
        # The order stops applications before their local metadata database.
        subprocess.run(['systemctl', '--user', 'stop', *units], check=True, capture_output=True)
    active = [u for u in units if subprocess.run(['systemctl', '--user', 'is-active', '--quiet', u]).returncode == 0]
    if finalize and active:
        raise SystemExit('仍有项目服务运行，未撤销访问授权：'+','.join(active))
    keys = ssh/'authorized_keys'
    original = keys.read_text() if keys.exists() else ''
    cleaned, count = without_setup_key(original)
    receipt = {'node': node, 'machine_id': Path('/etc/machine-id').read_text().strip(),
        'tailscale_version': subprocess.check_output(['tailscale', 'version'], text=True).splitlines()[0],
        'tailscale_state': 'NeedsLogin', 'hdfs': 'not_initialized',
        'personal_cloud_config_and_user_ssh_private_keys': 'not_found_in_checked_locations',
        'checked_locations': ['~/.codex', '~/.aws', '~/.azure', '~/.config/gcloud', '~/.config/gh', '~/.ssh'],
        'active_project_services': active, 'temporary_setup_key_entries': count,
        'state': 'checked_not_finalized', 'archive': 'not_created',
        'cluster_network': 'not_yet_validated', 'real_data_analysis': 'not_started'}
    if finalize:
        if count:
            descriptor, name = tempfile.mkstemp(prefix='.authorized_keys-taobao-', dir=ssh)
            with os.fdopen(descriptor, 'w') as out:
                out.write(cleaned)
            os.replace(name, keys)
        receipt.update(state='guest_prepared_for_shutdown_and_archive', temporary_setup_key='revoked')
        folder = base/'checks/delivery'
        folder.mkdir(exist_ok=True)
        (folder/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finalize', action='store_true', help='停止项目服务，并仅撤销本项目的临时配置公钥')
    main(parser.parse_args().finalize)
