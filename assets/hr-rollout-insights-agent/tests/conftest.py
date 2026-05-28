"""Test-level conftest — adds app/ to sys.path for all tests in this directory."""

import os
import sys
from pathlib import Path

# Add app/ to sys.path so modules can be imported without 'app.' prefix
APP_DIR = str(Path(__file__).parent.parent / "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.environ.setdefault("IBD_TESTING", "1")
