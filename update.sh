#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
git -C "$SCRIPT_DIR" pull --ff-only
exec python3 "$SCRIPT_DIR/install.py" "$@"
