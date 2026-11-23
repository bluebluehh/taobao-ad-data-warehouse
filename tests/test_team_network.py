"""Safety boundaries for the team commissioning helper; no live host changes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('team_network', Path(__file__).resolve().parents[1]/'scripts/platform/team_network.py')
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class TeamNetwork(unittest.TestCase):
    def setUp(self):
        self.plan = dict(adw101='100.80.0.1', adw102='100.80.0.2', adw103='100.80.0.3')

    def test_nat_duplicate_and_incomplete_plans_are_rejected(self):
        for plan in [{**self.plan,'adw102':'192.168.109.129'},
                     {**self.plan,'adw102':self.plan['adw101']},
                     {'adw101':'100.80.0.1'}]:
            with self.assertRaises(ValueError):
                team.validate_plan(plan)
        self.assertEqual(team.validate_plan(self.plan), self.plan)

    def test_hosts_preserves_other_names_and_replaces_conflicting_node_aliases(self):
        source = '127.0.0.1 localhost adw101 # keep\n127.0.1.1 adw102\n::1 localhost ip6-localhost\n192.0.2.1 unrelated\n'
        result = team.render_hosts(source, self.plan)
        self.assertIn('127.0.0.1\tlocalhost # keep', result)
        self.assertNotIn('127.0.1.1 adw102', result)
        self.assertIn('::1 localhost ip6-localhost', result)
        self.assertIn('192.0.2.1 unrelated', result)
        self.assertEqual(team.render_hosts(result, self.plan), result)

    def test_existing_or_symlinked_storage_cannot_be_formatted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            empty = root/'empty'
            empty.mkdir()
            team.require_empty(empty)
            (empty/'VERSION').write_text('existing cluster identity')
            with self.assertRaises(ValueError):
                team.require_empty(empty)
            target = root/'target'
            target.mkdir()
            link = root/'link'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                team.require_empty(link)

    def test_development_host_refused_before_any_network_or_file_mutation(self):
        with patch.object(team.socket, 'gethostname', return_value='taobao-template'):
            with self.assertRaisesRegex(ValueError, '旧开发机或模板'):
                team.live_node(self.plan)


if __name__ == '__main__':
    unittest.main()
