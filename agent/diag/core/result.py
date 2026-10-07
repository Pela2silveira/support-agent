from __future__ import annotations

from dataclasses import dataclass, field


VALID_STATUSES = {"OK", "WARNING", "CRITICAL", "UNKNOWN", "SKIPPED"}


@dataclass
class CheckResult:
    status: str
    check: str
    target: str
    message: str
    details: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Unsupported status: {self.status}")
