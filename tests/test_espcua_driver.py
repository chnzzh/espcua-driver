"""Standalone unit test suite for espcua-driver CLI, SDK, skill, and plugin manifest."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from espcua import cli
from espcua.adapter import ESPCUADriver
from espcua.client import ESPCUAClient, ESPCUAClientError
from espcua.keymap import (
    KEYBOARD_MOD_LALT,
    KEYBOARD_MOD_LCTRL,
    KEYBOARD_MOD_LGUI,
    KEYBOARD_MOD_LSHIFT,
    KEYBOARD_MOD_NONE,
    char_to_hid,
    name_to_hid,
    parse_hotkey,
)


MOCK_JPEG = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
    0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0x10, 0x0B, 0x0C, 0x0E, 0x0C, 0x0A, 0x10,
    0xFF, 0xD9,
])


class MockHTTPResponse:
    def __init__(self, body: bytes, headers: dict[str, str], status: int = 200):
        self._body = body
        self.headers = headers
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockKVMDispatcher:
    default_logs = [
        {"seq": 1, "ts_ms": 1500, "line": "I (1500) MAIN: ESP32-P4 IP-KVM starting..."},
        {"seq": 2, "ts_ms": 2041, "line": "I (2041) C790: TC358743 C790 HDMI bridge initialized successfully"},
        {"seq": 3, "ts_ms": 7187, "line": "I (7187) KVM_NET: Got IPv4 Address: 192.168.1.100"},
    ]
    requests_log = []
    power_state = "on"
    caps_lock = False
    logs = []
    dropped_logs = 0

    @classmethod
    def reset(cls):
        cls.requests_log = []
        cls.power_state = "on"
        cls.caps_lock = False
        cls.logs = [dict(entry) for entry in cls.default_logs]
        cls.dropped_logs = 0

    @classmethod
    def handle_request(cls, req: urllib.request.Request, timeout: float = 5.0):
        url = req.full_url
        method = req.get_method()
        path = req.selector
        if ":65530" in url:
            raise urllib.error.URLError("Connection refused")

        parsed_path = path.split("?")[0]
        body_data = req.data
        parsed_body = json.loads(body_data.decode("utf-8")) if body_data else {}
        cls.requests_log.append({"method": method, "path": path, "url": url, "body": parsed_body})

        if method == "GET":
            if parsed_path == "/api/v1/capture":
                headers = {
                    "Content-Type": "image/jpeg",
                    "Content-Length": str(len(MOCK_JPEG)),
                    "X-Video-Width": "1920",
                    "X-Video-Height": "1080",
                    "X-Frame-Timestamp": "123456789",
                }
                return MockHTTPResponse(MOCK_JPEG, headers, 200)
            if parsed_path == "/api/v1/video/status":
                resp = {
                    "ddc5v_present": True,
                    "tmds_clock_locked": True,
                    "video_sync_locked": True,
                    "is_hdmi": True,
                    "detected_resolution": {"width": 1920, "height": 1080, "interlaced": False},
                    "stream_stats": {"current_fps": 30.0, "frames_captured": 1000},
                }
                return MockHTTPResponse(json.dumps(resp).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/atx/status":
                resp = {
                    "connected": cls.power_state != "disconnected",
                    "power_state": cls.power_state,
                    "pwr_led": (cls.power_state == "on"),
                    "hdd_led": False,
                    "uptime_seconds": 120 if cls.power_state == "on" else 0,
                }
                return MockHTTPResponse(json.dumps(resp).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/system/status":
                resp = {
                    "status": "ok",
                    "device": "ESP32-P4-Nano-IPKVM",
                    "usb_mounted": True,
                    "free_heap": 250000,
                    "free_psram": 31457280,
                    "free_internal_heap": 250000,
                    "uptime_sec": 120,
                    "leds": {"num_lock": False, "caps_lock": cls.caps_lock, "scroll_lock": False},
                }
                return MockHTTPResponse(json.dumps(resp).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/logs":
                query = path.split("?", 1)[1] if "?" in path else ""
                params = urllib.parse.parse_qs(query)
                try:
                    since_seq = max(0, int(params.get("since", ["0"])[0]))
                except ValueError:
                    since_seq = 0
                filtered = [entry for entry in cls.logs if entry["seq"] > since_seq][:64]
                next_seq = filtered[-1]["seq"] if filtered else max(since_seq, cls.logs[-1]["seq"])
                resp = {"status": "ok", "next_seq": next_seq, "dropped": cls.dropped_logs, "logs": filtered}
                return MockHTTPResponse(json.dumps(resp).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/error/500":
                raise urllib.error.HTTPError(url, 500, "Internal Server Error", {}, io.BytesIO(b"Internal Server Error"))
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b"Not Found"))

        if method == "POST":
            if parsed_path == "/api/v1/hid/keyboard":
                if parsed_body.get("action") == "press" and str(parsed_body.get("key", "")).lower() in ("capslock", "caps_lock", "caps"):
                    cls.caps_lock = not cls.caps_lock
                resp = {
                    "status": "ok",
                    "usb_mounted": True,
                    "leds": {"num_lock": False, "caps_lock": cls.caps_lock, "scroll_lock": False},
                }
                return MockHTTPResponse(json.dumps(resp).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/hid/mouse":
                return MockHTTPResponse(json.dumps({"status": "ok", "usb_mounted": True}).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/atx/power":
                action = parsed_body.get("action", "click")
                if action in ("on", "click"):
                    cls.power_state = "on"
                elif action in ("off", "hold"):
                    cls.power_state = "off"
                resp = {"status": "ok", "connected": cls.power_state != "disconnected", "power_state": cls.power_state}
                return MockHTTPResponse(json.dumps(resp).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/atx/reset":
                return MockHTTPResponse(json.dumps({"status": "ok"}).encode("utf-8"), {"Content-Type": "application/json"}, 200)
            if parsed_path == "/api/v1/video/config":
                return MockHTTPResponse(
                    json.dumps({"status": "ok", "edid_profile": parsed_body.get("edid_profile", "720p")}).encode("utf-8"),
                    {"Content-Type": "application/json"},
                    200,
                )
            if parsed_path == "/api/v1/error/400":
                raise urllib.error.HTTPError(url, 400, "Bad Request", {}, io.BytesIO(json.dumps({"error": "Bad request"}).encode("utf-8")))
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b"Not Found"))

        raise urllib.error.HTTPError(url, 405, "Method Not Allowed", {}, io.BytesIO(b""))


class MockServerTestCase(unittest.TestCase):
    def setUp(self):
        MockKVMDispatcher.reset()
        self.patcher = patch("urllib.request.urlopen", side_effect=MockKVMDispatcher.handle_request)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()


class TestKeymap(unittest.TestCase):
    def test_ascii_special_keys_and_hotkeys(self):
        self.assertEqual(char_to_hid("a"), (0x04, KEYBOARD_MOD_NONE))
        self.assertEqual(char_to_hid("A"), (0x04, KEYBOARD_MOD_LSHIFT))
        self.assertEqual(char_to_hid("1"), (0x1E, KEYBOARD_MOD_NONE))
        self.assertEqual(char_to_hid("!"), (0x1E, KEYBOARD_MOD_LSHIFT))
        self.assertEqual(char_to_hid("\n")[0], 0x28)
        self.assertEqual(name_to_hid("Enter"), (0x28, KEYBOARD_MOD_NONE))
        self.assertEqual(name_to_hid("CapsLock"), (0x39, KEYBOARD_MOD_NONE))
        self.assertEqual(name_to_hid("F2"), (0x3B, KEYBOARD_MOD_NONE))

        kcodes, mods = parse_hotkey(["ctrl", "alt", "delete"])
        self.assertEqual(mods, KEYBOARD_MOD_LCTRL | KEYBOARD_MOD_LALT)
        self.assertEqual(kcodes, [0x4C])
        self.assertEqual(parse_hotkey(["win", "r"]), ([0x15], KEYBOARD_MOD_LGUI))


class TestClientAndAdapter(MockServerTestCase):
    def setUp(self):
        super().setUp()
        self.client = ESPCUAClient(host="127.0.0.1", port=80, timeout=2.0)
        self.driver = ESPCUADriver(host="127.0.0.1", port=80, timeout=2.0)

    def test_coordinate_normalization_and_clamping(self):
        self.driver.screen_width = 1920
        self.driver.screen_height = 1080
        self.assertEqual(self.driver.normalize_coordinates(0, 0), (0, 0))
        self.assertEqual(self.driver.normalize_coordinates(1920, 1080), (32767, 32767))
        self.assertEqual(self.driver.normalize_coordinates(-50, -50), (0, 0))
        self.assertEqual(self.driver.normalize_coordinates(9999, 9999), (32767, 32767))

    def test_client_errors(self):
        with self.assertRaises(ESPCUAClientError) as ctx:
            self.client._request("POST", "/api/v1/error/400")
        self.assertEqual(ctx.exception.status_code, 400)
        with self.assertRaises(ESPCUAClientError):
            ESPCUAClient(host="127.0.0.1", port=65530, timeout=0.5).capture()

    def test_atx_disconnected_status(self):
        MockKVMDispatcher.power_state = "disconnected"
        stat = self.driver.power("status")
        self.assertEqual(stat["power_state"], "disconnected")
        self.assertFalse(stat["connected"])

        state = self.driver.get_desktop_state()
        self.assertEqual(state["power_state"], "disconnected")
        self.assertFalse(state["atx_connected"])

    def test_run_steps_fail_fast_observe_and_drag(self):
        res_drag = self.driver.drag(100, 100, 200, 200, steps=3, delay_ms=1)
        self.assertEqual(res_drag["status"], "ok")
        self.assertEqual(MockKVMDispatcher.requests_log[-1]["body"]["action"], "drag")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            res = self.driver.run_steps(
                [
                    {"tool": "click", "args": {"x": 10, "y": 20}},
                    {"tool": "nonexistent_tool", "args": {}},
                    {"tool": "click", "args": {"x": 30, "y": 40}},
                ],
                delay_ms=1,
                observe={"screenshot_out_file": tmp_path, "settle_ms": 0},
            )
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["failed_step"], 1)
            self.assertEqual(len(res["steps"]), 2)
            self.assertEqual(os.path.getsize(tmp_path), len(MOCK_JPEG))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_dims_cache_across_cli_invocations(self):
        test_host = "192.168.99.98"
        cache_file = ESPCUADriver(host=test_host, port=80)._dims_cache_path()
        if os.path.exists(cache_file):
            os.remove(cache_file)

        orig_handle = MockKVMDispatcher.handle_request

        def handle_720p(req, timeout=5.0):
            resp = orig_handle(req, timeout)
            if req.selector.startswith("/api/v1/capture"):
                resp.headers["X-Video-Width"] = "1280"
                resp.headers["X-Video-Height"] = "720"
            return resp

        try:
            with patch("urllib.request.urlopen", side_effect=handle_720p):
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    cli.main(["--host", test_host, "screenshot", "-o", tmp_path])
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            driver2 = ESPCUADriver(host=test_host, port=80, auto_sync_dims=True)
            self.assertEqual((driver2.screen_width, driver2.screen_height), (1280, 720))
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)


class TestCLILogsAndRepoPortability(MockServerTestCase):
    def setUp(self):
        super().setUp()
        self.client = ESPCUAClient(host="127.0.0.1", port=80, timeout=2.0)

    def test_cli_subcommands_and_flags(self):
        cli.main(["edid", "720p", "--host", "192.168.6.201", "--no-wait"])
        self.assertTrue(MockKVMDispatcher.requests_log[-1]["url"].startswith("http://192.168.6.201:80/"))
        self.assertEqual(MockKVMDispatcher.requests_log[-1]["body"]["edid_profile"], "720p")

        cli.main(["--host", "127.0.0.1", "press", "CapsLock"])
        self.assertTrue(MockKVMDispatcher.caps_lock)
        cli.main(["--host", "127.0.0.1", "press", "CapsLock"])
        self.assertFalse(MockKVMDispatcher.caps_lock)

    def test_get_logs_incremental(self):
        res0 = self.client.get_logs(since=0)
        self.assertEqual(len(res0["logs"]), 3)
        res2 = self.client.get_logs(since=2)
        self.assertEqual([e["seq"] for e in res2["logs"]], [3])
        self.assertEqual(self.client.get_logs(since=3)["logs"], [])

    def test_cli_update_without_git(self):
        with patch("espcua.cli._find_git_repo", return_value=None):
            self.assertEqual(cli.main(["update"]), 1)

    def test_skill_portability_and_launcher(self):
        self.assertFalse(os.path.exists(os.path.join(REPO_ROOT, "plugin.json")))

        skill_dir = os.path.join(REPO_ROOT, "skills", "espcua-driver")
        for rel in ("SKILL.md", os.path.join("references", "WORKFLOW.md")):
            path = os.path.join(skill_dir, rel)
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read()
            self.assertNotIn("/Users/", txt)
            self.assertNotIn(".venv/bin", txt)

        launcher = os.path.join(skill_dir, "scripts", "espcua-driver")
        proc = subprocess.run([sys.executable, launcher, "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("run-steps", proc.stdout)
        self.assertIn("update", proc.stdout)


if __name__ == "__main__":
    unittest.main()
