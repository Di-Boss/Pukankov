"""Print the public RSA certificate pin after normal CA and hostname verification."""

import argparse
import hashlib
import json
from pathlib import Path
import socket
import ssl
from urllib.parse import urlsplit

from run_stable_api import domain_url


def certificate_pin(url):
    url = domain_url(url)
    host = urlsplit(url).hostname
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers('AES128-GCM-SHA256')
    with socket.create_connection((host, 443), timeout=15) as tcp:
        with context.wrap_socket(tcp, server_hostname=host) as connection:
            certificate = connection.getpeercert()
            digest = hashlib.sha256(connection.getpeercert(binary_form=True)).hexdigest()
    return url, digest, certificate['notAfter']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Assigned ngrok HTTPS URL; otherwise use the saved device URL')
    args = parser.parse_args()
    url = args.url
    if not url:
        path = Path(__file__).resolve().parents[1] / '.local/esp32.private.json'
        url = json.loads(path.read_text(encoding='utf-8'))['base_url']
    url, digest, expiry = certificate_pin(url)
    print('CA and hostname verification passed.')
    print('Certificate valid until: ' + expiry)
    print('Send these lines in ESP32 Serial Monitor, in this order:')
    print('URL ' + url)
    print('PIN ' + digest)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit('Certificate verification failed: ' + str(exc))
