from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Dependency:
    source: str
    target: str


class DependencyGraph:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._dependencies: list[Dependency] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Dependency file not found: {self.path}")

        with self.path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        self._dependencies = [
            Dependency(source=dep["from"], target=dep["to"])
            for dep in data.get("dependencies", [])
        ]

    @property
    def dependencies(self) -> list[Dependency]:
        return list(self._dependencies)

    def depends_on(self, source: str) -> list[str]:
        return [dep.target for dep in self._dependencies if dep.source == source]
