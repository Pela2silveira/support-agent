from __future__ import annotations

from typing import Callable, Type

from .check import Check


class CheckRegistry:
    def __init__(self):
        self._checks: dict[str, Type[Check]] = {}

    def register(self, name: str, check_cls: Type[Check]) -> None:
        self._checks[name] = check_cls

    def get(self, name: str) -> Type[Check]:
        try:
            return self._checks[name]
        except KeyError as exc:
            raise KeyError(f"No check registered for '{name}'") from exc

    def names(self) -> list[str]:
        return sorted(self._checks)
