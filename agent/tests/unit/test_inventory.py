from pathlib import Path

from diag.topology.inventory import Inventory


def test_inventory_loads_locations():
    inventory = Inventory(Path("inventory/locations.yaml"))

    assert "hospital-alumine" in inventory.locations
    assert "hospital-alumine/network" in inventory.locations
    assert "hospital-alumine/network/ipsec/remote" in inventory.locations
