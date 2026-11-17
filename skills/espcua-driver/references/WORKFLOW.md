# ESPCUA Workflow, Batch Schema & Python SDK Reference

## 1. `run-steps` JSON Schema

Pass either a JSON array `[...]` (with CLI flags `--delay-ms`, `--observe`, `--settle-ms`) or an object `{"steps": [...], "delay_ms": 100, "observe": {"screenshot_out_file": "/abs/out.jpg", "settle_ms": 400}}` to `espcua-driver run-steps` (alias `run_steps`). Execution stops immediately on the first failing step (`failed_step`) and still captures `observation` if requested.

Supported step `tool` entries:

| `tool` (aliases) | Required `args` | Optional `args` |
| :--- | :--- | :--- |
| `click` | `x`, `y` | `button` (`left`/`right`/`middle`), `count` (`1`/`2`) |
| `double_click` | `x`, `y` | `button` |
| `triple_click` | `x`, `y` | `button` |
| `right_click` | `x`, `y` | — |
| `move_cursor` (`move`) | `x`, `y` | — |
| `drag` | `x1`/`x`, `y1`/`y`, `x2`, `y2` | `button`, `steps` (`12`), `delay_ms` (`12`) |
| `scroll` | `delta` (or `wheel` / `dy`) | `x`, `y` |
| `type_text` (`type`) | `text` | `delay_ms` (`10`), `x`, `y` (clicks `(x, y)` first) |
| `press_key` (`press`) | `key` (`Enter`, `Escape`, `Tab`, `Shift`, `CapsLock`, `F1`–`F12`, `a`–`z`, etc.) | `down` (`true`/`false`), `modifiers` (`["ctrl","shift"]`) |
| `hotkey` | `keys` (e.g. `["ctrl","alt","t"]`, `["alt","f4"]`, `["ctrl","l"]`) | — |
| `wait` (`sleep`) | — | `ms` / `duration_ms` (default `250`) |
| `get_desktop_state` | — | `screenshot_out_file` |
| `edid` | `profile` (`720p`/`1080p30`/`1080p50`/`1024x768`) | `wait_lock_sec` (`2.5`) |
| `hotplug` / `usb_reattach` | — | — |
| `power` | `action` (`status`, `on`, `click`, etc.) | — |

## 2. Python SDK (`run_script` equivalent)

When an automation needs loops, polling, or conditional branching based on visual/telemetry checks, run one self-contained `python3` script (if `espcua` is not globally installed, prepend `<skill-dir>/scripts` to `sys.path`):

```python
import os
import sys

# Uncomment if running from a standalone copied skill without global install:
# sys.path.insert(0, os.path.expanduser("~/.gemini/config/skills/espcua-driver/scripts"))

from espcua import ESPCUADriver

drv = ESPCUADriver(
    host=os.environ.get("ESPCUA_HOST", "192.168.1.100"),
    port=int(os.environ.get("ESPCUA_PORT", "80")),
    auto_sync_dims=True,
)
st = drv.get_status()
if not st["system"]["usb_mounted"]:
    drv.usb_reattach()

res = drv.run_steps(
    [
        {"tool": "hotkey", "args": {"keys": ["ctrl", "alt", "t"]}},
        {"tool": "wait", "args": {"ms": 1000}},
        {"tool": "type_text", "args": {"text": "echo ok\n"}},
    ],
    observe={"screenshot_out_file": "/tmp/espcua_term.jpg", "settle_ms": 400},
)
print(res)
```

## 3. Common Recipes

- **Wake a sleeping display cleanly**: send `press Shift` or `move` to `(100, 100)` + `wait 1500ms` rather than clicking blind coordinates.
- **Open application launcher (GNOME)**: `press win` or click the top-left pill / bottom-left `Show Apps` icon seen in the screenshot; wait ~600ms, then type the app name and press `Return`.
- **Switch resolution cleanly**: run `espcua-driver edid 720p`, wait for the returned `detected_resolution`, then take a fresh `screenshot -o ...` before issuing any pixel clicks (`edid` changes display geometry).
- **Enter UEFI / BIOS after cold power-on**: power on with `power on`, wait ~1.5s, loop `press_key("F2")` / `press_key("Delete")` every 250ms while checking `get_desktop_state`.
- **Verify `usb_reattach` / `logs`**: inspect firmware event logs via `espcua-driver logs --since 0` if HDMI lock or HID attach behaves unexpectedly.
