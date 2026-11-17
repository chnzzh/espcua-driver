#!/usr/bin/env python3
"""Cross-platform installer & live updater for espcua-driver CLI and skills."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "espcua-driver"
PACKAGE_NAME = "espcua"


def _agent_dirs(home: Path) -> dict[str, Path]:
    return {
        "antigravity": home / ".gemini" / "config" / "skills",
        "claude": home / ".claude" / "skills",
        "codex": home / ".codex" / "skills",
        "agents": home / ".agents" / "skills",
    }


def _default_agent_targets(home: Path) -> list[str]:
    targets = ["agents", "antigravity"]
    if (home / ".claude").exists():
        targets.append("claude")
    if (home / ".codex").exists():
        targets.append("codex")
    return targets


def _remove_path(path: Path) -> bool:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return True
    if path.is_dir():
        shutil.rmtree(path)
        return True
    return False


def _copy_tree_clean(src: Path, dst: Path) -> None:
    _remove_path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "*.egg-info"),
    )


def _make_executable(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def _install_skill_target(skill_src: Path, pkg_src: Path, dst: Path, link_mode: bool) -> str:
    _remove_path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if link_mode:
        try:
            dst.symlink_to(skill_src.resolve(), target_is_directory=True)
            _make_executable(skill_src / "scripts" / SKILL_NAME)
            return f"{dst} -> {skill_src.resolve()}"
        except OSError:
            pass

    _copy_tree_clean(skill_src, dst)
    _copy_tree_clean(pkg_src, dst / "scripts" / PACKAGE_NAME)
    _make_executable(dst / "scripts" / SKILL_NAME)
    return str(dst)


def _try_tool_install(repo_root: Path, editable: bool) -> str | None:
    for tool in ("uv", "pipx"):
        exe = shutil.which(tool)
        if not exe:
            continue
        if tool == "uv":
            cmd = [exe, "tool", "install", "--force"]
            if editable:
                cmd.append("--editable")
            cmd.append(str(repo_root))
        else:
            cmd = [exe, "install", "--force"]
            if editable:
                cmd.append("--editable")
            cmd.append(str(repo_root))

        print(f"Trying {tool} install ({'editable' if editable else 'copy'}) from {repo_root} ...")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError:
            continue
        if proc.returncode == 0:
            print(f"Installed CLI via {tool}.")
            return tool
        lines = (proc.stderr or proc.stdout or "").strip().splitlines()
        msg = lines[-1] if lines else f"exit code {proc.returncode}"
        print(f"Note: {tool} install skipped ({msg}); using zero-dependency launcher.")
    return None


def _install_standalone_cli(repo_root: Path, home: Path, link_mode: bool) -> Path:
    bin_dir = home / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    if link_mode:
        import_root = repo_root.resolve()
    else:
        share_dir = home / ".local" / "share" / SKILL_NAME
        share_dir.mkdir(parents=True, exist_ok=True)
        _copy_tree_clean(repo_root / PACKAGE_NAME, share_dir / PACKAGE_NAME)
        import_root = share_dir

    py_exec = sys.executable or "python3"
    launcher_posix = bin_dir / SKILL_NAME
    launcher_posix.write_text(
        f"#!{py_exec}\n"
        f"import sys\n"
        f"sys.path.insert(0, {str(import_root)!r})\n"
        f"from espcua.cli import main\n"
        f"if __name__ == '__main__':\n"
        f"    raise SystemExit(main())\n",
        encoding="utf-8",
    )
    _make_executable(launcher_posix)

    if os.name == "nt":
        cmd_wrapper = bin_dir / f"{SKILL_NAME}.cmd"
        cmd_wrapper.write_text(
            f'@echo off\r\n"{py_exec}" "{launcher_posix}" %*\r\n',
            encoding="utf-8",
        )
        print(f"Installed standalone Windows CLI launcher: {cmd_wrapper}")
        return cmd_wrapper

    mode_desc = f"live-linked -> {import_root}" if link_mode else f"copied -> {import_root}"
    print(f"Installed standalone CLI launcher: {launcher_posix} ({mode_desc})")
    return launcher_posix


def _uninstall(home: Path, project_dir: str | None, targets: list[str]) -> int:
    all_dirs = _agent_dirs(home)
    removed: list[str] = []

    for name in targets:
        skill_path = all_dirs[name] / SKILL_NAME
        if _remove_path(skill_path):
            removed.append(str(skill_path))

    if project_dir:
        proj_skill = Path(project_dir).expanduser().resolve() / ".agents" / "skills" / SKILL_NAME
        if _remove_path(proj_skill):
            removed.append(str(proj_skill))

    for p in (
        home / ".local" / "bin" / SKILL_NAME,
        home / ".local" / "bin" / f"{SKILL_NAME}.cmd",
        home / ".local" / "share" / SKILL_NAME,
    ):
        if _remove_path(p):
            removed.append(str(p))

    for tool, args in (("uv", ["tool", "uninstall", PACKAGE_NAME]), ("pipx", ["uninstall", PACKAGE_NAME])):
        exe = shutil.which(tool)
        if exe:
            subprocess.run([exe, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    if removed:
        print("Removed:")
        for item in removed:
            print(f"  - {item}")
    else:
        print("Nothing to uninstall.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install or update espcua-driver CLI and agent skills.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install skill into all global agent directories (antigravity, claude, codex, agents)",
    )
    parser.add_argument(
        "--agent",
        action="append",
        choices=["antigravity", "claude", "codex", "agents"],
        help="Target global agent skill directory (repeatable)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Install skill into <dir>/.agents/skills/espcua-driver",
    )
    parser.add_argument(
        "--skill-only",
        action="store_true",
        help="Install only the skill directory (skip global CLI installation)",
    )
    parser.add_argument(
        "--standalone-cli",
        action="store_true",
        help="Skip uv/pipx and install zero-dependency launcher directly to ~/.local/bin",
    )
    mode_grp = parser.add_mutually_exclusive_group()
    mode_grp.add_argument(
        "--link",
        action="store_true",
        help="Symlink skills and editable-link CLI to this repo so git pull updates everything immediately",
    )
    mode_grp.add_argument(
        "--copy",
        action="store_true",
        help="Copy files into destination directories instead of symlinking",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Run git pull --ff-only in this repo before refreshing installation",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove installed skill directories and CLI",
    )

    args = parser.parse_args(argv)
    home = Path.home()
    repo_root = Path(__file__).resolve().parent
    is_git = (repo_root / ".git").exists()
    link_mode = args.link or (is_git and not args.copy)

    if args.update:
        if not is_git:
            print("Error: --update requires a git clone (.git missing).", file=sys.stderr)
            return 1
        print(f"Pulling latest changes in {repo_root} ...")
        pull = subprocess.run(["git", "-C", str(repo_root), "pull", "--ff-only"], check=False)
        if pull.returncode != 0:
            return pull.returncode

    if args.all:
        targets = ["antigravity", "claude", "codex", "agents"]
    elif args.agent:
        targets = list(dict.fromkeys(args.agent))
    elif args.project and not args.uninstall:
        targets = []
    else:
        targets = _default_agent_targets(home)

    if args.uninstall:
        return _uninstall(home, args.project, targets or ["antigravity", "claude", "codex", "agents"])

    skill_src = repo_root / "skills" / SKILL_NAME
    pkg_src = repo_root / PACKAGE_NAME
    if not skill_src.is_dir() or not pkg_src.is_dir():
        print(f"Error: expected skills/{SKILL_NAME} and {PACKAGE_NAME}/ under {repo_root}", file=sys.stderr)
        return 1

    if not args.skill_only:
        installed_via = None if args.standalone_cli else _try_tool_install(repo_root, editable=link_mode)
        if installed_via is None:
            launcher = _install_standalone_cli(repo_root, home, link_mode=link_mode)
            bin_dir_str = str(launcher.parent)
            if bin_dir_str not in os.environ.get("PATH", "").split(os.pathsep):
                print(f'Reminder: add {bin_dir_str} to PATH (e.g. export PATH="{bin_dir_str}:$PATH")')

    all_dirs = _agent_dirs(home)
    installed_skills: list[str] = []

    for name in targets:
        installed_skills.append(_install_skill_target(skill_src, pkg_src, all_dirs[name] / SKILL_NAME, link_mode))

    if args.project:
        proj_dst = Path(args.project).expanduser().resolve() / ".agents" / "skills" / SKILL_NAME
        installed_skills.append(_install_skill_target(skill_src, pkg_src, proj_dst, link_mode))

    print("Installed skills:")
    for item in installed_skills:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
