"""Ruff-adjacent legibility checks for Python."""

from importlib.metadata import PackageNotFoundError, version

from .core import Diagnostic, check_path, check_source
from .rules import RULES

__all__ = ["Diagnostic", "RULES", "check_path", "check_source"]

try:
    __version__ = version("ruff-legibility")
except PackageNotFoundError:
    __version__ = "0.3.1"
