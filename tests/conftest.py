"""Shared pytest setup.

The optimizer is a standalone package rooted at src/optimizer (its modules import
each other with bare names like `from catalog import ...`). The backend makes this
work by inserting that directory onto sys.path at runtime; the tests do the same so
they exercise the optimizer exactly as the running app does.
"""
import sys
from pathlib import Path

OPTIMIZER_DIR = Path(__file__).resolve().parents[1] / "src" / "optimizer"
if str(OPTIMIZER_DIR) not in sys.path:
    sys.path.insert(0, str(OPTIMIZER_DIR))
