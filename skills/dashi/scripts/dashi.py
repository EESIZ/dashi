"""Portable MCP entrypoint: 15 inspection tools and controlled compose."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'guard'))
from host.mcp_server import mcp
mcp.run()
