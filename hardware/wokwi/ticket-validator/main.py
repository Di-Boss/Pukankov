# PUKANKOV Pico W gate. MicroPython 1.28.0. No device key in the source.
# Serial: KEY <validator key> | URL <https base URL> | STATUS | HELP
# Keypad: six digits then #; * clears; D removes the last digit.
import sys
import time
import json
import os
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

API_URL = "https://foil-reoccur-tablet.ngrok-free.dev"
DEFAULT_DEVICE_KEY = ""
USE_SAVED_CONFIG = True
CONFIG_FILE = "gate.private.json"
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""
OPEN_MS = 5000
ERROR_MS = 2000
BLINK_MS = 500
DEBOUNCE_MS = 35
REQUEST_TIMEOUT = 30
MAX_RESPONSE = 4096


def ticks_ms():
    return time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.monotonic() * 1000)


def ticks_diff(a, b):
    return time.ticks_diff(a, b) if hasattr(time, "ticks_diff") else a - b


def ticks_add(value, delta):
    return time.ticks_add(value, delta) if hasattr(time, "ticks_add") else value + delta


class GateController:
    """Pure state machine; outputs are red, green, servo angle, buzzer Hz."""
    def __init__(self, now=0):
        self.state = "idle"
        self.started = now
        self.code = ""
        self.generation = 0
        self.sound_started = now
        self.sound_ms = 0
        self.sound_hz = 0

    def beep(self, now, hz=1400, duration=35):
        self.sound_started, self.sound_hz, self.sound_ms = now, hz, duration

    def key(self, key, now):
        if self.state != "idle":
            return None
        if key in "0123456789" and len(key) == 1:
            if len(self.code) < 6:
                self.code += key
                self.beep(now)
            else:
                self.beep(now, 500, 80)
        elif key == "*":
            self.code = ""
            self.beep(now, 1000, 60)
        elif key == "D":
            self.code = self.code[:-1]
            self.beep(now, 1000, 40)
        elif key == "#":
            if len(self.code) != 6:
                self.deny(now)
                return None
            submitted = self.code
            self.code = ""
            self.generation += 1
            self.state, self.started = "checking", now
            self.beep(now, 1600, 50)
            return submitted, self.generation
        return None

    def deny(self, now):
        self.code = ""
        self.state, self.started = "error", now

    def result(self, allowed, generation, now):
        if self.state != "checking" or generation != self.generation:
            return False
        self.state = "open" if allowed is True else "error"
        self.started = now
        return True

    def outputs(self, now):
        elapsed = ticks_diff(now, self.started)
        limit = OPEN_MS if self.state == "open" else ERROR_MS
        if self.state in ("open", "error") and elapsed >= limit:
            was_open = self.state == "open"
            self.state, self.started = "idle", ticks_add(self.started, limit)
            elapsed = ticks_diff(now, self.started)
            if was_open:
                self.beep(now, 900, 80)
        if self.state == "open":
            green = elapsed >= 1000 or elapsed % 500 < 250
            tone = 2200 if elapsed < 130 else 2800 if 500 <= elapsed < 630 else 0
            return 0, int(green), 90, tone
        if self.state == "error":
            return 1, 0, 0, 400 if elapsed < 300 else 0
        tone = self.sound_hz if ticks_diff(now, self.sound_started) < self.sound_ms else 0
        period = 150 if self.state == "checking" else BLINK_MS
        return int((elapsed // period) % 2 == 0), 0, 0, tone


class KeyDebouncer:
    def __init__(self):
        self.candidate = None
        self.stable = None
        self.changed = 0

    def update(self, raw, now):
        if raw != self.candidate:
            self.candidate, self.changed = raw, now
        if raw != self.stable and ticks_diff(now, self.changed) >= DEBOUNCE_MS:
            self.stable = raw
            if raw and len(raw) == 1:
                return raw
        return None


def make_hardware():
    from machine import Pin, PWM
    import rp2

    @rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
    def square_wave():
        set(pins, 1) [31]
        set(pins, 0) [31]

    class Hardware:
        def __init__(self):
            self.red = Pin(12, Pin.OUT, value=1)
            self.green = Pin(13, Pin.OUT, value=0)
            self.servo = PWM(Pin(15), freq=50)
            self.servo.duty_ns(500000)
            self.buzzer = Pin(14, Pin.OUT, value=0)
            # Allocate sound PIO on first use, after WiFi has started.
            self.tone = None
            self.rows = [Pin(n, Pin.IN) for n in (2, 3, 4, 5)]
            self.columns = [Pin(n, Pin.IN, Pin.PULL_UP) for n in (6, 7, 8, 9)]
            self.last = None

        def apply(self, outputs):
            if outputs == self.last:
                return
            red, green, angle, hz = outputs
            self.red.value(red)
            self.green.value(green)
            if self.last is None or angle != self.last[2]:
                self.servo.duty_ns(500000 + angle * 2000000 // 180)
            if self.last is None or hz != self.last[3]:
                if self.tone:
                    self.tone.active(0)
                if hz:
                    if self.tone is None:
                        self.tone = rp2.StateMachine(7, square_wave, freq=hz * 64, set_base=self.buzzer)
                    else:
                        self.tone.init(square_wave, freq=hz * 64, set_base=self.buzzer)
                    self.tone.active(1)
                else:
                    self.buzzer.init(Pin.OUT, value=0)
            self.last = outputs

        def scan(self):
            keys = (("1", "2", "3", "A"), ("4", "5", "6", "B"),
                    ("7", "8", "9", "C"), ("*", "0", "#", "D"))
            pressed = []
            for row_index, row in enumerate(self.rows):
                row.init(Pin.OUT, value=0)
                time.sleep_us(5)
                for column_index, column in enumerate(self.columns):
                    if column.value() == 0:
                        pressed.append(keys[row_index][column_index])
                row.init(Pin.IN)  # No opposing output levels when keys are held.
            return pressed[0] if len(pressed) == 1 else "MULTI" if pressed else None

        def close(self):
            self.apply((1, 0, 0, 0))

    return Hardware()


def normalize_url(value):
    value = value.strip().rstrip("/")
    if not value.startswith("https://"):
        raise ValueError("Use an HTTPS base URL")
    host = value[8:].lower()
    if not host or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-." for c in host) or "." not in host:
        raise ValueError("Use a hostname without an API path or port")
    return "https://" + host.lower()


def load_config():
    config = {"api_url": API_URL, "device_key": DEFAULT_DEVICE_KEY}
    if not USE_SAVED_CONFIG:
        return config
    try:
        with open(CONFIG_FILE) as source:
            saved = json.load(source)
        config["api_url"] = normalize_url(saved.get("api_url", API_URL))
        key = saved.get("device_key", "")
        if isinstance(key, str) and key.startswith("pk_device_") and not any(c.isspace() for c in key):
            config["device_key"] = key
    except (OSError, ValueError, TypeError):
        pass
    return config


def save_config(config):
    with open(CONFIG_FILE + ".tmp", "w") as target:
        json.dump(config, target)
    os.rename(CONFIG_FILE + ".tmp", CONFIG_FILE)


def tls_context():
    # MicroPython 1.28 exposes cipher control in tls; the ssl compatibility
    # wrapper does not forward get_ciphers/set_ciphers.
    try:
        import tls as ssl
    except ImportError:
        import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Certificate checks disabled by request for this Wokwi prototype.
    context.verify_mode = ssl.CERT_NONE
    print("TLS_CERT_CHECK: disabled")
    print("TLS_CIPHERS: default")
    return context


async def read_response(reader):
    line = await reader.readline()
    fields = line.split()
    if len(fields) < 2 or not fields[0].startswith(b"HTTP/"):
        raise ValueError("Invalid HTTP response")
    status = int(fields[1])
    headers = {}
    total = len(line)
    while True:
        line = await reader.readline()
        total += len(line)
        if total > 8192 or not line:
            raise ValueError("Invalid HTTP headers")
        if line in (b"\r\n", b"\n"):
            break
        name, value = line.split(b":", 1)
        headers[name.lower()] = value.strip().lower()
    body = bytearray()
    if b"chunked" in headers.get(b"transfer-encoding", b""):
        while True:
            length = int((await reader.readline()).split(b";", 1)[0].strip(), 16)
            if not length:
                break
            if len(body) + length > MAX_RESPONSE:
                raise ValueError("Response too large")
            body.extend(await reader.readexactly(length))
            if await reader.readexactly(2) != b"\r\n":
                raise ValueError("Invalid chunk ending")
    elif b"content-length" in headers:
        length = int(headers[b"content-length"])
        if length < 0 or length > MAX_RESPONSE:
            raise ValueError("Response too large")
        body.extend(await reader.readexactly(length))
    else:
        while True:
            chunk = await reader.read(512)
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_RESPONSE:
                raise ValueError("Response too large")
    return status, json.loads(bytes(body).decode())


async def validate_code(config, code, context):
    host = normalize_url(config["api_url"])[8:]
    writer = None
    try:
        print("API_CONNECTING", host)
        reader, writer = await asyncio.open_connection(host, 443, ssl=context)
        body = json.dumps({"ticket_code": code}).encode()
        header = ("POST /api/validator/validate HTTP/1.1\r\nHost: " + host
                  + "\r\nAuthorization: Bearer " + config["device_key"]
                  + "\r\nContent-Type: application/json\r\nAccept: application/json"
                  + "\r\nngrok-skip-browser-warning: 1\r\nUser-Agent: Pukankov-Pico-Gate/1.0"
                  + "\r\nConnection: close\r\nContent-Length: " + str(len(body)) + "\r\n\r\n")
        writer.write(header.encode() + body)
        await writer.drain()
        print("API_REQUEST_SENT")
        status, result = await read_response(reader)
        print("VALIDATOR_HTTP", status)
        if status != 200 or not isinstance(result, dict):
            raise ValueError("API refused validation; HTTP " + str(status))
        if result.get("valid") is True and result.get("ticket_code") != code:
            raise ValueError("API returned a different ticket")
        return result
    finally:
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


async def main(wlan, hardware, gate):
    import select
    debounce = KeyDebouncer()
    config = load_config()
    ready = {"tls": False}
    context = None
    serial = ""
    print("PUKANKOV PICO GATE START")
    print("Firmware: pico-gate-3; digits + #; * clear; D backspace")
    print("Commands: KEY <validator key> | URL <https URL> | STATUS | HELP")
    if not config["device_key"]:
        print("CONFIG_REQUIRED: send KEY <validator key>")

    async def connection_manager():
        nonlocal context
        while True:
            if gate.state == "idle" and not gate.code:
                if not wlan.isconnected():
                    ready["tls"] = False
                    print("WIFI_CONNECTING")
                    try:
                        if wlan.status() not in (1, 2):
                            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
                        start = ticks_ms()
                        while not wlan.isconnected() and ticks_diff(ticks_ms(), start) < 20000:
                            # Native sleeps pump the CYW43 driver in Wokwi.
                            # This branch only runs with an idle, closed gate.
                            hardware.apply(gate.outputs(ticks_ms()))
                            time.sleep_ms(50)
                    except OSError:
                        pass
                    if wlan.isconnected():
                        print("WIFI_READY", wlan.ifconfig()[0])
                    else:
                        print("WIFI_RETRY", wlan.status())
                        wlan.disconnect()
                if wlan.isconnected() and not ready["tls"]:
                    try:
                        context = tls_context()
                        ready["tls"] = True
                        print("NETWORK_READY")
                    except Exception as error:
                        print("TLS_SETUP_ERROR", type(error).__name__, str(error))
            await asyncio.sleep_ms(5000)

    async def check(code, generation):
        try:
            if not config["device_key"]:
                raise ValueError("Send KEY with the validator credential first")
            if not wlan.isconnected() or not ready["tls"]:
                raise ValueError("WiFi or TLS not ready")
            result = await asyncio.wait_for(validate_code(config, code, context), REQUEST_TIMEOUT)
            allowed = result.get("valid") is True
            print("ACCESS_GRANTED" if allowed else "ACCESS_DENIED", result.get("reason", ""))
            gate.result(allowed, generation, ticks_ms())
        except Exception as error:
            # No automatic repeat: the server may have consumed the ticket.
            print("ACCESS_DENIED: network/configuration error", type(error).__name__, str(error))
            gate.result(False, generation, ticks_ms())
        hardware.apply(gate.outputs(ticks_ms()))

    manager = asyncio.create_task(connection_manager())
    try:
        while True:
            now = ticks_ms()
            hardware.apply(gate.outputs(now))
            key = debounce.update(hardware.scan(), now)
            if key and gate.state == "idle":
                submitted = gate.key(key, now)
                if submitted:
                    print("CHECKING_TICKET")
                    asyncio.create_task(check(submitted[0], submitted[1]))
                elif key == "#":
                    print("ACCESS_DENIED invalid_length: enter six digits")
                else:
                    print("DIGITS", len(gate.code))
            # Avoid persistent USB polling during WiFi setup and TLS in Wokwi.
            while gate.state == "idle" and ready["tls"] and wlan.isconnected() and select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if not char:
                    break
                if char == "\r":
                    continue
                if char == "\n":
                    command, serial = serial.strip(), ""
                    if command == "STATUS":
                        print("API_BASE", config["api_url"], "KEY_CONFIGURED", bool(config["device_key"]),
                              "WIFI", wlan.isconnected(), "TLS", ready["tls"], "GATE", gate.state)
                    elif gate.state != "idle":
                        print("Wait until the gate returns to idle before changing configuration")
                    elif command.startswith("KEY "):
                        token = command[4:].strip()
                        if token.startswith("pk_device_") and len(token) >= 20 and not any(c.isspace() for c in token):
                            config["device_key"] = token
                            save_config(config)
                            print("Validator key saved (not echoed)")
                        else:
                            print("Invalid device key")
                    elif command.startswith("URL "):
                        try:
                            config["api_url"] = normalize_url(command[4:])
                            save_config(config)
                            print("API URL saved")
                        except ValueError as error:
                            print(str(error))
                    elif command:
                        print("KEY <validator key> | URL <https URL> | STATUS | HELP")
                elif len(serial) < 512:
                    serial += char
                else:
                    serial = ""
            # The Pico W simulator services WiFi during the native sleep hook.
            # Keep this to 1 ms; the rest of the 10 ms cycle stays asynchronous.
            time.sleep_ms(1)
            await asyncio.sleep_ms(9)
    finally:
        manager.cancel()
        hardware.close()


def run():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    hardware = None
    try:
        # Complete initial DHCP in the native VM loop before starting asyncio.
        # USB polling and sound PIO are deliberately absent during this phase.
        print("WIFI_BOOT: connecting to", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        start = ticks_ms()
        while not wlan.isconnected() and ticks_diff(ticks_ms(), start) < 20000:
            time.sleep_ms(100)
        if wlan.isconnected():
            print("WIFI_READY", wlan.ifconfig()[0])
        hardware = make_hardware()
        gate = GateController(ticks_ms())
        asyncio.run(main(wlan, hardware, gate))
    finally:
        if hardware is not None:
            hardware.close()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("GATE_STOPPED_CLOSED")
