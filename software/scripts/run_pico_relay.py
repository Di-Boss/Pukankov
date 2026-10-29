"""Temporary Pico HTTPS relay and private preconfigured firmware generator."""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_private_firmware(url, output):
    if not re.fullmatch(r'https://[a-z0-9-]+\.trycloudflare\.com', url):
        raise ValueError('Expected a Cloudflare Quick Tunnel HTTPS URL')
    credentials = json.loads((ROOT / '.local/pico-validator.private.json').read_text(encoding='utf-8'))
    source_path = ROOT.parent / 'hardware/wokwi/ticket-validator/main.py'
    source = source_path.read_text(encoding='utf-8')
    source = re.sub(r'^API_URL = .*$', 'API_URL = ' + json.dumps(url), source, count=1, flags=re.M)
    source = source.replace('DEFAULT_DEVICE_KEY = ""', 'DEFAULT_DEVICE_KEY = ' + json.dumps(credentials['device_key']))
    source = source.replace('USE_SAVED_CONFIG = True', 'USE_SAVED_CONFIG = False')
    source = source.replace('No device key in the source.', 'PRIVATE copy: contains the validator device key.')
    compile(source, 'pico-ready.private.py', 'exec')
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding='utf-8', newline='\n')
    (ROOT / '.local/pico-relay.private.json').write_text(
        json.dumps({'api_url': url, 'output': str(output)}, indent=2), encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloudflared', default='cloudflared')
    parser.add_argument('--port', type=int, default=8002)
    parser.add_argument('--output', type=Path, default=ROOT / '.local/pico-ready.private.py')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Invalid port')
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/api/v1/health' % args.port, timeout=4) as response:
            if json.load(response).get('service') != 'pukankov-device-api':
                raise ValueError('The local port is not the PUKANKOV device API')
    except Exception as error:
        raise SystemExit('Start the device API first. ' + str(error))
    process = subprocess.Popen(
        [args.cloudflared, 'tunnel', '--url', 'http://127.0.0.1:%d' % args.port,
         '--no-autoupdate', '--protocol', 'http2'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding='utf-8', errors='replace',
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        ready = False
        for line in process.stdout:
            if not ready:
                match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
                if match:
                    output = write_private_firmware(match.group(), args.output)
                    ready = True
                    print('PICO_API_URL=' + match.group(), flush=True)
                    print('READY_FILE=' + str(output), flush=True)
                    print('Replace main.py with this private file. Keep this window open.', flush=True)
            if 'ERR' in line:
                print(line.strip(), flush=True)
        if process.wait() != 0:
            raise SystemExit('Relay stopped. Restart it and copy the regenerated main.py.')
    except KeyboardInterrupt:
        pass
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    main()
