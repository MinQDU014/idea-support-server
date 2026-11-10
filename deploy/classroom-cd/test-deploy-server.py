import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('receiver', Path(__file__).with_name('deploy-server.py'))
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)

class DeploymentSafety(unittest.TestCase):
    def test_image_scope_and_shell_payloads(self):
        good = 'docker.minq.live/team1/idea-support-server:dev-'+'a'*40
        self.assertEqual(receiver.validate_image('team1',good),good)
        for image in [good.replace('/team1/','/team2/'),good+';id',good.replace(':dev-'+ 'a'*40,':latest'),
                      'alpine:latest','docker.minq.live/team1/other@sha256:'+'a'*64]:
            with self.assertRaises(ValueError):
                receiver.validate_image('team1', image)
        with self.assertRaises(ValueError):
            receiver.validate_image('team9',good)

    def test_failed_health_restores_only_selected_team(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for team in ['team1','team2']:
                (root/team).mkdir()
                (root/team/'compose.json').write_text(json.dumps({'services':{'app':{'image':'previous','env_file':['.env.dev']}}}))
            untouched = (root/'team2/compose.json').read_bytes()
            digest = 'docker.minq.live/team1/idea-support-server@sha256:'+'a'*64
            with patch.object(receiver,'ROOT',root), patch.object(receiver,'command',side_effect=['',json.dumps([digest])]), \
                 patch.object(receiver,'compose') as compose, patch.object(receiver,'health',side_effect=[False,True]):
                result = receiver.deploy('team1','docker.minq.live/team1/idea-support-server:dev-'+'b'*40,'b'*40)
            self.assertEqual(result['status'],'rolled_back')
            self.assertTrue(result['rollback_healthy'])
            self.assertEqual(compose.call_count,2)
            self.assertEqual(json.loads((root/'team1/compose.json').read_text())['services']['app']['image'],'previous')
            self.assertEqual((root/'team2/compose.json').read_bytes(),untouched)

if __name__ == '__main__':
    unittest.main()
