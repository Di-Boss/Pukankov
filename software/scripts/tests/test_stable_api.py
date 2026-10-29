import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

spec = importlib.util.spec_from_file_location('stable_api', Path(__file__).parents[1] / 'run_stable_api.py')
stable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stable)


class StableApiTests(unittest.TestCase):
    def test_store_alias_is_checked_by_execution_without_file_stat(self):
        alias = 'C:/Users/example/AppData/Local/Microsoft/WindowsApps/ngrok.exe'
        result = Mock(returncode=0, stdout='ngrok version 3.0.0\n')
        with patch.object(stable.subprocess, 'run', return_value=result) as run:
            self.assertEqual(stable.find_ngrok(alias), alias)
        self.assertEqual(run.call_args.args[0], [alias, 'version'])

    def test_unavailable_store_alias_produces_actionable_error(self):
        with patch.object(stable.subprocess, 'run', side_effect=PermissionError('alias unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'new Windows terminal'):
                stable.find_ngrok('unavailable.exe')

    def test_assigned_domain_normalization(self):
        for value in ('my-cinema.ngrok-free.app', 'https://my-cinema.ngrok-free.app/',
                      'https://MY-CINEMA.ngrok-free.app:443'):
            self.assertEqual(stable.domain_url(value), 'https://my-cinema.ngrok-free.app')

    def test_non_account_or_non_https_addresses_are_rejected(self):
        for value in ('http://cinema.ngrok-free.app', 'https://evil.example',
                      'https://cinema.ngrok-free.app.evil.example',
                      'https://user:password@cinema.ngrok-free.app',
                      'https://cinema.ngrok-free.app/api',
                      'https://cinema.ngrok-free.app?url=evil',
                      'https://cinema.ngrok-free.app:8443', 'https://.ngrok-free.app'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                stable.domain_url(value)

    def run_agent(self, folder, public_ready):
        url = 'https://pukankov-test.ngrok-free.app'
        token = 'example_test_token_not_a_real_account_123'
        settings = folder / 'stable-api.private.json'
        stable.save_json(settings, {'url': url, 'authtoken': token})
        credentials = folder / 'esp32.private.json'
        stable.save_json(credentials, {'base_url': 'https://old.example', 'device_key': 'device-test-key'})
        agent = Mock()
        agent.poll.side_effect = [None, 0, 0]
        health = {'service': 'pukankov-device-api'}
        replies = [health, health if public_ready else urllib.error.URLError('offline')]
        output = io.StringIO()
        with (patch.object(stable, 'LOCAL', folder), patch.object(stable, 'CONFIG', settings),
              patch.object(stable, 'find_ngrok', return_value=sys.executable),
              patch.object(stable, 'read_health', side_effect=replies),
              patch.object(stable.subprocess, 'Popen', return_value=agent) as launch,
              patch.object(stable.time, 'sleep'), patch.object(sys, 'argv', ['run_stable_api.py']),
              contextlib.redirect_stdout(output), self.assertRaises(RuntimeError)):
            stable.main()
        args = launch.call_args.args[0]
        self.assertEqual(args[args.index('--url') + 1], url)
        self.assertNotIn(token, repr(args))
        self.assertNotIn(token, output.getvalue())
        self.assertEqual(launch.call_count, 1)
        return json.loads(credentials.read_text()), folder / 'stable-api-state.json', url

    def test_success_pins_url_without_exposing_token_or_restarting_existing_api(self):
        with tempfile.TemporaryDirectory() as temporary:
            device, state, url = self.run_agent(Path(temporary), public_ready=True)
            self.assertEqual(device['base_url'], url)
            self.assertEqual(device['url_mode'], 'stable')
            self.assertEqual(device['device_key'], 'device-test-key')
            self.assertIn('stopped_at', json.loads(state.read_text()))

    def test_failed_tunnel_preserves_previous_device_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            device, state, _ = self.run_agent(Path(temporary), public_ready=False)
            self.assertEqual(device['base_url'], 'https://old.example')
            self.assertNotIn('url_mode', device)
            self.assertFalse(state.exists())


if __name__ == '__main__':
    unittest.main()
