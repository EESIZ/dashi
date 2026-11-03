#!/bin/sh
# 윤문 스킬 설치: 같은 폴더에 .venv(Python 3.12, x86_64 Linux)를 만들고 MCP 서버를 등록한다.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
uv venv "$HERE/.venv" --python 3.12
uv pip install --python "$HERE/.venv/bin/python" -r "$HERE/requirements.txt"
echo "MCP 등록:"
echo "  claude mcp add --scope user yunmun -- $HERE/.venv/bin/python $HERE/scripts/yunmun.py"
