"""
Root conftest.py — makes sure `from src.clients... import ...` works no
matter where `pytest` is invoked from (repo root, tests/, CI runner, etc.),
without requiring the package to be `pip install -e .`'d first.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))