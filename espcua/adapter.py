"""ESPCUADriver: High-level CUA-Driver compatible adapter for ESP32-P4 IP-KVM."""

import os
import json
import time
import tempfile
from typing import Optional, Any
from espcua.client import ESPCUAClient


class ESPCUADriver:
    """Provides high-level methods matching CUA-Driver and LLM agent conventions."""

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 80,
        timeout: float = 5.0,
        auto_sync_dims: bool = False,
    ):
        self.client = ESPCUAClient(host=host, port=port, timeout=timeout)
        self.screen_width = 1920
        self.screen_height = 1080
        self._dims_synced = False
        self._auto_sync_dims = auto_sync_dims
        if auto_sync_dims:
            self._dims_synced = self._load_dims_cache()

    def _dims_cache_path(self) -> str:
        safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in self.client.host)
        return os.path.join(tempfile.gettempdir(), f"espcua_dims_{safe}_{self.client.port}.json")

    def _save_dims_cache(self, width: int, height: int) -> None:
        if width <= 64 or height <= 64:
            return
        try:
            with open(self._dims_cache_path(), "w", encoding="utf-8") as f:
                json.dump({"width": int(width), "height": int(height)}, f)
        except Exception:
            pass

    def _load_dims_cache(self) -> bool:
        try:
            with open(self._dims_cache_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            w = int(data.get("width") or 0)
            h = int(data.get("height") or 0)
            if w > 64 and h > 64:
                self.screen_width = w
                self.screen_height = h
                return True
        except Exception:
            pass
        return False

    def sync_dimensions(self) -> tuple[int, int]:
        """Queries live detected HDMI resolution and updates/caches screen dimensions."""
        vid = self.client.get_video_status()
        det = vid.get("detected_resolution") or {}
        w = int(det.get("width") or 0)
        h = int(det.get("height") or 0)
        if w > 64 and h > 64:
            self.screen_width = w
            self.screen_height = h
            self._dims_synced = True
            if self.client.host != "127.0.0.1":
                self._save_dims_cache(w, h)
        return self.screen_width, self.screen_height

    def _ensure_dims(self) -> None:
        if self._auto_sync_dims and not self._dims_synced:
            self._dims_synced = True
            try:
                self.sync_dimensions()
            except Exception:
                pass

    def normalize_coordinates(self, x: int, y: int) -> tuple[int, int]:
        """Maps target pixel coordinates (X, Y) to normalized absolute HID pointer coordinates (0..32767)."""
        w = max(1, self.screen_width)
        h = max(1, self.screen_height)

        # Clamping
        cx = max(0, min(x, w))
        cy = max(0, min(y, h))

        abs_x = int((cx * 32767) / w)
        abs_y = int((cy * 32767) / h)

        return min(32767, max(0, abs_x)), min(32767, max(0, abs_y))

    def get_desktop_state(self, screenshot_out_file: Optional[str] = None) -> dict[str, Any]:
        """Emulates CUA-Driver's get_desktop_state by capturing a fresh HDMI video frame.

        Returns target metadata, dimensions, power state, and optionally saves the screenshot.
        """
        jpeg_bytes, headers = self.client.capture()

        # Update detected dimensions if valid (>64x64)
        w_hdr = headers.get("X-Video-Width") or headers.get("x-video-width")
        h_hdr = headers.get("X-Video-Height") or headers.get("x-video-height")
        updated_from_hdr = False
        if w_hdr and h_hdr:
            try:
                w = int(w_hdr)
                h = int(h_hdr)
                if w > 64 and h > 64:
                    self.screen_width = w
                    self.screen_height = h
                    self._dims_synced = True
                    updated_from_hdr = True
                    if self.client.host != "127.0.0.1":
                        self._save_dims_cache(w, h)
            except (ValueError, TypeError):
                pass
        if not updated_from_hdr and self._auto_sync_dims:
            try:
                self.sync_dimensions()
            except Exception:
                pass

        if screenshot_out_file:
            with open(screenshot_out_file, "wb") as f:
                f.write(jpeg_bytes)

        atx_info = {}
        try:
            atx_info = self.client.get_atx_status()
        except Exception:
            pass

        out: dict[str, Any] = {
            "target": {"kind": "desktop", "display_id": "primary"},
            "dimensions": {"width": self.screen_width, "height": self.screen_height},
            "screenshot_out_file": screenshot_out_file,
            "power_state": atx_info.get("power_state", "unknown"),
            "status": "ok",
        }
        if "connected" in atx_info:
            out["atx_connected"] = atx_info["connected"]
        return out

    def click(self, x: int, y: int, button: str = "left", count: int = 1) -> dict[str, Any]:
        """Sends pixel-grounded mouse click using Absolute Pointer coordinates."""
        self._ensure_dims()
        action = "click" if count <= 1 else "double_click"
        payload = {
            "mode": "absolute",
            "action": action,
            "x": x,
            "y": y,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "button": button,
        }
        return self.client.send_mouse(payload)

    def double_click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        """Convenience method for double clicking at (x, y)."""
        return self.click(x, y, button=button, count=2)

    def right_click(self, x: int, y: int) -> dict[str, Any]:
        """Convenience method for right clicking at (x, y)."""
        return self.click(x, y, button="right", count=1)

    def move_cursor(self, x: int, y: int) -> dict[str, Any]:
        """Moves cursor to pixel (x, y) via Absolute Pointer."""
        self._ensure_dims()
        payload = {
            "mode": "absolute",
            "action": "move",
            "x": x,
            "y": y,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
        }
        return self.client.send_mouse(payload)

    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        button: str = "left",
        steps: int = 12,
        delay_ms: int = 12,
    ) -> dict[str, Any]:
        """Executes an atomic drag-and-drop gesture from (x1, y1) to (x2, y2) via firmware HID."""
        self._ensure_dims()
        payload = {
            "mode": "absolute",
            "action": "drag",
            "x": x1,
            "y": y1,
            "x2": x2,
            "y2": y2,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "button": button,
            "steps": max(2, steps),
            "delay_ms": max(1, delay_ms),
        }
        return self.client.send_mouse(payload)

    def scroll(self, delta: int, x: Optional[int] = None, y: Optional[int] = None) -> dict[str, Any]:
        """Scrolls mouse wheel by delta units (+127..-127)."""
        self._ensure_dims()
        payload: dict[str, Any] = {
            "mode": "absolute",
            "action": "scroll",
            "wheel": delta,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
        }
        if x is not None and y is not None:
            payload["x"] = x
            payload["y"] = y
        return self.client.send_mouse(payload)

    def press_key(
        self,
        key: str,
        down: Optional[bool] = None,
        modifiers: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Presses, holds, or releases a single key."""
        if down is True:
            action = "down"
        elif down is False:
            action = "up"
        else:
            action = "press"

        payload: dict[str, Any] = {"action": action, "key": key}
        if modifiers:
            payload["modifiers"] = modifiers
        return self.client.send_keyboard(payload)

    def hotkey(self, keys: list[str]) -> dict[str, Any]:
        """Sends simultaneous hotkey combinations (e.g. ['ctrl', 'alt', 'del'])."""
        payload = {"action": "hotkey", "keys": keys}
        return self.client.send_keyboard(payload)

    def type_text(
        self,
        text: str,
        delay_ms: int = 10,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> dict[str, Any]:
        """Types string of text via USB HID Keyboard emulation, optionally focusing (x, y) first."""
        if x is not None and y is not None:
            self.click(x, y, button="left")
            if self.client.host != "127.0.0.1":
                time.sleep(0.08)
        payload = {"action": "type", "text": text, "delay_ms": delay_ms}
        return self.client.send_keyboard(payload)

    def power(self, action: str) -> dict[str, Any]:
        """ATX Motherboard power management.

        Supported actions: 'on', 'off', 'click', 'hold', 'cycle', 'reset', 'status'.
        """
        act = action.strip().lower()
        if act == "status":
            return self.client.get_atx_status()
        elif act == "reset":
            return self.client.send_reset()
        elif act in ("click", "hold", "on", "off", "cycle"):
            return self.client.send_power(act)
        else:
            raise ValueError(f"Unsupported power action: {action}")

    def set_edid(self, profile: str, wait_lock_sec: float = 2.5) -> dict[str, Any]:
        """Switches active C790 EDID profile ('720p', '1080p30', '1080p50', '1024x768')."""
        res = self.client.set_video_config({"edid_profile": profile})
        if wait_lock_sec > 0 and self.client.host != "127.0.0.1":
            deadline = time.monotonic() + wait_lock_sec
            time.sleep(min(0.6, wait_lock_sec))
            while time.monotonic() < deadline:
                try:
                    vid = self.client.get_video_status()
                    det = vid.get("detected_resolution") or {}
                    w = int(det.get("width") or 0)
                    h = int(det.get("height") or 0)
                    if vid.get("video_sync_locked") and w > 64 and h > 64:
                        self.screen_width = w
                        self.screen_height = h
                        self._dims_synced = True
                        self._save_dims_cache(w, h)
                        break
                except Exception:
                    pass
                time.sleep(0.4)
            res["detected_resolution"] = {"width": self.screen_width, "height": self.screen_height}
        return res

    def hotplug(self) -> dict[str, Any]:
        """Pulses HDMI HPD low/high to trigger target EDID re-read."""
        return self.client.set_video_config({"hotplug": True})

    def usb_reattach(self) -> dict[str, Any]:
        """Simulates physical USB HID cable replug via passive SE0."""
        return self.client.set_video_config({"usb_reattach": True})

    def get_status(self) -> dict[str, Any]:
        """Returns combined system, video, and ATX status telemetry."""
        sys_res = self.client.get_system_status()
        vid_res = self.client.get_video_status()
        atx_res = self.power("status")
        det = vid_res.get("detected_resolution") or {}
        w = int(det.get("width") or 0)
        h = int(det.get("height") or 0)
        if w > 64 and h > 64:
            self.screen_width = w
            self.screen_height = h
            self._dims_synced = True
            if self.client.host != "127.0.0.1":
                self._save_dims_cache(w, h)
        return {"system": sys_res, "video": vid_res, "atx": atx_res}

    def run_steps(
        self,
        steps: list[dict[str, Any]],
        delay_ms: int = 100,
        observe: Any = None,
        settle_ms: int = 300,
    ) -> dict[str, Any]:
        """Executes a batch of CUA-Driver tool actions fail-fast, with optional end observation."""
        results = []
        failed_step: Optional[int] = None
        for idx, step in enumerate(steps):
            tool = step.get("tool")
            args = step.get("args", {})
            try:
                if tool == "click":
                    res = self.click(args["x"], args["y"], args.get("button", "left"), args.get("count", 1))
                elif tool == "double_click":
                    res = self.double_click(args["x"], args["y"], args.get("button", "left"))
                elif tool == "triple_click":
                    self.double_click(args["x"], args["y"], args.get("button", "left"))
                    if self.client.host != "127.0.0.1":
                        time.sleep(0.03)
                    res = self.click(args["x"], args["y"], button=args.get("button", "left"), count=1)
                elif tool == "right_click":
                    res = self.right_click(args["x"], args["y"])
                elif tool in ("move_cursor", "move"):
                    res = self.move_cursor(args["x"], args["y"])
                elif tool == "drag":
                    sx = args["x1"] if "x1" in args else args["x"]
                    sy = args["y1"] if "y1" in args else args["y"]
                    res = self.drag(
                        sx,
                        sy,
                        args["x2"],
                        args["y2"],
                        args.get("button", "left"),
                        args.get("steps", 12),
                        args.get("delay_ms", 12),
                    )
                elif tool == "scroll":
                    if "delta" in args:
                        delta = int(args["delta"])
                    elif "wheel" in args:
                        delta = int(args["wheel"])
                    elif "dy" in args:
                        delta = -int(args["dy"])
                    else:
                        raise KeyError("delta")
                    res = self.scroll(delta, args.get("x"), args.get("y"))
                elif tool in ("type_text", "type"):
                    res = self.type_text(
                        args["text"],
                        args.get("delay_ms", 10),
                        x=args.get("x"),
                        y=args.get("y"),
                    )
                elif tool in ("press_key", "press"):
                    res = self.press_key(args["key"], args.get("down"), modifiers=args.get("modifiers"))
                elif tool == "hotkey":
                    res = self.hotkey(args["keys"])
                elif tool in ("wait", "sleep"):
                    ms = int(args.get("ms", args.get("duration_ms", 250)))
                    if ms > 0 and self.client.host != "127.0.0.1":
                        time.sleep(ms / 1000.0)
                    res = {"status": "ok", "waited_ms": ms}
                elif tool == "power":
                    res = self.power(args["action"])
                elif tool == "edid":
                    res = self.set_edid(args["profile"], wait_lock_sec=float(args.get("wait_lock_sec", 2.5)))
                elif tool == "hotplug":
                    res = self.hotplug()
                elif tool == "usb_reattach":
                    res = self.usb_reattach()
                elif tool == "get_desktop_state":
                    res = self.get_desktop_state(args.get("screenshot_out_file"))
                else:
                    raise ValueError(f"Unknown tool in step {idx}: {tool}")

                results.append({"step": idx, "tool": tool, "ok": True, "result": res})
            except Exception as e:
                results.append({"step": idx, "tool": tool, "ok": False, "error": str(e)})
                failed_step = idx
                break

            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

        obs_state = None
        if observe is not None and observe is not False:
            obs_file = None
            obs_settle = settle_ms
            if isinstance(observe, str):
                obs_file = observe
            elif isinstance(observe, dict):
                obs_file = observe.get("screenshot_out_file")
                obs_settle = int(observe.get("settle_ms", settle_ms))
            if obs_settle > 0 and self.client.host != "127.0.0.1":
                time.sleep(obs_settle / 1000.0)
            obs_state = self.get_desktop_state(screenshot_out_file=obs_file)

        out: dict[str, Any] = {
            "status": "ok" if failed_step is None else "error",
            "total_steps": len(steps),
            "steps": results,
        }
        if failed_step is not None:
            out["failed_step"] = failed_step
        if obs_state is not None:
            out["observation"] = obs_state
        return out
