#!/usr/bin/env python3
"""Team commissioning helpers. No development storage, automatic formatting, or credentials."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('/opt/taobao')
NODES = ('adw101', 'adw102', 'adw103')


def validate_plan(plan):
    if set(plan) != set(NODES):
        raise ValueError('地址表必须准确包含adw101、adw102、adw103')
    for address in plan.values():
        ip = ipaddress.ip_address(address)
        if ip.version != 4 or ip not in ipaddress.ip_network('100.64.0.0/10'):
            raise ValueError('必须填写tailscale ip -4得到的100.64.0.0/10内地址，不能填VMware NAT地址')
    if len(set(plan.values())) != 3:
        raise ValueError('三台地址必须不同')
    return plan


def render_hosts(text, plan):
    output = []
    for line in text.splitlines():
        if line.strip() in ['# BEGIN TAOBAO TEAM', '# END TAOBAO TEAM']:
            continue
        body, sep, comment = line.partition('#')
        fields = body.split()
        if len(fields) >= 2 and any(n in NODES for n in fields[1:]):
            aliases = [n for n in fields[1:] if n not in NODES]
            if aliases:
                output.append(fields[0]+'\t'+' '.join(aliases)+((' #'+comment) if sep else ''))
            elif sep:
                output.append('#'+comment)
        else:
            output.append(line)
    output += ['# BEGIN TAOBAO TEAM']+[plan[n]+' '+n for n in NODES]+['# END TAOBAO TEAM']
    return '\n'.join(output)+'\n'


def require_empty(path):
    if path.resolve() != path.absolute():
        raise ValueError('存储路径含符号链接，拒绝格式化：'+str(path))
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError('目录已有内容，拒绝格式化或覆盖：'+str(path))


def command(text, timeout=120):
    return subprocess.run(['bash', '-c', 'source /opt/taobao/node-env.sh; '+text],
                          check=True, timeout=timeout)


def live_node(plan):
    node = socket.gethostname().split('.')[0]
    if node not in NODES:
        raise ValueError('只能在三个已配置项目节点运行，不能在旧开发机或模板运行')
    identities = json.loads((ROOT/'platform/team/node-identities.json').read_text())
    if Path('/etc/machine-id').read_text().strip() != identities[node]['machine_id']:
        raise ValueError('机器ID与交付记录不符，停止；请先由组内核实是否打开了正确副本')
    state = json.loads(subprocess.check_output(['tailscale', 'status', '--json'], text=True))
    if state.get('BackendState') != 'Running' or plan[node] not in (state.get('TailscaleIPs') or []):
        raise ValueError('本机尚未登录Tailscale，或地址表与本机地址不符')
    return node, identities


def verify(plan, node, identities):
    marker = BASE/'node-conf/NETWORK_VERIFIED'
    marker.unlink(missing_ok=True)
    for peer in NODES:
        addresses = {r[4][0] for r in socket.getaddrinfo(peer, 22, socket.AF_INET, socket.SOCK_STREAM)}
        if addresses != {plan[peer]}:
            raise ValueError(peer+'主机名解析不符：'+str(addresses)+'；先执行configure')
        with socket.create_connection((plan[peer], 22), timeout=8):
            pass
        result = subprocess.run(['ssh-keyscan', '-T', '8', '-t', 'ed25519', plan[peer]],
                                capture_output=True, text=True, timeout=15)
        keys = [line.split()[2] for line in result.stdout.splitlines() if line and not line.startswith('#') and len(line.split()) == 3]
        if identities[peer]['ssh_ed25519'] not in keys:
            raise ValueError(peer+' SSH主机身份与交付记录不符；不自动接受新身份')
        print('PASS 主机解析、SSH端口、节点身份：'+peer, flush=True)
    receipt = {'node': node, 'addresses': plan, 'machine_id': identities[node]['machine_id'],
               'scope': 'three SSH endpoints and pinned host identities; Hadoop ports checked after startup'}
    marker.write_text(json.dumps(receipt, indent=2)+'\n')
    print('PASS 基础网络验收，已生成本机启动标记。三台都需分别通过。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['configure', 'verify', 'resources', 'init-namenode', 'report-access'])
    parser.add_argument('--plan', type=Path, default=ROOT/'platform/team/nodes.json')
    parser.add_argument('--confirm-first-initialization', action='store_true')
    args = parser.parse_args()
    plan = validate_plan(json.loads(args.plan.read_text()))
    node, identities = live_node(plan)
    if args.action == 'configure':
        if os.geteuid() != 0:
            raise ValueError('configure需要sudo，仅用于本机hosts和已启用的UFW规则')
        hosts = Path('/etc/hosts')
        backup = Path('/etc/hosts.before-taobao-team')
        if not backup.exists():
            shutil.copy2(hosts, backup)
        hosts.write_text(render_hosts(hosts.read_text(), plan))
        (BASE/'node-conf/NETWORK_VERIFIED').unlink(missing_ok=True)
        if shutil.which('ufw'):
            state = subprocess.check_output(['ufw', 'status'], text=True, env={**os.environ, 'LC_ALL':'C'})
            if 'Status: active' in state:
                for peer in NODES:
                    if peer != node:
                        subprocess.run(['ufw', 'allow', 'in', 'on', 'tailscale0', 'from', plan[peer]], check=True)
        print('PASS 本机hosts已更新；未关闭防火墙，只对已启用UFW添加项目同伴入口。')
    elif args.action == 'verify':
        if os.geteuid() == 0:
            raise ValueError('verify请用student运行，不加sudo')
        verify(plan, node, identities)
    elif args.action == 'report-access':
        if node != 'adw101' or os.geteuid() == 0:
            raise ValueError('仅adw101的student可设置报表入口')
        if subprocess.run(['systemctl','--user','is-active','--quiet','taobao-superset']).returncode == 0:
            raise ValueError('先停止taobao-superset，再设置监听地址')
        folder = Path.home()/'.config/systemd/user/taobao-superset.service.d'
        folder.mkdir(parents=True, exist_ok=True)
        runtime = ROOT/'output/superset'
        runtime.mkdir(parents=True, exist_ok=True)
        (folder/'team.conf').write_text('[Service]\n'
            +'Environment=SUPERSET_CONFIG_PATH='+str(ROOT/'platform/superset/superset_config.py')+'\n'
            +'Environment=FLASK_APP=superset\n'
            +'ExecStart=\nExecStart=/opt/taobao/module/superset-6.1.0-venv/bin/gunicorn '
            +'--workers 1 --threads 2 --timeout 120 --bind 127.0.0.1:8089 --bind '+plan[node]+':8089 '
            +'--pid '+str(runtime/'server.pid')+' --access-logfile '+str(runtime/'access.log')
            +' --error-logfile '+str(runtime/'error.log')+' superset.app:create_app()\n')
        subprocess.run(['systemctl','--user','daemon-reload'], check=True)
        print('PASS 报表入口配置为本机回环及项目私有地址；未启动报表服务。')
    elif args.action == 'resources':
        if os.geteuid() == 0:
            raise ValueError('resources请用student运行')
        daemons = subprocess.check_output([str(BASE/'module/java-8-openjdk-amd64/bin/jps'), '-l'], text=True)
        if any(name in daemons for name in ['NameNode','DataNode','NodeManager','ResourceManager','HiveServer2']):
            raise ValueError('先停止Hadoop/Hive服务，再设置资源预算')
        path = BASE/'node-conf/hadoop/yarn-site.xml'
        tree = ET.parse(path)
        values = {'yarn.nodemanager.resource.memory-mb': '512' if node == 'adw101' else '1024',
                  'yarn.scheduler.maximum-allocation-mb': '1024',
                  'yarn.nodemanager.hostname': node,
                  'yarn.nodemanager.vmem-check-enabled': 'false'}
        root = tree.getroot()
        for key, value in values.items():
            prop = next((p for p in root if p.findtext('name') == key), None)
            if prop is None:
                prop = ET.SubElement(root, 'property')
                ET.SubElement(prop, 'name').text = key
                ET.SubElement(prop, 'value')
            prop.find('value').text = value
        ET.indent(root)
        tree.write(path, encoding='utf-8', xml_declaration=True)
        hdfs = BASE/'node-conf/hadoop/hdfs-site.xml'
        tree = ET.parse(hdfs)
        root = tree.getroot()
        for key, value in {'dfs.datanode.hostname':node, 'dfs.client.use.datanode.hostname':'true',
                           'dfs.datanode.use.datanode.hostname':'true'}.items():
            prop = next((p for p in root if p.findtext('name') == key), None)
            if prop is None:
                prop = ET.SubElement(root,'property')
                ET.SubElement(prop,'name').text = key
                ET.SubElement(prop,'value')
            prop.find('value').text = value
        ET.indent(root)
        tree.write(hdfs, encoding='utf-8', xml_declaration=True)
        capacity = BASE/'node-conf/hadoop/capacity-scheduler.xml'
        tree = ET.parse(capacity)
        root = tree.getroot()
        key = 'yarn.scheduler.capacity.maximum-am-resource-percent'
        prop = next((p for p in root if p.findtext('name') == key), None)
        if prop is None:
            prop = ET.SubElement(root,'property')
            ET.SubElement(prop,'name').text = key
            ET.SubElement(prop,'value')
        prop.find('value').text = '0.4'
        ET.indent(root)
        tree.write(capacity, encoding='utf-8', xml_declaration=True)
        env = BASE/'node-conf/hadoop/hadoop-env.sh'
        text = env.read_text().replace('export HADOOP_HEAPSIZE_MAX=256', 'export HADOOP_HEAPSIZE_MAX=${HADOOP_HEAPSIZE_MAX:-256}')
        env.write_text(text)
        print('PASS 初始保守预算：主节点YARN 512MB，工作节点1024MB；关闭虚拟内存比率检查，保留物理内存检查。')
    else:
        if node != 'adw101' or os.geteuid() == 0:
            raise ValueError('仅adw101的student可执行首次初始化')
        if not args.confirm_first_initialization:
            raise ValueError('首次初始化需显式添加--confirm-first-initialization；日常启动不使用此操作')
        name = BASE/'cluster-data/hdfs/name'
        if (name/'current/VERSION').exists():
            print('已有NameNode身份，保留全部数据，跳过格式化；直接使用日常启动步骤。')
            return
        require_empty(name)
        require_empty(BASE/'cluster-data/hdfs/data')
        conf = ET.parse(BASE/'node-conf/hadoop/hdfs-site.xml')
        properties = {p.findtext('name'):p.findtext('value') for p in conf.getroot()}
        if properties.get('dfs.namenode.name.dir') != 'file:///opt/taobao/cluster-data/hdfs/name':
            raise ValueError('NameNode目录配置不符，停止')
        verify(plan, node, identities)
        logs = ROOT/'output/team'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs/'first-format.log').open('w') as log:
            subprocess.run(['bash','-c','source /opt/taobao/node-env.sh; exec hdfs namenode -format -nonInteractive'],
                           check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        if not (name/'current/VERSION').exists():
            raise ValueError('初始化未生成身份文件，检查output/team/first-format.log，禁止强制重试')
        print('PASS 首次NameNode初始化完成，后续不得再次格式化。')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit('STOP '+str(error))
