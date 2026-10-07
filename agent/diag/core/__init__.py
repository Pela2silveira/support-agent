"""Core domain types for the diagnostics platform."""

from .check import Check
from .registry import CheckRegistry
from .result import CheckResult
from .target import Target

__all__ = ["Check", "CheckRegistry", "CheckResult", "Target"]
