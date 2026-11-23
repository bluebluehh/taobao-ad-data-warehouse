#!/usr/bin/env python3
"""Validate a prepared worker locally; never contact or initialize HDFS."""
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import xml.etree.ElementTree as ET

BASE = Path('/opt/taobao')


def main():
    node = socket.gethostname().split('.')[0]
    if node not in ['adw102', 'adw103']:
        raise SystemExit('仅允许在工作节点adw102/adw103运行')
    conf = BASE/'node-conf'
    if (conf/'NETWORK_VERIFIED').exists():
        raise SystemExit('已有联网验收标记，停止离线启动拦截测试')
    for path in [BASE/'cluster-data', BASE/'data/hadoop']:
        if path.exists():
            raise SystemExit('发现集群运行目录，停止离线验证')
    roles = ['datanode', 'nodemanager']
    if node == 'adw102':
        roles.append('secondarynamenode')
    logs = BASE/'checks/worker-preparation'
    logs.mkdir(exist_ok=True)
    for path in list((conf/'hadoop').glob('*-site.xml')) + [conf/'tez/tez-site.xml']:
        tree = ET.parse(path)
        assert all('CHANGE_ME' not in (p.findtext('value') or '') for p in tree.findall('property'))
    def properties(name):
        return {p.findtext('name'): p.findtext('value') for p in ET.parse(conf/'hadoop'/name).getroot()}
    assert properties('core-site.xml')['fs.defaultFS'] == 'hdfs://adw101:9000'
    assert properties('hdfs-site.xml')['dfs.namenode.secondary.http-address'] == 'adw102:9868'
    assert properties('yarn-site.xml')['yarn.resourcemanager.hostname'] == 'adw101'
    units = [str(Path.home()/'.config/systemd/user'/('taobao-'+r+'.service')) for r in roles]
    with (logs/'unit-validation.log').open('w') as out:
        subprocess.run(['systemd-analyze', '--user', 'verify', *units], stdout=out, stderr=subprocess.STDOUT, check=True)
    for role in roles:
        unit = 'taobao-'+role
        if subprocess.run(['systemctl', '--user', 'is-active', '--quiet', unit]).returncode == 0:
            raise SystemExit('已有节点服务运行，停止离线测试：'+unit)
        result = subprocess.run(['systemctl', '--user', 'start', unit], capture_output=True, text=True)
        pre = subprocess.check_output(['systemctl', '--user', 'show', unit, '-p', 'ExecStartPre'], text=True)
        if result.returncode == 0 or 'NETWORK_VERIFIED' not in pre or 'status=1' not in pre:
            raise SystemExit('启动拦截未按预期生效：'+unit)
        subprocess.run(['systemctl', '--user', 'reset-failed', unit], check=True)
    with tempfile.TemporaryDirectory(prefix='local-task-', dir=logs) as taskdir:
        with (logs/'local-pi.log').open('w') as out:
            result = subprocess.run(['bash', '-c', '''source /opt/taobao/node-env.sh
exec hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" pi \
 -Dmapreduce.framework.name=local -Dfs.defaultFS=file:/// -Dhadoop.tmp.dir="$1/tmp" 2 1000
''', 'local-check', taskdir], cwd=taskdir, stdout=out, stderr=subprocess.STDOUT, timeout=120)
        if result.returncode or 'Estimated value of Pi is 3.144' not in (logs/'local-pi.log').read_text():
            raise SystemExit('工作节点本地任务未通过，请查看节点内local-pi.log')
    assert not (BASE/'cluster-data').exists()
    assert not (BASE/'data/hadoop').exists()
    states = subprocess.check_output(['systemctl', '--user', 'show', *['taobao-'+r for r in roles],
                                     '-p', 'Id', '-p', 'ActiveState', '-p', 'UnitFileState'], text=True)
    result = {'node': node, 'roles': roles, 'configuration_xml': 'passed',
        'systemd_unit_validation': 'passed', 'offline_start_guards': 'passed',
        'local_mapreduce_pi': 'passed', 'services': states, 'hdfs': 'not_initialized',
        'cluster_network': 'not_yet_validated', 'memory_budget': 'provisional'}
    (logs/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
