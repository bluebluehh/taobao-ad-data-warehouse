"""人工技术样例；不用于项目真实业务分析。"""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import json
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts/platform'/f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

stage = module('stage_csv')
cluster = module('render_cluster')

class DeliveryKeys(unittest.TestCase):
    def test_revoke_only_setup_key_preserving_other_access_and_comments(self):
        tool = module('finalize_node_delivery')
        retained = '# ssh-ed25519 '+tool.SETUP_KEY+' example\n\nssh-ed25519 OTHER_KEY teammate\n'
        source = retained+'restrict ssh-ed25519 '+tool.SETUP_KEY+' setup\n'
        source += 'ssh-ed25519 '+tool.SETUP_KEY+' duplicate\n'
        result, count = tool.without_setup_key(source)
        self.assertEqual(result, retained)
        self.assertEqual(count, 2)

    def test_without_setup_key_keeps_file_unchanged(self):
        tool = module('finalize_node_delivery')
        source = 'ssh-rsa OTHER_KEY owner\n# preserved comment'
        self.assertEqual(tool.without_setup_key(source), (source, 0))

class NodeSafety(unittest.TestCase):
    def test_master_tools_refuse_template_and_development_hosts(self):
        for name in ['node_mysql', 'prepare_master_node', 'init_node_metastore']:
            tool = module(name)
            for host in ['taobao-template', 'development', 'adw102']:
                with self.subTest(tool=name, host=host), patch.object(tool.socket, 'gethostname', return_value=host):
                    with self.assertRaisesRegex(SystemExit, '仅允许在adw101'):
                        if name == 'node_mysql':
                            tool.main('bootstrap')
                        else:
                            tool.main()

class Staging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root/'raw_sample.csv'
        self.out = self.root/'raw.tsv'
        self.header = ','.join(stage.HEADERS['raw_sample'])+'\n'

    def test_duplicate_exposures_and_provenance(self):
        self.src.write_text(self.header+'1,1494000000,2,slot_a,1,0\n'*2)
        report = stage.stage_file(self.src,self.out,stage.HEADERS['raw_sample'])
        self.assertEqual(report['rows'],2)
        self.assertEqual([row.split('\t')[:2] for row in self.out.read_text().splitlines()],
                         [['raw_sample.csv','2'],['raw_sample.csv','3']])
        self.assertEqual(report['staged_sha256'],stage.file_sha256(self.out))

    def test_bad_header(self):
        self.src.write_text('unknown,header\n')
        with self.assertRaises(ValueError):stage.stage_file(self.src,self.out,stage.HEADERS['raw_sample'])
        self.assertFalse(self.out.exists())

    def test_does_not_overwrite(self):
        self.out.write_text('keep this')
        with self.assertRaises(ValueError):stage.stage_file(self.src,self.out,stage.HEADERS['raw_sample'])
        self.assertEqual(self.out.read_text(),'keep this')

    def test_wrong_width_fails_after_valid_row_without_partial_output(self):
        self.src.write_text(self.header+'1,1494000000,2,slot_a,1,0\n1,2\n')
        with self.assertRaises(ValueError):stage.stage_file(self.src,self.out,stage.HEADERS['raw_sample'])
        self.assertFalse(self.out.exists())

    def test_multiline_fields_are_not_silently_renumbered(self):
        self.src.write_text(self.header+'1,1494000000,2,"slot\nother",1,0\n')
        with self.assertRaises(ValueError):stage.stage_file(self.src,self.out,stage.HEADERS['raw_sample'])
        self.assertFalse(self.out.exists())

    def test_empty_attribute_preserved(self):
        self.src.write_text(self.header+'1,1494000000,2,,1,0\n')
        stage.stage_file(self.src,self.out,stage.HEADERS['raw_sample'])
        self.assertIn('\t\t',self.out.read_text())

class PublicationGuard(unittest.TestCase):
    def test_marked_technical_input_cannot_enter_business_namespace(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/'manifest.json').write_text(json.dumps({'kind':'full_csv_staging','sampled':False,'technical_validation':True,'files':[]}))
            result=subprocess.run([sys.executable,str(ROOT/'scripts/platform/run_batch.py'),'--staged',str(path),'--batch','safety_test','--namespace','taobao'],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('人工技术测试数据禁止',result.stderr)

class Cluster(unittest.TestCase):
    def nodes(self):
        return [{'name':f'adw10{i}','address':f'192.0.2.{i}','yarn_memory_mb':1024} for i in range(1,4)]

    def test_configs_have_three_unique_roles_and_no_current_storage(self):
        with tempfile.TemporaryDirectory() as d:
            out=cluster.render({'nodes':self.nodes()},Path(d)/'configs')
            self.assertEqual(len(list(out.glob('*/role.json'))),3)
            for p in out.glob('*/*.xml'):
                ET.parse(p)
                self.assertNotIn('/opt/taobao/data/',p.read_text())
            self.assertIn('<value>3</value>',(out/'adw101/hdfs-site.xml').read_text())

    def test_placeholders_require_explicit_template_mode(self):
        nodes=self.nodes()
        for i,node in enumerate(nodes,1):node['address']=f'CHANGE_ME_NODE{i}'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):cluster.render({'nodes':nodes},Path(d)/'bad')
            out=cluster.render({'nodes':nodes},Path(d)/'templates',template=True)
            self.assertIn('CHANGE_ME_NODE1',(out/'adw101/hosts.fragment').read_text())
            self.assertIn('template_not_deployed',(out/'adw101/role.json').read_text())

    def test_duplicate_and_loopback_addresses_fail(self):
        for bad in ['127.0.0.1','192.0.2.1','CHANGE_ME_NODE2']:
            nodes=self.nodes();nodes[1]['address']=bad
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError):cluster.render({'nodes':nodes},Path(d)/'bad')
                self.assertFalse((Path(d)/'bad').exists())

if __name__ == '__main__':
    unittest.main()
