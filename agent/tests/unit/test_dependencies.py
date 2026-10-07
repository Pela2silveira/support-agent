from diag.topology.dependencies import DependencyGraph


def test_dependency_graph_loads_edges():
    graph = DependencyGraph("inventory/dependencies.yaml")

    assert graph.depends_on("hospital-alumine/imaging/pacs") == [
        "hospital-alumine/network/ipsec"
    ]
    assert graph.depends_on("hospital-alumine/network/ipsec") == [
        "central/network/ipsec"
    ]
