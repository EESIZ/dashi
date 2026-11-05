"""Portable entrypoint for the compiled, controlled Dashi writer."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'guard'))
from host.cli import main
raise SystemExit(main())
