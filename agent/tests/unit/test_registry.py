from diag.core.registry import CheckRegistry
from diag.checks.network.ping import PingCheck


def test_registry_resolves_network_ping():
    registry = CheckRegistry()
    registry.register("network/ping", PingCheck)

    check_cls = registry.get("network/ping")
    assert check_cls is PingCheck
