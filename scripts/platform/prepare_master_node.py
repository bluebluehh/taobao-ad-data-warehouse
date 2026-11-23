#!/usr/bin/env python3
"""Prepare hostname-based configs; does not initialize or start HDFS/YARN."""
import json
import os
from pathlib import Path
import shutil
import socket
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('/opt/taobao')


def xml(path, values, private=False):
    root = ET.Element('configuration')
    for name, value in values.items():
        prop = ET.SubElement(root, 'property')
        ET.SubElement(prop, 'name').text = name
        ET.SubElement(prop, 'value').text = str(value)
    ET.indent(root)
    with os.fdopen(os.open(path, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600 if private else 0o644), 'wb') as out:
        ET.ElementTree(root).write(out, encoding='utf-8', xml_declaration=True)


def main():
    if socket.gethostname().split('.')[0] != 'adw101':
        raise SystemExit('仅允许在adw101运行')
    if (BASE/'cluster-data').exists() or (BASE/'data/hadoop').exists():
        raise SystemExit('发现HDFS运行目录，停止；本工具只用于首次准备')
    marker = Path('/etc/taobao-clone-identity')
    if not marker.is_file() or marker.read_text().strip() != 'adw101':
        raise SystemExit('独立节点身份尚未完成')
    conf = BASE/'node-conf'
    conf.mkdir(mode=0o700, exist_ok=True)
    hadoop = conf/'hadoop'
    if not hadoop.exists():
        shutil.copytree(BASE/'module/hadoop-3.3.6/etc/hadoop', hadoop)
    for name in ['core-site.xml', 'hdfs-site.xml', 'yarn-site.xml', 'mapred-site.xml', 'workers']:
        shutil.copy2(ROOT/'platform/cluster/templates/adw101'/name, hadoop/name)
    (hadoop/'hadoop-env.sh').write_text('export JAVA_HOME=/opt/taobao/module/java-8-openjdk-amd64\nexport HADOOP_HEAPSIZE_MAX=256\nexport YARN_HEAPSIZE=256\n')
    tez = conf/'tez'
    tez.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'platform/cluster/templates/adw101/tez-site.xml', tez/'tez-site.xml')
    hive = conf/'hive'
    hive.mkdir(mode=0o700, exist_ok=True)
    c = json.loads((BASE/'data/reporting/credentials.json').read_text())
    xml(hive/'hive-site.xml', {
        'javax.jdo.option.ConnectionURL': 'jdbc:mysql://127.0.0.1:3307/hive_metastore?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai',
        'javax.jdo.option.ConnectionDriverName': 'com.mysql.cj.jdbc.Driver',
        'javax.jdo.option.ConnectionUserName': 'hive_metastore',
        'javax.jdo.option.ConnectionPassword': c['hive_metastore'],
        'hive.metastore.schema.verification': 'true',
        'datanucleus.schema.autoCreateAll': 'false',
        'hive.metastore.warehouse.dir': 'hdfs://adw101:9000/user/hive/warehouse',
        'hive.execution.engine': 'tez',
        'hive.local.time.zone': 'Asia/Shanghai',
        'hive.tez.container.size': 512,
        'hive.tez.java.opts': '-Xmx384m',
        'hive.server2.thrift.bind.host': '127.0.0.1',
        'hive.server2.enable.doAs': 'false',
    }, private=True)
    (BASE/'node-env.sh').write_text('''source /opt/taobao/common-env.sh
export TAOBAO_HADOOP_CONF_DIR=/opt/taobao/node-conf/hadoop
export TAOBAO_HIVE_CONF_DIR=/opt/taobao/node-conf/hive
export TAOBAO_TEZ_CONF_DIR=/opt/taobao/node-conf/tez
export HADOOP_CONF_DIR="$TAOBAO_HADOOP_CONF_DIR"
export HIVE_CONF_DIR="$TAOBAO_HIVE_CONF_DIR"
export TEZ_CONF_DIR="$TAOBAO_TEZ_CONF_DIR"
export HADOOP_CLASSPATH="$TEZ_CONF_DIR:$TEZ_HOME/*:$TEZ_HOME/lib/*"
export PATH="/opt/taobao/module/mysql-ubuntu-8.0.46/usr/bin:$PATH"
export LD_LIBRARY_PATH="/opt/taobao/module/mysql-ubuntu-8.0.46/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
''')
    bashrc = Path.home()/'.bashrc'
    line = 'source /opt/taobao/node-env.sh'
    if line not in bashrc.read_text().splitlines():
        with bashrc.open('a') as out:
            out.write('\n'+line+'\n')
    (conf/'STATUS.json').write_text(json.dumps({
        'node': 'adw101', 'configuration': 'prepared_hostname_based',
        'network': 'pending_cross_network_addresses_and_connectivity',
        'hdfs': 'not_initialized', 'hive_schema': 'requires_initialization_and_validation',
        'services': ['NameNode', 'ResourceManager', 'DataNode', 'NodeManager', 'Hive'],
    }, indent=2)+'\n')
    print('主节点配置已准备；未修改hosts，未启动或初始化HDFS/YARN。')


if __name__ == '__main__':
    main()
