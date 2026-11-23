#!/usr/bin/env python3
"""Generate three-node configuration files; never apply them to this running VM."""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def xml_file(path, values):
    root = ET.Element('configuration')
    for key, value in values.items():
        prop = ET.SubElement(root, 'property')
        ET.SubElement(prop, 'name').text = key
        ET.SubElement(prop, 'value').text = str(value)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def render(config, out, template=False):
    nodes = config['nodes']
    if len(nodes) != 3:
        raise ValueError('必须准确配置三个节点')
    for node in nodes:
        if not re.fullmatch('[a-z][a-z0-9-]{0,30}', node['name']):
            raise ValueError('节点名格式错误')
        if template and node['address'].startswith('CHANGE_ME_NODE'):
            pass
        else:
            ip = ipaddress.ip_address(node['address'])
            if ip.version != 4 or ip.is_loopback or ip.is_unspecified or ip.is_multicast:
                raise ValueError('必须提供三个真实可互访的IPv4地址，不能使用localhost')
        if not isinstance(node['yarn_memory_mb'], int) or not 1024 <= node['yarn_memory_mb'] <= 8192:
            raise ValueError('单节点YARN内存需在1024至8192MB之间；仍需依据实际资源验收')
    if len({n['name'] for n in nodes}) != 3 or len({n['address'] for n in nodes}) != 3:
        raise ValueError('节点名和IP必须互不相同')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    master = nodes[0]['name']
    secondary = nodes[1]['name']
    for node in nodes:
        folder = out / node['name']
        folder.mkdir()
        base = '/opt/taobao/cluster-data'
        xml_file(folder/'core-site.xml', {
            'fs.defaultFS':f'hdfs://{master}:9000', 'hadoop.tmp.dir':base+'/tmp'})
        xml_file(folder/'hdfs-site.xml', {
            'dfs.replication':3,
            'dfs.namenode.name.dir':'file://'+base+'/hdfs/name',
            'dfs.datanode.data.dir':'file://'+base+'/hdfs/data',
            'dfs.namenode.secondary.http-address':f'{secondary}:9868'})
        xml_file(folder/'yarn-site.xml', {
            'yarn.resourcemanager.hostname':master,
            'yarn.nodemanager.aux-services':'mapreduce_shuffle',
            'yarn.nodemanager.resource.memory-mb':node['yarn_memory_mb'],
            'yarn.scheduler.minimum-allocation-mb':256,
            'yarn.scheduler.maximum-allocation-mb':max(n['yarn_memory_mb'] for n in nodes),
            'yarn.nodemanager.resource.cpu-vcores':2,
            'yarn.nodemanager.local-dirs':base+'/yarn/local',
            'yarn.nodemanager.log-dirs':base+'/yarn/logs'})
        xml_file(folder/'mapred-site.xml', {
            'mapreduce.framework.name':'yarn',
            'mapreduce.application.classpath':'/opt/taobao/module/hadoop-3.3.6/share/hadoop/mapreduce/*,/opt/taobao/module/hadoop-3.3.6/share/hadoop/mapreduce/lib/*'})
        xml_file(folder/'tez-site.xml', {
            'tez.lib.uris':f'hdfs://{master}:9000/apps/tez/0.10.4/tez.tar.gz',
            'tez.use.cluster.hadoop-libs':'true',
            'tez.am.resource.memory.mb':512, 'tez.task.resource.memory.mb':512,
            'tez.am.launch.cmd-opts':'-Xmx384m','tez.task.launch.cmd-opts':'-Xmx384m'})
        (folder/'workers').write_text(''.join(n['name']+'\n' for n in nodes))
        (folder/'hosts.fragment').write_text(''.join(n['address']+' '+n['name']+'\n' for n in nodes))
        role = ['DataNode','NodeManager']
        if node == nodes[0]:
            role += ['NameNode','ResourceManager','HiveServer2','Hive metastore database']
        if node == nodes[1]:
            role += ['SecondaryNameNode']
        (folder/'role.json').write_text(json.dumps({'hostname':node['name'],'services':role,
            'status':'template_not_deployed' if template else 'configuration_generated_not_deployed'},ensure_ascii=False,indent=2))
    (out/'STATUS.txt').write_text('仅生成三个节点配置；未创建VMware虚拟机、未克隆、未联网验收。\n配置写入全新cluster-data路径，不引用现有单机HDFS数据。\n')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nodes', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--template', action='store_true', help='仅生成带明确地址占位符的模板，不能部署')
    args = parser.parse_args()
    print(render(json.loads(args.nodes.read_text()), args.out, template=args.template))

if __name__ == '__main__':
    main()
