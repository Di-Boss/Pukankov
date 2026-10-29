"""Validate the publishable Wokwi project structure without external packages."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "wokwi"
PROJECTS = {
    "vending-machine": ("wokwi-arduino-mega", "sketch.ino"),
    "ticket-kiosk": ("board-esp32-devkit-c-v4", "sketch.ino"),
    "ticket-validator": ("board-pi-pico-w", "main.py"),
}


def check_projects():
    for name, (board, source) in PROJECTS.items():
        folder = ROOT / name
        diagram = json.loads((folder / "diagram.json").read_text(encoding="utf-8"))
        parts = diagram["parts"]
        ids = {part["id"] for part in parts}
        assert len(ids) == len(parts), f"{name}: duplicate component id"
        assert sum(part["type"] == board for part in parts) == 1, f"{name}: board"
        assert diagram["connections"], f"{name}: missing connections"
        for connection in diagram["connections"]:
            assert len(connection) == 4, f"{name}: malformed connection"
            for endpoint in connection[:2]:
                component, separator, pin = endpoint.partition(":")
                assert separator and pin, f"{name}: malformed endpoint"
                assert component in ids or component == "$serialMonitor", f"{name}: dangling {endpoint}"
        code = (folder / source).read_text(encoding="utf-8")
        assert not re.search(r"pk_device_[A-Za-z0-9_-]{30,}", code), f"{name}: embedded credential"
        assert (folder / "README.md").is_file(), f"{name}: missing instructions"
        if source.endswith(".ino"):
            assert (folder / "libraries.txt").read_text().strip(), f"{name}: missing libraries"
        else:
            compile(code, str(folder / source), "exec")
            assert 'DEFAULT_DEVICE_KEY = ""' in code, f"{name}: public key must be empty"
            assert "USE_SAVED_CONFIG = True" in code, f"{name}: runtime configuration disabled"
        print(f"OK {name}: {len(parts)} components, {len(diagram['connections'])} connections")


if __name__ == "__main__":
    check_projects()
