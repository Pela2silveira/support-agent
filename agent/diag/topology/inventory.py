from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml


@dataclass(frozen=True)
class InventoryItem:
    identifier: str
    item_type: str
    children: list["InventoryItem"] = field(default_factory=list)

    @property
    def path(self) -> str:
        return self.identifier


class Inventory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._locations: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Inventory file not found: {self.path}")

        with self.path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        self._locations = {}
        for item in data.get("locations", []):
            self._register_location(item)

    def _register_location(self, item: dict, parent: str | None = None) -> None:
        identifier = item["id"]
        if parent:
            identifier = f"{parent}/{identifier}"

        current = self._locations.setdefault(identifier, [])
        for child in item.get("children", []):
            child_id = f"{identifier}/{child['id']}"
            current.append(child_id)
            self._register_location(child, identifier)

    @property
    def locations(self) -> list[str]:
        return sorted(self._locations)

    def find(self, identifier: str) -> bool:
        return identifier in self._locations

    def iter_children(self, identifier: str) -> Iterable[str]:
        return tuple(self._locations.get(identifier, []))
