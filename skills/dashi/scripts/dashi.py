"""dashi MCP 서버 진입점. 컴파일된 모듈(*.so)을 같은 폴더에서 읽는다.
실행: <skill>/.venv/bin/python <skill>/scripts/dashi.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server
server.mcp.run()
