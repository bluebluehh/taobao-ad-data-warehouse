#!/usr/bin/env python3
"""Install per-node Hadoop configs and gated user services, without formatting HDFS."""
import json
from pathlib import Path
import shutil
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('/opt/taobao')


def main(node):
    if node not in ['adw101', 'adw102', 'adw103'] or socket.gethostname().split('.')[0] != node:
        raise SystemExit('只能在对应的adw101/adw102/adw103节点运行')
    if Path('/etc/taobao-clone-identity').read_text().strip() != node:
        raise SystemExit('节点独立身份不符')
    if (BASE/'cluster-data').exists() or (BASE/'data/hadoop').exists():
        raise SystemExit('发现HDFS运行目录，停止；不覆盖已运行集群的配置')
    conf = BASE/'node-conf'
    conf.mkdir(mode=0o700, exist_ok=True)
    hadoop = conf/'hadoop'
    if not hadoop.exists():
        shutil.copytree(BASE/'module/hadoop-3.3.6/etc/hadoop', hadoop)
    for name in ['core-site.xml', 'hdfs-site.xml', 'yarn-site.xml', 'mapred-site.xml', 'workers']:
        shutil.copy2(ROOT/'platform/cluster/templates'/node/name, hadoop/name)
    (hadoop/'hadoop-env.sh').write_text('export JAVA_HOME=/opt/taobao/module/java-8-openjdk-amd64\nexport HADOOP_HEAPSIZE_MAX=256\nexport YARN_HEAPSIZE=256\n')
    tez = conf/'tez'
    tez.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'platform/cluster/templates'/node/'tez-site.xml', tez/'tez-site.xml')
    lines = ['source /opt/taobao/common-env.sh',
        'export TAOBAO_HADOOP_CONF_DIR=/opt/taobao/node-conf/hadoop',
        'export TAOBAO_TEZ_CONF_DIR=/opt/taobao/node-conf/tez',
        'export HADOOP_CONF_DIR="$TAOBAO_HADOOP_CONF_DIR"',
        'export TEZ_CONF_DIR="$TAOBAO_TEZ_CONF_DIR"',
        'export HADOOP_CLASSPATH="$TEZ_CONF_DIR:$TEZ_HOME/*:$TEZ_HOME/lib/*"']
    if node == 'adw101':
        lines += ['export TAOBAO_HIVE_CONF_DIR=/opt/taobao/node-conf/hive',
            'export HIVE_CONF_DIR="$TAOBAO_HIVE_CONF_DIR"',
            'export PATH="/opt/taobao/module/mysql-ubuntu-8.0.46/usr/bin:$PATH"',
            'export LD_LIBRARY_PATH="/opt/taobao/module/mysql-ubuntu-8.0.46/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"']
    (BASE/'node-env.sh').write_text('\n'.join(lines)+'\n')
    bashrc = Path.home()/'.bashrc'
    line = 'source /opt/taobao/node-env.sh'
    if line not in bashrc.read_text().splitlines():
        with bashrc.open('a') as out:
            out.write('\n'+line+'\n')
    roles = {'datanode': 'hdfs datanode', 'nodemanager': 'yarn nodemanager'}
    if node == 'adw101':
        roles.update(namenode='hdfs namenode', resourcemanager='yarn resourcemanager', hiveserver2='hive --service hiveserver2')
    if node == 'adw102':
        roles['secondarynamenode'] = 'hdfs secondarynamenode'
    units = Path.home()/'.config/systemd/user'
    units.mkdir(parents=True, exist_ok=True)
    for role, command in roles.items():
        heap = 512 if role == 'hiveserver2' else 256
        additional = ''
        if role == 'namenode':
            additional = 'ExecStartPre=/usr/bin/test -f /opt/taobao/cluster-data/hdfs/name/current/VERSION\n'
        if role == 'hiveserver2':
            additional += 'ExecStartPre=/usr/bin/test -f /opt/taobao/checks/master-metadata/SUCCESS\n'
        (units/('taobao-'+role+'.service')).write_text(f'''[Unit]
Description=Taobao {node} {role} (requires verified cluster network)

[Service]
Type=simple
WorkingDirectory=/opt/taobao
ExecStartPre=/usr/bin/test -f /opt/taobao/node-conf/NETWORK_VERIFIED
{additional}ExecStart=/bin/bash -c 'source /opt/taobao/node-env.sh; export HADOOP_HEAPSIZE_MAX={heap} YARN_HEAPSIZE=256; exec {command}'
Restart=no
SuccessExitStatus=143
TimeoutStopSec=60

[Install]
WantedBy=default.target
''')
    (conf/'hadoop-readiness.json').write_text(json.dumps({'node': node, 'roles': list(roles),
        'state': 'configured_not_started', 'network_verified': False, 'hdfs_initialized': False,
        'memory_budget': 'provisional_requires_real_cluster_validation'}, indent=2)+'\n')
    print(node+'职责配置和手动服务入口已准备；联网验收前启动受阻，不初始化HDFS。')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('用法：prepare_hadoop_node.py adw101|adw102|adw103')
    main(sys.argv[1])
