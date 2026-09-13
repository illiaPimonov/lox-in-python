"""Test helper: import sibling ``lox-in-python`` modules despite the hyphen.

The project's root package directory is named ``lox-in-python``, which is
not a valid Python identifier, so it cannot be imported with a plain
``import`` statement. This helper resolves modules from it dynamically
through :mod:`importlib` instead, after making sure the project's parent
directory is on ``sys.path`` so the lookup succeeds regardless of the
current working directory or which test runner is in use.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

_TESTS_DIR = Path(__file__).resolve().parent
_PACKAGE_DIR = _TESTS_DIR.parent
_PACKAGE_NAME = _PACKAGE_DIR.name
_PARENT_DIR = _PACKAGE_DIR.parent

if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))


def imp(module: str = "") -> ModuleType:
    """Import ``<package>.<module>``, or the package itself if ``module`` is empty."""
    name = _PACKAGE_NAME if not module else f"{_PACKAGE_NAME}.{module}"
    return importlib.import_module(name)
