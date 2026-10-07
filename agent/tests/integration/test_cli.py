from typer.testing import CliRunner

from diag.cli import app


runner = CliRunner()


def test_cli_lists_checks():
    result = runner.invoke(app, ["list-checks"])
    assert result.exit_code == 0
    assert "network/ping" in result.stdout
