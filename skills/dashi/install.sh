#!/bin/sh
# Install the compiled local Dashi tools and controlled writer.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
  echo 'This binary release requires Linux x86_64 and CPython 3.12.' >&2
  exit 1
fi
command -v uv >/dev/null 2>&1 || { echo 'Install uv before running this installer.' >&2; exit 1; }
uv venv "$HERE/.venv" --python 3.12
uv pip install --python "$HERE/.venv/bin/python" -r "$HERE/requirements.txt"
"$HERE/.venv/bin/python" -I -B -c 'import sys; from pathlib import Path; sys.path.insert(0, str(Path(sys.argv[1])/"guard")); from host.cli import main; from host.mcp_server import mcp; assert mcp.name == "dashi" and len(mcp._tool_manager.list_tools()) == 16; from dashi_guard.adapters import DashiBackend; assert DashiBackend(str(Path(sys.argv[1])/"guard")).resolve_route("수필을 다듬어 주세요.", "자료", "essay")["status"] == "ready"' "$HERE"
printf '%s\n' 'MCP registration (Claude CLI must be installed and logged in for compose):'
printf 'claude mcp add --scope user dashi -- "%s/.venv/bin/python" "%s/scripts/dashi.py"\n' "$HERE" "$HERE"
if ! command -v claude >/dev/null 2>&1; then
  printf '%s\n' 'Claude CLI is not on PATH. Inspection tools work; compose requires a local CLI login.'
fi
