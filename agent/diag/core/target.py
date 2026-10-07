from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    value: str

    @classmethod
    def from_value(cls, value: str | "Target" | None) -> "Target":
        if value is None:
            return cls("")
        if isinstance(value, cls):
            return value
        return cls(str(value))

    @property
    def parts(self) -> list[str]:
        return [part for part in self.value.split("/") if part]

    def __str__(self) -> str:
        return self.value
