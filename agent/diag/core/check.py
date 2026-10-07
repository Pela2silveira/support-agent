from __future__ import annotations

from abc import ABC, abstractmethod

from .result import CheckResult
from .target import Target


class Check(ABC):
    """Base abstraction for a diagnostic check."""

    name: str = "base/check"

    def __init__(self, target: str | Target | None = None):
        self.target = Target.from_value(target) if target is not None else None

    @abstractmethod
    def run(self, target: str | Target | None = None) -> CheckResult:
        raise NotImplementedError
