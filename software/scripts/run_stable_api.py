"""Run the device API behind an explicitly pinned ngrok HTTPS domain."""

import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
CONFIG = LOCAL / 'stable-api.private.json'


def domain_url(value):
    value = value.strip()
    if '://' not in value:
        value = 'https://' + value
    parsed = urllib.parse.urlsplit(value)
    suffixes = ('.ngrok-free.app', '.ngrok-free.dev', '.ngrok.app', '.ngrok.dev')
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.path not in ('', '/')
            or parsed.query or parsed.fragment
            or not re.fullmatch(r'[a-z0-9.-]+', host)
            or not host.endswith(suffixes)
            or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?', label)
                   for label in host.split('.'))):
        raise ValueError('Use the assigned HTTPS domain from https://dashboard.ngrok.com/domains')
    return 'https://' + host


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def configure():
    if not sys.stdin.isatty():
        raise RuntimeError('Run START-STABLE-API.cmd in your own terminal to enter the ngrok account settings.')
    print('Create a free account: https://dashboard.ngrok.com/signup')
    print('Assigned domain: https://dashboard.ngrok.com/domains')
    url = domain_url(input('Paste your assigned domain: '))
    print('Authtoken: https://dashboard.ngrok.com/get-started/your-authtoken')
    token = getpass.getpass('Paste ngrok authtoken (hidden): ').strip()
    if len(token) < 20 or any(c.isspace() for c in token):
        raise ValueError('The ngrok authtoken is missing or invalid.')
    save_json(CONFIG, {'url': url, 'authtoken': token})
    print('Settings saved locally. The token is not printed or added to Git.')


def read_health(url, timeout=3):
    request = urllib.request.Request(url + '/api/v1/health', headers={
        'ngrok-skip-browser-warning': '1', 'User-Agent': 'Pukankov-API-Launcher/1.0',
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    if result.get('service') != 'pukankov-device-api':
        raise RuntimeError('The address does not serve the PUKANKOV device API.')
    return result


def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def find_ngrok(explicit=None):
    # Microsoft Store execution aliases may run even when Path.is_file()/stat
    # cannot resolve their reparse point. Verify by executing the version command.
    candidates = [explicit] if explicit else [
        shutil.which('ngrok'),
        str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/WindowsApps/ngrok.exe'),
        'ngrok.exe',
    ]
    for candidate in dict.fromkeys(c for c in candidates if c):
        try:
            result = subprocess.run([str(candidate), 'version'], capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip().lower().startswith('ngrok'):
            return str(candidate)
    raise RuntimeError('ngrok could not be started. Open a new Windows terminal after installing '
                       'the Store app, or pass --ngrok C:/path/to/ngrok.exe.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', action='store_true', help='Replace the saved domain and token interactively')
    parser.add_argument('--ngrok', help='Path to ngrok executable; otherwise use PATH')
    parser.add_argument('--database-path', type=Path, help='Existing website database; otherwise use backend/.env')
    parser.add_argument('--port', type=int, default=8002)
    parser.add_argument('--check', action='store_true', help='Validate the saved settings without starting a tunnel')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be 1-65535.')
    binary = find_ngrok(args.ngrok)
    if args.setup or not CONFIG.exists():
        configure()
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    url = domain_url(config['url'])
    token = config.get('authtoken', '')
    if len(token) < 20 or any(c.isspace() for c in token):
        raise RuntimeError('Saved authtoken is invalid; run again with --setup.')
    # JSON string literals are valid YAML scalars. No token is passed on the command line.
    agent_config = LOCAL / 'ngrok.private.yml'
    agent_config.write_text(
        'version: "3"\nagent:\n  authtoken: ' + json.dumps(token)
        + '\n  web_addr: false\n  console_ui: false\n  remote_management: false\n',
        encoding='utf-8',
    )
    if args.check:
        result = subprocess.run([binary, 'config', 'check', '--config', str(agent_config)],
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode:
            raise RuntimeError('ngrok rejected the generated configuration.')
        print('Configuration valid. Pinned URL: ' + url)
        return

    server = agent = None
    state_file = LOCAL / 'stable-api-state.json'
    log_file = LOCAL / 'ngrok.private.log'
    local = f'http://127.0.0.1:{args.port}'
    try:
        try:
            read_health(local)
        except urllib.error.URLError as exc:
            if not isinstance(exc.reason, ConnectionRefusedError):
                raise RuntimeError('The local API port is not responding normally; no replacement was started.') from exc
            command = [sys.executable, '-u', str(ROOT / 'scripts/run_public_api.py'),
                       '--local-only', '--port', str(args.port)]
            if args.database_path:
                command.extend(['--database-path', str(args.database_path.resolve())])
            server = subprocess.Popen(command)
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError('Local API startup failed.')
                try:
                    read_health(local, timeout=1)
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.2)
            else:
                raise RuntimeError('Local API did not become ready.')
        # No random URL or rotating-tunnel fallback is permitted here.
        with log_file.open('w', encoding='utf-8') as log:
            agent = subprocess.Popen(
                [binary, 'http', local, '--url', url, '--config', str(agent_config),
                 '--inspect=false', '--log', 'stdout', '--log-format', 'json'],
                stdout=log, stderr=subprocess.STDOUT,
            )
            ready = False
            for _ in range(30):
                if agent.poll() is not None:
                    detail = log_file.read_text(encoding='utf-8', errors='replace')[-2000:]
                    raise RuntimeError('ngrok could not start. ' + detail.replace(token, '[hidden]'))
                try:
                    read_health(url, timeout=2)
                    ready = True
                    break
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                    time.sleep(1)
            if not ready:
                raise RuntimeError('Pinned public URL did not become ready; check the account and assigned domain.')
            state = {'url': url, 'docs': url + '/api/docs', 'local_origin': local,
                     'provider': 'ngrok', 'url_mode': 'stable', 'pid': os.getpid(),
                     'started_at': datetime.now(timezone.utc).isoformat()}
            save_json(state_file, state)
            credentials = LOCAL / 'esp32.private.json'
            if credentials.exists():
                device = json.loads(credentials.read_text(encoding='utf-8'))
                device.update(base_url=url, docs_url=url + '/api/docs', url_mode='stable')
                save_json(credentials, device)
            print(f'STABLE_API_URL={url}\nSend once in ESP32 Serial Monitor:\nURL {url}', flush=True)
            print('Keep this window, computer and internet connection running. Ctrl+C stops the tunnel.', flush=True)
            while agent.poll() is None:
                if server and server.poll() is not None:
                    raise RuntimeError('Local API stopped; closing the public tunnel.')
                time.sleep(1)
            raise RuntimeError('ngrok stopped; run the same launcher again to use the same URL.')
    except KeyboardInterrupt:
        print('\nStopping stable API tunnel.', flush=True)
    finally:
        stop(agent)
        stop(server)  # Reused API processes belong to their original launcher.
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding='utf-8'))
            if state.get('pid') == os.getpid():
                state['stopped_at'] = datetime.now(timezone.utc).isoformat()
                save_json(state_file, state)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
