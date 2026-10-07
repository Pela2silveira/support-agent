from __future__ import annotations

from typing import Annotated

import typer

from diag.checks.network.ping import PingCheck
from diag.core.registry import CheckRegistry

app = typer.Typer(add_completion=False, help="Diagnostic platform CLI")

registry = CheckRegistry()
registry.register("network/ping", PingCheck)


@app.command("list-checks")
def list_checks() -> None:
    """List the available checks."""
    for name in registry.names():
        typer.echo(name)


@app.command("check")
def perform_check(name: Annotated[str, typer.Argument(...)], target: Annotated[str, typer.Argument(...)]) -> None:
    """Run a named check against a target."""
    check_cls = registry.get(name)
    result = check_cls(target=target).run()
    typer.echo(f"{result.status} {result.check} {result.target} {result.message}")


if __name__ == "__main__":
    app()
