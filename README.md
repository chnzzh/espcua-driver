# espcua-driver

Hardware IP-KVM CLI, Python SDK, and multi-agent Skill for **ESP32-P4 + C790 (TC358743)** KVM targets.  
Pure Python 3.8+ standard library — **zero third-party runtime dependencies**, offline-ready, works on macOS, Linux, and Windows.

基于硬件 IP-KVM（ESP32-P4 + C790）的控制工具集、Python SDK 与通用 Agent Skill，纯 Python 3.8+ 标准库实现（**零第三方依赖**），可直接在多台电脑与多种 Agent 上安装并随时更新。

---

## 1. 安装与更新 / Install & Update

### 方式 A（推荐）：独立 CLI + Skills CLI 安装 / Standalone CLI + Skills Install (Recommended)

```bash
# 1. 安装独立 CLI（`uv` 或 `pipx` 二选一）
uv tool install git+https://github.com/chnzzh/espcua-driver.git
# 或: pipx install git+https://github.com/chnzzh/espcua-driver.git

# 2. 安装 Skill（支持 Antigravity / Claude Code / Codex / Cursor 等）
npx skills add chnzzh/espcua-driver
```

随时更新到最新版本：

```bash
# 更新 CLI（任选其一）
espcua-driver update
uv tool upgrade espcua

# 更新 Skill
npx skills add chnzzh/espcua-driver
```

### 方式 B：Git Clone 安装 / Git Clone Install (Offline / Live Symlink Updates)

适合离线环境，或希望本地修改/拉取仓库后 Skill 与 CLI 同步生效的场景：

```bash
git clone https://github.com/chnzzh/espcua-driver.git
cd espcua-driver

# 默认安装 CLI + 本机已存在的 Agent (始终包含 Antigravity & ~/.agents/skills)
./install.sh

# 或强制安装到全部 4 个全局 Agent 目录 (Antigravity / Claude Code / Codex / ~/.agents/skills)
./install.sh --all
```

在 `git clone` 目录下运行 `./install.sh` 会自动采用动态链接模式，后续随时运行：

```bash
espcua-driver update
# 或进入仓库目录执行：
./update.sh    # git pull --ff-only 并刷新链接
```

### Windows 安装

```powershell
# 推荐：独立 CLI + Skill
uv tool install git+https://github.com/chnzzh/espcua-driver.git
npx skills add chnzzh/espcua-driver

# 或 Git Clone 安装：
git clone https://github.com/chnzzh/espcua-driver.git
cd espcua-driver
python install.py --all
```

---

## 2. 安装脚本常用参数 / Installer Flags (`install.py` / `install.sh`)

| Flag | Description |
| :--- | :--- |
| `--all` | 安装 Skill 至全部 4 个目录 (`~/.gemini/config/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`) |
| `--agent <name>` | 仅安装到指定 Agent (`antigravity`, `claude`, `codex`, `agents`，可多次指定) |
| `--project <dir>` | 安装到指定代码仓库的 `<dir>/.agents/skills/espcua-driver` |
| `--link` / `--copy` | 强制软链接动态更新（`.git` 仓库默认）或复制独立副本 |
| `--skill-only` | 仅安装 Skill（内置 `scripts/espcua-driver` 零依赖启动器） |
| `--standalone-cli` | 跳过 `uv` / `pipx`，直接安装至 `~/.local/bin/espcua-driver` |
| `--update` | 执行 `git pull --ff-only` 后刷新安装 |
| `--uninstall` | 卸载已安装的 Skill 与 CLI |

---

## 3. 快速使用 / Quick Usage

```bash
export ESPCUA_HOST=192.168.1.100   # 或通过 --host <ip> 传入

# 1. 查看硬件遥测（USB HID 挂载状态、HDMI 锁相与分辨率、ATX 电源状态、键盘指示灯）
espcua-driver status

# 2. 截图（自动读取并缓存当前屏幕宽高）
espcua-driver screenshot -o /tmp/desktop.jpg --json

# 3. 批量执行操作并自动等待后取证截图（Fail-Fast，对齐 CUA-Driver 风格）
espcua-driver run-steps '[
  {"tool":"hotkey","args":{"keys":["ctrl","alt","t"]}},
  {"tool":"wait","args":{"ms":900}},
  {"tool":"type_text","args":{"text":"uname -sr\n"}}
]' --observe /tmp/after.jpg --settle-ms 400

# 4. 其他常用命令
espcua-driver click 640 360
espcua-driver drag 100 100 500 500
espcua-driver press CapsLock
espcua-driver edid 720p             # 720p | 1080p30 | 1080p50 | 1024x768
espcua-driver hotplug               # 重发 HDMI HPD 脉冲
espcua-driver usb-reattach          # USB SE0 重枚举
espcua-driver logs --since 0        # 读取固件日志
espcua-driver update                # 更新最新版 CLI / Git 仓库
```

### Python SDK

```python
import os
from espcua import ESPCUADriver

drv = ESPCUADriver(host=os.environ.get("ESPCUA_HOST", "192.168.1.100"), auto_sync_dims=True)
state = drv.get_desktop_state(screenshot_out_file="/tmp/screen.jpg")
drv.click(640, 360)
drv.type_text("echo hello\n")
```

---

## 4. 目录结构 / Repository Layout

```text
espcua-driver/
├── pyproject.toml / setup.py        # Pure stdlib Python package (espcua)
├── install.sh / install.py / update.sh
├── espcua/                          # Client, CUA-style Adapter, Keymap, CLI
├── skills/espcua-driver/            # Multi-agent Skill (SKILL.md + WORKFLOW.md + scripts/)
└── tests/                           # Standalone unit tests (python -m unittest)
```
