---
name: espcua-driver
description: >-
  Drive a physical target computer at hardware KVM level (BIOS/UEFI, OS login, Wayland/X11 desktop, GUI apps) via ESP32-P4 + C790 over the `espcua-driver` CLI or `ESPCUADriver` Python SDK. Use when the user asks to view, operate, automate, or perform GUI/console tasks on a physical machine attached to the ESPCUA IP-KVM.
---

# espcua-driver

Observe the target display via HDMI capture, ground every pixel coordinate visually, batch known USB HID actions in one fail-fast `run-steps --observe` call, and verify outcomes from the returned screenshot. Unlike host-local `cua-driver`, ESPCUA has no accessibility tree—ground every pointer action on a fresh JPEG captured at the current resolution.

## Binary & Connection

- CLI command: `espcua-driver` (if not in GUI `PATH` on macOS/Linux, check `~/.local/bin/espcua-driver`; if installed via `git clone` or offline bundle, `<skill-dir>/scripts/espcua-driver` also works directly).
- Python SDK: `python3` (`from espcua import ESPCUADriver`). If `espcua` is not installed globally, add `<skill-dir>/scripts` to `PYTHONPATH` / `sys.path`.
- Target selection: export `ESPCUA_HOST=<kvm-ip>` (optional `ESPCUA_PORT`, default `80`) or pass `--host <kvm-ip>` before or after any subcommand.

## Efficient loop

1. **Preflight (`status`)**: confirm `system.usb_mounted == true` and `video.video_sync_locked == true` before sending UI input.
   ```bash
   ESPCUA_HOST=<kvm-ip> espcua-driver status
   ```
   - `usb_mounted: false` → run `usb-reattach`, wait ~2.5s, re-check `status`.
   - `video_sync_locked: false` (monitor DPMS sleep) → wake with `press Shift` or `move` to two distinct points, wait ~1.5s, re-check `status`.
2. **Observe (`screenshot` / `get_desktop_state`)**: capture to a scratch JPEG path and view it with `read_file` to obtain exact pixel `(x, y)` coordinates in the reported `width×height` space. Never invent coordinates without reading the image.
   ```bash
   espcua-driver --host <kvm-ip> screenshot -o /tmp/espcua_screen.jpg
   ```
   (`espcua-driver` automatically caches and syncs `width×height` across CLI invocations and `--observe` snapshots.)
3. **Batch known actions (`run-steps` + `--observe`)**: combine every action whose coordinates/keys are already decided into a single `run-steps` call with `--observe <checkpoint.jpg>`. It executes sequentially, stops at the first error (`failed_step`), waits `--settle-ms` (default `300`), and captures one end screenshot.
   ```bash
   espcua-driver --host <kvm-ip> run-steps '[
     {"tool":"hotkey","args":{"keys":["ctrl","alt","t"]}},
     {"tool":"wait","args":{"ms":900}},
     {"tool":"type_text","args":{"text":"uname -sr\n"}}
   ]' --observe /tmp/espcua_after.jpg --settle-ms 500
   ```
4. **Verify from the image**: HTTP `"status": "ok"` only confirms USB HID delivery, never that a window opened or a command succeeded. Always inspect the returned observation image at each checkpoint.
5. **Restore & clean up**: leave the remote desktop in the requested clean state and remove any temporary local screenshots before finishing.

## Act

| Goal | Command | Notes |
| :--- | :--- | :--- |
| Check health, resolution & LEDs | `espcua-driver status` | Verify `usb_mounted`, `video_sync_locked`, `leds` |
| Capture screen (text / JSON) | `espcua-driver screenshot -o /abs/p.jpg` | Add `--json` or use `get_desktop_state` for JSON metadata |
| Click / double / right click | `espcua-driver click X Y [--count 2]` | Also `double-click X Y`, `right-click X Y` |
| Move cursor / drag / scroll | `espcua-driver move X Y` / `drag X1 Y1 X2 Y2` / `scroll DELTA` | Negative `scroll` scrolls down |
| Focus + type ASCII text | `espcua-driver type "cmd\n" [--x X --y Y]` | Add `--delay-ms 12` for slow/BIOS consoles |
| Single key / shortcut combo | `espcua-driver press Enter` / `hotkey ctrl alt t` | Check `leds.caps_lock` before case-sensitive typing |
| Batch actions + capture | `espcua-driver run-steps '<json-or-file>' --observe /abs/p.jpg` | Fail-fast; supports `wait`, `type_text`, `click`, `hotkey`, etc. |
| Switch HDMI resolution | `espcua-driver edid 720p\|1080p30\|1080p50\|1024x768` | Re-capture before clicking after EDID change |
| Re-handshake display / USB | `espcua-driver hotplug` / `espcua-driver usb-reattach` | Wait ~2–3s after either command |
| ATX power telemetry / control | `espcua-driver power status` | `power_state: "disconnected"` (`connected: false`) means ATX sense wires are unplugged; rely on `video_sync_locked` & `usb_mounted`. Destructive power actions require explicit user authorization |

## Guardrails & failure recovery

- **Never bypass the KVM**: when operating or testing via `espcua-driver`, use only `espcua-driver` / `ESPCUADriver` (do not SSH or probe the target behind its back unless separately authorized to inspect).
- **Power safety**: never run `power off`, `power hold`, `power cycle`, `power reset`, or click OS shutdown/restart controls unless the user explicitly asked for it.
- **Display blanked mid-task**: wake with `press Shift` or `move` to two different coordinates (`click` can accidentally trigger UI behind the sleep shield), wait ~1.5s, and re-capture.
- **Wrong click location**: check whether `edid` changed or the screenshot came from an old resolution; run `screenshot -o ...` to refresh dimensions and inspect the visual cursor position.
- **Caps Lock mismatch**: check `system.leds.caps_lock` in `status` or the `press` response; toggle with `press CapsLock` if unexpectedly `true`.

## References

Load on demand for batch JSON schemas, Python scripting loops, and BIOS/power recipes:
- [references/WORKFLOW.md](./references/WORKFLOW.md)
