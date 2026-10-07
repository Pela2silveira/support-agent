from __future__ import annotations

import shutil
import subprocess

from diag.core.check import Check
from diag.core.result import CheckResult


class PingCheck(Check):
    name = "network/ping"

    def __init__(self, target: str | None = None):
        super().__init__(target)

    def run(self, target: str | None = None) -> CheckResult:
        target_name = str(target or self.target.value if self.target else "localhost")
        ping = shutil.which("ping")
        if ping is None:
            return CheckResult(
                status="UNKNOWN",
                check=self.name,
                target=target_name,
                message="ping utility not found",
                details={"command": "ping"},
            )

        try:
            completed = subprocess.run(
                [ping, "-c", "1", target_name],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return CheckResult(
                status="UNKNOWN",
                check=self.name,
                target=target_name,
                message="ping command failed to execute",
                details={"command": [ping, "-c", "1", target_name]},
            )

        if completed.returncode == 0:
            return CheckResult(
                status="OK",
                check=self.name,
                target=target_name,
                message="Host responded to ping",
                details={"stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()},
            )

        return CheckResult(
            status="CRITICAL",
            check=self.name,
            target=target_name,
            message="Host did not respond to ping",
            details={"returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()},
        )
