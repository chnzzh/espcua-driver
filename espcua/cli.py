"""Command-line interface (CLI) for ESPCUA IP-KVM driver."""

import os
import sys
import json
import shutil
import argparse
import subprocess
from typing import Optional
from espcua.adapter import ESPCUADriver


def _find_git_repo() -> Optional[str]:
    cur = os.path.dirname(os.path.realpath(__file__))
    for _ in range(3):
        cur = os.path.dirname(cur)
        if not cur:
            break
        has_git = os.path.exists(os.path.join(cur, ".git"))
        has_pkg = os.path.isdir(os.path.join(cur, "espcua")) and (
            os.path.exists(os.path.join(cur, "pyproject.toml"))
            or os.path.exists(os.path.join(cur, "setup.py"))
        )
        if has_git and has_pkg:
            return cur
    return None


def _run_tool_upgrade(tool: str) -> Optional[int]:
    exe = shutil.which(tool)
    if not exe:
        return None
    cmd = [exe, "tool", "upgrade", "espcua"] if tool == "uv" else [exe, "upgrade", "espcua"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as e:
        print(json.dumps({"status": "error", "method": tool, "error": str(e)}, indent=2))
        return 1
    out = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
    if proc.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "method": tool,
                    "error": out or f"{tool} upgrade failed with code {proc.returncode}",
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps({"status": "ok", "method": tool, "output": out}, indent=2))
    return 0


def _run_self_update() -> int:
    repo_root = _find_git_repo()
    if not repo_root:
        exec_lower = (sys.executable or "").lower()
        for tool in ("uv", "pipx"):
            if tool in exec_lower:
                rc = _run_tool_upgrade(tool)
                if rc is not None:
                    return rc
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "Not installed from a git clone; upgrade via: uv tool upgrade espcua",
                },
                indent=2,
            )
        )
        return 1

    try:
        before = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        pull = subprocess.run(
            ["git", "-C", repo_root, "pull", "--ff-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        after = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError as e:
        print(json.dumps({"status": "error", "repo": repo_root, "error": str(e)}, indent=2))
        return 1

    out = ((pull.stdout or "") + ("\n" + pull.stderr if pull.stderr else "")).strip()
    if pull.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "error",
                    "repo": repo_root,
                    "before": before,
                    "after": after,
                    "error": out or f"git pull failed with code {pull.returncode}",
                },
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "repo": repo_root,
                "before": before,
                "after": after,
                "updated": bool(before and after and before != after),
                "output": out,
            },
            indent=2,
        )
    )
    return 0


def _build_sub_common_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--host", default=argparse.SUPPRESS, help="ESP32-P4 IP (or ESPCUA_HOST env var)")
    common.add_argument("--port", type=int, default=argparse.SUPPRESS, help="HTTP server port (or ESPCUA_PORT)")
    common.add_argument("--timeout", type=float, default=argparse.SUPPRESS, help="HTTP timeout in seconds")
    common.add_argument("--screen-width", type=int, default=argparse.SUPPRESS, help="Override target screen width")
    common.add_argument("--screen-height", type=int, default=argparse.SUPPRESS, help="Override target screen height")
    return common


def main(args=None):
    common = _build_sub_common_parser()
    parser = argparse.ArgumentParser(
        prog="espcua-driver",
        description="Command-line tool for controlling ESP32-P4 IP-KVM via CUA-Driver primitives.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("ESPCUA_HOST", "192.168.1.100"),
        help="ESP32-P4 IP address (default: ESPCUA_HOST or 192.168.1.100)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ESPCUA_PORT", "80")),
        help="HTTP server port (default: ESPCUA_PORT or 80)",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds (default: 5.0)")
    parser.add_argument("--screen-width", type=int, default=None, help="Override target screen width")
    parser.add_argument("--screen-height", type=int, default=None, help="Override target screen height")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    # screenshot / get_desktop_state / capture
    p_screen = subparsers.add_parser(
        "screenshot",
        aliases=["get_desktop_state", "capture"],
        parents=[common],
        help="Capture a desktop frame to file",
    )
    p_screen.add_argument("-o", "--output", default="desktop.jpg", help="Output file path (default: desktop.jpg)")
    p_screen.add_argument("--json", action="store_true", help="Print JSON metadata instead of summary line")

    # click
    p_click = subparsers.add_parser("click", parents=[common], help="Mouse click at screen coordinates")
    p_click.add_argument("x", type=int, help="X pixel coordinate")
    p_click.add_argument("y", type=int, help="Y pixel coordinate")
    p_click.add_argument("--button", default="left", choices=["left", "right", "middle"], help="Mouse button")
    p_click.add_argument("--count", type=int, default=1, help="Click count (1=single, 2=double)")

    # double-click
    p_dbl = subparsers.add_parser(
        "double-click", aliases=["double_click"], parents=[common], help="Double-click at screen coordinates"
    )
    p_dbl.add_argument("x", type=int)
    p_dbl.add_argument("y", type=int)
    p_dbl.add_argument("--button", default="left", choices=["left", "right", "middle"])

    # right-click
    p_rclick = subparsers.add_parser(
        "right-click", aliases=["right_click"], parents=[common], help="Right-click at screen coordinates"
    )
    p_rclick.add_argument("x", type=int)
    p_rclick.add_argument("y", type=int)

    # move / move_cursor
    p_move = subparsers.add_parser(
        "move", aliases=["move_cursor"], parents=[common], help="Move cursor to screen coordinates"
    )
    p_move.add_argument("x", type=int, help="X pixel coordinate")
    p_move.add_argument("y", type=int, help="Y pixel coordinate")

    # drag
    p_drag = subparsers.add_parser("drag", parents=[common], help="Mouse drag gesture from (X1, Y1) to (X2, Y2)")
    p_drag.add_argument("x1", type=int)
    p_drag.add_argument("y1", type=int)
    p_drag.add_argument("x2", type=int)
    p_drag.add_argument("y2", type=int)
    p_drag.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p_drag.add_argument("--steps", type=int, default=12)
    p_drag.add_argument("--delay-ms", type=int, default=12)

    # scroll
    p_scroll = subparsers.add_parser("scroll", parents=[common], help="Scroll mouse wheel")
    p_scroll.add_argument("delta", type=int, help="Wheel delta (-127..127)")
    p_scroll.add_argument("--x", type=int, default=None)
    p_scroll.add_argument("--y", type=int, default=None)

    # type / type_text
    p_type = subparsers.add_parser(
        "type", aliases=["type_text"], parents=[common], help="Type text string via USB Keyboard emulation"
    )
    p_type.add_argument("text", help="Text string to type")
    p_type.add_argument("--delay-ms", type=int, default=10, help="Inter-key delay in ms")
    p_type.add_argument("--x", type=int, default=None, help="Optional X coordinate to focus before typing")
    p_type.add_argument("--y", type=int, default=None, help="Optional Y coordinate to focus before typing")

    # press / press_key
    p_press = subparsers.add_parser(
        "press", aliases=["press_key"], parents=[common], help="Press single key (Enter, Escape, F1, etc.)"
    )
    p_press.add_argument("key", help="Key name to press")
    p_press.add_argument("--down", dest="down", action="store_true", default=None, help="Hold key down")
    p_press.add_argument("--up", dest="down", action="store_false", help="Release key up")
    p_press.add_argument("--mod", nargs="*", default=None, help="Optional modifier keys (ctrl, alt, shift, gui)")

    # hotkey
    p_hotkey = subparsers.add_parser("hotkey", parents=[common], help="Send hotkey combination")
    p_hotkey.add_argument("keys", nargs="+", help="Key names (e.g. ctrl alt delete)")

    # edid
    p_edid = subparsers.add_parser("edid", parents=[common], help="Switch C790 EDID resolution profile")
    p_edid.add_argument("profile", choices=["720p", "1080p30", "1080p50", "1024x768"])
    p_edid.add_argument("--no-wait", action="store_true", help="Do not wait for HDMI re-lock")

    # hotplug
    subparsers.add_parser("hotplug", parents=[common], help="Pulse HDMI HPD to re-negotiate display")

    # usb-reattach
    subparsers.add_parser(
        "usb-reattach", aliases=["usb_reattach"], parents=[common], help="Trigger passive SE0 USB HID re-attach"
    )

    # power
    p_power = subparsers.add_parser("power", parents=[common], help="ATX Power and Reset Control")
    p_power.add_argument("action", choices=["on", "off", "click", "hold", "cycle", "reset", "status"])

    # status
    subparsers.add_parser("status", parents=[common], help="Get system, video, and ATX telemetry")

    # logs
    p_logs = subparsers.add_parser("logs", parents=[common], help="Fetch firmware runtime logs")
    p_logs.add_argument("--since", type=int, default=0, help="Fetch logs with seq > SINCE")

    # update / self-update
    subparsers.add_parser(
        "update",
        aliases=["self-update", "self_update"],
        parents=[common],
        help="Pull latest version when installed from a git clone",
    )

    # run-steps / run_steps
    p_steps = subparsers.add_parser(
        "run-steps",
        aliases=["run_steps"],
        parents=[common],
        help="Execute batch of CUA-Driver steps from JSON string or file",
    )
    p_steps.add_argument("steps", help="JSON array/object string or file path containing steps")
    p_steps.add_argument("--delay-ms", type=int, default=None, help="Inter-step delay in ms")
    p_steps.add_argument("--observe", default=None, help="Save end checkpoint screenshot to file")
    p_steps.add_argument("--settle-ms", type=int, default=300, help="Settle delay before observation capture")

    parsed = parser.parse_args(args)
    if parsed.command in ("update", "self-update", "self_update"):
        return _run_self_update()

    driver = ESPCUADriver(
        host=parsed.host,
        port=parsed.port,
        timeout=parsed.timeout,
        auto_sync_dims=(parsed.host != "127.0.0.1"),
    )
    if parsed.screen_width is not None and parsed.screen_height is not None:
        driver.screen_width = parsed.screen_width
        driver.screen_height = parsed.screen_height
        driver._dims_synced = True

    try:
        cmd = parsed.command
        if cmd in ("screenshot", "get_desktop_state", "capture"):
            res = driver.get_desktop_state(screenshot_out_file=parsed.output)
            if parsed.json or cmd == "get_desktop_state":
                print(json.dumps(res, indent=2))
            else:
                print(
                    f"Captured screenshot saved to {parsed.output} "
                    f"({res['dimensions']['width']}x{res['dimensions']['height']})"
                )
        elif cmd == "click":
            res = driver.click(parsed.x, parsed.y, button=parsed.button, count=parsed.count)
            print(json.dumps(res, indent=2))
        elif cmd in ("double-click", "double_click"):
            res = driver.double_click(parsed.x, parsed.y, button=parsed.button)
            print(json.dumps(res, indent=2))
        elif cmd in ("right-click", "right_click"):
            res = driver.right_click(parsed.x, parsed.y)
            print(json.dumps(res, indent=2))
        elif cmd in ("move", "move_cursor"):
            res = driver.move_cursor(parsed.x, parsed.y)
            print(json.dumps(res, indent=2))
        elif cmd == "drag":
            res = driver.drag(
                parsed.x1,
                parsed.y1,
                parsed.x2,
                parsed.y2,
                button=parsed.button,
                steps=parsed.steps,
                delay_ms=parsed.delay_ms,
            )
            print(json.dumps(res, indent=2))
        elif cmd == "scroll":
            res = driver.scroll(parsed.delta, x=parsed.x, y=parsed.y)
            print(json.dumps(res, indent=2))
        elif cmd in ("type", "type_text"):
            res = driver.type_text(parsed.text, delay_ms=parsed.delay_ms, x=parsed.x, y=parsed.y)
            print(json.dumps(res, indent=2))
        elif cmd in ("press", "press_key"):
            res = driver.press_key(parsed.key, down=parsed.down, modifiers=parsed.mod)
            print(json.dumps(res, indent=2))
        elif cmd == "hotkey":
            res = driver.hotkey(parsed.keys)
            print(json.dumps(res, indent=2))
        elif cmd == "edid":
            res = driver.set_edid(parsed.profile, wait_lock_sec=0.0 if parsed.no_wait else 2.5)
            print(json.dumps(res, indent=2))
        elif cmd == "hotplug":
            res = driver.hotplug()
            print(json.dumps(res, indent=2))
        elif cmd in ("usb-reattach", "usb_reattach"):
            res = driver.usb_reattach()
            print(json.dumps(res, indent=2))
        elif cmd == "power":
            res = driver.power(parsed.action)
            print(json.dumps(res, indent=2))
        elif cmd == "status":
            print(json.dumps(driver.get_status(), indent=2))
        elif cmd == "logs":
            print(json.dumps(driver.client.get_logs(since=parsed.since), indent=2))
        elif cmd in ("run-steps", "run_steps"):
            raw_txt = parsed.steps.lstrip()
            if raw_txt.startswith("[") or raw_txt.startswith("{"):
                raw_data = json.loads(parsed.steps)
            else:
                with open(parsed.steps, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

            delay_ms = 100
            observe = None
            settle_ms = parsed.settle_ms
            if isinstance(raw_data, dict):
                steps_list = raw_data["steps"]
                delay_ms = int(raw_data.get("delay_ms", delay_ms))
                observe = raw_data.get("observe")
                settle_ms = int(raw_data.get("settle_ms", settle_ms))
            else:
                steps_list = raw_data

            if parsed.delay_ms is not None:
                delay_ms = parsed.delay_ms
            if parsed.observe is not None:
                observe = {"screenshot_out_file": parsed.observe, "settle_ms": settle_ms}

            res = driver.run_steps(steps_list, delay_ms=delay_ms, observe=observe, settle_ms=settle_ms)
            print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    raise SystemExit(main())
