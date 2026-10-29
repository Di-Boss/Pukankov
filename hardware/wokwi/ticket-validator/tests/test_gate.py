import asyncio
import importlib.util
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

spec = importlib.util.spec_from_file_location('pico_gate', Path(__file__).parents[1] / 'main.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def submit(controller, start=0):
    for i, digit in enumerate('123456'):
        controller.key(digit, start + i)
    return controller.key('#', start + 10)[1]


class GateTests(unittest.TestCase):
    def test_preconfigured_copy_uses_current_url_instead_of_old_flash_settings(self):
        with patch.object(gate, 'USE_SAVED_CONFIG', False), \
             patch.object(gate, 'API_URL', 'https://relay.example.com'), \
             patch.object(gate, 'DEFAULT_DEVICE_KEY', 'pk_device_test'), \
             patch('builtins.open', side_effect=AssertionError('Old flash config must not override firmware')):
            self.assertEqual(gate.load_config(), {
                'api_url': 'https://relay.example.com', 'device_key': 'pk_device_test'})

    def test_idle_red_blinks_and_gate_remains_closed(self):
        controller = gate.GateController(0)
        for now, red in ((0, 1), (499, 1), (500, 0), (999, 0), (1000, 1)):
            self.assertEqual(controller.outputs(now)[:3], (red, 0, 0))

    def test_success_two_flashes_one_second_and_close_after_five(self):
        controller = gate.GateController(0)
        generation = submit(controller)
        self.assertTrue(controller.result(True, generation, 2000))
        for offset, green in ((0, 1), (249, 1), (250, 0), (499, 0), (500, 1),
                              (749, 1), (750, 0), (999, 0), (1000, 1), (4999, 1)):
            self.assertEqual(controller.outputs(2000 + offset)[:3], (0, green, 90))
        self.assertEqual(controller.outputs(7000)[:3], (1, 0, 0))
        self.assertEqual(controller.outputs(7500)[:3], (0, 0, 0))

    def test_denied_red_solid_exactly_two_seconds(self):
        controller = gate.GateController(0)
        generation = submit(controller)
        controller.result(False, generation, 100)
        self.assertEqual(controller.outputs(100), (1, 0, 0, 400))
        self.assertEqual(controller.outputs(400), (1, 0, 0, 0))
        self.assertEqual(controller.outputs(2099)[:3], (1, 0, 0))
        self.assertEqual(controller.outputs(2600)[:3], (0, 0, 0))

    def test_only_exact_boolean_true_opens(self):
        for response in (None, False, 1, 'true', {}, []):
            controller = gate.GateController()
            generation = submit(controller)
            controller.result(response, generation, 100)
            self.assertEqual(controller.outputs(100)[2], 0)

    def test_old_or_repeated_response_cannot_open_or_extend_gate(self):
        controller = gate.GateController()
        first = submit(controller)
        controller.result(False, first, 100)
        controller.outputs(2100)
        second = submit(controller, 2200)
        self.assertFalse(controller.result(True, first, 2300))
        self.assertEqual(controller.state, 'checking')
        controller.result(True, second, 2400)
        self.assertFalse(controller.result(True, second, 6000))
        self.assertEqual(controller.outputs(7400)[2], 0)

    def test_editing_length_and_locked_input(self):
        controller = gate.GateController()
        for digit in '1234567':
            controller.key(digit, 1)
        self.assertEqual(controller.code, '123456')
        controller.key('D', 2)
        self.assertEqual(controller.code, '12345')
        controller.key('*', 3)
        self.assertEqual(controller.code, '')
        self.assertIsNone(controller.key('#', 4))
        self.assertEqual(controller.state, 'error')
        controller.key('1', 5)
        self.assertEqual(controller.code, '')

    def test_debounce_hold_and_multi_key(self):
        debounce = gate.KeyDebouncer()
        self.assertIsNone(debounce.update('1', 0))
        self.assertIsNone(debounce.update('1', 34))
        self.assertEqual(debounce.update('1', 35), '1')
        self.assertIsNone(debounce.update('1', 1000))
        debounce.update(None, 1001)
        debounce.update(None, 1036)
        debounce.update('1', 1040)
        self.assertEqual(debounce.update('1', 1075), '1')
        debounce.update('MULTI', 1100)
        self.assertIsNone(debounce.update('MULTI', 1140))

    def test_url_rejects_paths_credentials_and_plaintext(self):
        self.assertEqual(gate.normalize_url(gate.API_URL + '/'), gate.API_URL)
        for url in ('http://example.com', 'https://user:pass@example.com', 'https://example.com/api'):
            with self.assertRaises(ValueError):
                gate.normalize_url(url)


class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def reader(self, response):
        reader = asyncio.StreamReader()
        reader.feed_data(response)
        reader.feed_eof()
        return reader

    async def test_fixed_and_chunked_json(self):
        body = b'{"valid":false,"reason":"invalid_code"}'
        fixed = b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body
        chunked = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n' + ('%x' % len(body)).encode() + b'\r\n' + body + b'\r\n0\r\n\r\n'
        for raw in (fixed, chunked):
            status, parsed = await gate.read_response(await self.reader(raw))
            self.assertEqual(status, 200)
            self.assertIs(parsed['valid'], False)

    async def test_oversized_response_rejected(self):
        with self.assertRaises(ValueError):
            await gate.read_response(await self.reader(b'HTTP/1.1 200 OK\r\nContent-Length: 99999\r\n\r\n'))

    async def test_validation_sends_code_only_and_checks_echo(self):
        body = json.dumps({'valid': True, 'ticket_code': '999999'}).encode()
        reader = await self.reader(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
        class Writer:
            def __init__(self):
                self.data = b''
                self.closed = False
            def write(self, data): self.data += data
            async def drain(self): pass
            def close(self): self.closed = True
            async def wait_closed(self): pass
        writer = Writer()
        config = {'api_url': gate.API_URL, 'device_key': 'pk_device_test'}
        with patch.object(gate.asyncio, 'open_connection', AsyncMock(return_value=(reader, writer))):
            with self.assertRaises(ValueError):
                await gate.validate_code(config, '123456', object())
        payload = json.loads(writer.data.split(b'\r\n\r\n')[1])
        self.assertEqual(payload, {'ticket_code': '123456'})
        self.assertTrue(writer.closed)


class TlsCompatibilityTests(unittest.TestCase):
    def test_wokwi_mode_uses_default_ciphers_without_certificate_checks(self):
        class Context:
            def __init__(self, protocol):
                self.verify_mode = None
            def load_verify_locations(self, ca):
                raise AssertionError("Certificate checks must remain disabled in Wokwi mode")
            def get_ciphers(self):
                return ['TLS-ECDHE-RSA-WITH-AES-128-GCM-SHA256',
                        'TLS-RSA-WITH-AES-128-GCM-SHA256']
            def set_ciphers(self, ciphers):
                raise AssertionError("Use default TLS ciphers for the relay")
        native = SimpleNamespace(SSLContext=Context, PROTOCOL_TLS_CLIENT=0, CERT_NONE=0)
        with patch.dict('sys.modules', {'tls': native}):
            context = gate.tls_context()
        self.assertEqual(context.verify_mode, 0)
        self.assertFalse(hasattr(context, "ciphers"))


if __name__ == '__main__':
    unittest.main()
