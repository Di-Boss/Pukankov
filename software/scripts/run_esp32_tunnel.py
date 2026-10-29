"""Expose the running device API through an alternative HTTPS SSH tunnel."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8002)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be 1-65535.')
    local = f'http://127.0.0.1:{args.port}'
    try:
        with urllib.request.urlopen(local + '/api/v1/health', timeout=5) as response:
            health = json.load(response)
        if health.get('service') != 'pukankov-device-api':
            raise ValueError('Port is not the PUKANKOV device API.')
    except Exception as exc:
        parser.exit(1, f'Device API is unavailable: {exc}\nStart START-PUBLIC-API.cmd first.\n')
    ssh = shutil.which('ssh')
    if not ssh:
        parser.exit(1, 'OpenSSH client is required.\n')
    state_dir = ROOT / '.local'
    state_dir.mkdir(exist_ok=True)
    command = [
        ssh, '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new',
        '-o', f'UserKnownHostsFile={state_dir / "tunnel_known_hosts"}',
        '-o', 'ExitOnForwardFailure=yes', '-o', 'ConnectTimeout=15',
        '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
        '-R', f'80:127.0.0.1:{args.port}', 'nokey@localhost.run', '--', '--output', 'json',
    ]
    print('Starting alternative HTTPS tunnel. Keep this window open.', flush=True)
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    last_url = None
    state_file = state_dir / 'esp32-fallback-tunnel.json'
    try:
        for line in child.stdout:
            match = re.search(r'\b[a-z0-9-]+\.lhr\.life\b', line)
            if not match:
                if line.startswith('ssh:') or 'Permission denied (' in line:
                    print(line.strip(), flush=True)
                continue
            url = 'https://' + match.group(0)
            if url == last_url:
                continue
            last_url = url
            state = {'url': url, 'docs': url + '/api/docs', 'local_origin': local,
                     'provider': 'localhost.run', 'started_at': datetime.now(timezone.utc).isoformat()}
            state_file.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
            credentials = state_dir / 'esp32.private.json'
            if credentials.exists():
                config = json.loads(credentials.read_text(encoding='utf-8'))
                if config.get('url_mode') != 'stable':
                    config.update(base_url=url, docs_url=url + '/api/docs')
                    temporary = credentials.with_suffix('.tmp')
                    temporary.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
                    temporary.replace(credentials)
            print(f'ESP32_API_URL={url}\nSend this line in Wokwi Serial Monitor:\nURL {url}', flush=True)
        if child.wait() != 0:
            raise RuntimeError('SSH tunnel disconnected; restart this launcher for a new URL.')
    except KeyboardInterrupt:
        print('\nStopping alternative tunnel.', flush=True)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        if last_url and state_file.exists():
            state = json.loads(state_file.read_text(encoding='utf-8'))
            state['stopped_at'] = datetime.now(timezone.utc).isoformat()
            state_file.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
