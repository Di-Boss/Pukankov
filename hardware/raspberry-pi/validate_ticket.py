"""Minimal Pi terminal client; keypad input can replace input()."""

import json
import os
import urllib.error
import urllib.request


def main():
    base = os.environ["PUKANKOV_URL"].rstrip("/")
    key = os.environ["PUKANKOV_DEVICE_KEY"]
    showtime_id = int(os.environ["PUKANKOV_SHOWTIME_ID"])
    while True:
        code = input("6 цифри (Enter за край): ").strip()
        if not code:
            break
        if len(code) != 6 or not code.isascii() or not code.isdigit():
            print("Въведи точно 6 цифри.")
            continue
        request = urllib.request.Request(
            base + "/api/validator/validate",
            data=json.dumps({"ticket_code": code, "showtime_id": showtime_id}).encode(),
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                result = json.load(response)
            # Drive the green LED/relay only after a verified positive reply.
            print(
                "ДОСТЪП РАЗРЕШЕН" if result.get("valid") is True else "ДОСТЪП ОТКАЗАН"
            )
            print(result.get("message", ""))
        except (urllib.error.URLError, TimeoutError, ValueError):
            print("ДОСТЪП ОТКАЗАН — няма потвърждение от сървъра.")


if __name__ == "__main__":
    main()
