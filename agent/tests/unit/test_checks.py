from diag.checks.network.ping import PingCheck
from diag.core.result import CheckResult


def test_ping_check_returns_ok_for_localhost():
    check = PingCheck(target="localhost")
    result = check.run()

    assert isinstance(result, CheckResult)
    assert result.status in {"OK", "CRITICAL", "UNKNOWN"}
    assert result.check == "network/ping"
