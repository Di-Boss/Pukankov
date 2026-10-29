"""Run the isolated device API and an optional Cloudflare Quick Tunnel.

Uses the same database as the website. RFID is handled locally by the terminal; the API receives only the outcome.
Ctrl+C shuts down the child processes; no Windows service or firewall changes.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-path",
        type=Path,
        help="Existing website SQLite database. Omit to use backend/.env or DATABASE_URL.",
    )
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument(
        "--cloudflared", help="Path to the official cloudflared executable"
    )
    parser.add_argument("--local-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be 1–65535.")
    env = dict(os.environ)
    if args.database_path:
        database = args.database_path.resolve()
        if not database.is_file():
            parser.error(
                "Database does not exist. Start the website once or pass its existing database path."
            )
        env["DATABASE_URL"] = "sqlite:///" + database.as_posix()
    binary = args.cloudflared or shutil.which("cloudflared")
    if not args.local_only and (not binary or not Path(binary).is_file()):
        parser.error(
            "Install official cloudflared or pass --cloudflared PATH; use --local-only without a tunnel."
        )
    local = f"http://127.0.0.1:{args.port}"
    backend = ROOT / "backend"
    # Do not attach a tunnel to an unrelated service already listening on this port.
    import socket

    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            parser.error(
                f"Port {args.port} is already in use. Stop that service or choose --port."
            )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend,
        env=env,
        check=True,
    )
    subprocess.run([sys.executable, "-m", "app.seed"], cwd=backend, env=env, check=True)
    server = tunnel = None
    state_dir = ROOT / ".local"
    state_dir.mkdir(exist_ok=True)
    state_file = state_dir / "public-api.json"
    try:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.public_gateway:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "--no-access-log",
            ],
            cwd=backend,
            env=env,
        )
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("API server exited during startup.")
            try:
                with urllib.request.urlopen(
                    local + "/api/v1/health", timeout=1
                ) as response:
                    healthy = json.load(response)
                if healthy.get("service") == "pukankov-device-api":
                    break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.2)
        else:
            raise RuntimeError("API server did not become healthy.")
        print(f"Local API: {local}/api/docs", flush=True)
        print(
            "Terminal payment: ESP32 sends payment_success; no card UID or balance.",
            flush=True,
        )
        if args.local_only:
            server.wait()
            return
        tunnel = subprocess.Popen(
            [
                str(binary),
                "tunnel",
                "--no-autoupdate",
                "--protocol",
                "http2",
                "--url",
                local,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        for line in tunnel.stdout:
            print(line, end="", flush=True)
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                url = match.group(0)
                state_file.write_text(
                    json.dumps(
                        {
                            "url": url,
                            "docs": url + "/api/docs",
                            "local_origin": local,
                            "started_at": datetime.now(timezone.utc).isoformat(),
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                credentials = state_dir / "esp32.private.json"
                if credentials.exists():
                    config = json.loads(credentials.read_text(encoding="utf-8"))
                    if config.get("url_mode") != "stable":
                        config.update({"base_url": url, "docs_url": url + "/api/docs"})
                        credentials.write_text(
                            json.dumps(config, indent=2) + "\n", encoding="utf-8"
                        )
                print(
                    f"PUBLIC_API_URL={url}\nKeep this terminal open. Ctrl+C stops API and tunnel.",
                    flush=True,
                )
            if server.poll() is not None:
                raise RuntimeError("API server exited; stopping the tunnel.")
        if tunnel.wait() != 0:
            raise RuntimeError(
                "Cloudflare tunnel exited. Read the connection error above."
            )
    except KeyboardInterrupt:
        print("\nStopping public API and tunnel.", flush=True)
    finally:
        stop(tunnel)
        stop(server)
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            state["stopped_at"] = datetime.now(timezone.utc).isoformat()
            state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
