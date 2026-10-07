from diag.config import resolve_inventory_secrets


def test_inventory_bindings_resolve_from_env(tmp_path):
    inventory = tmp_path / "locations.yaml"
    inventory.write_text(
        """
locations:
  - id: hospital-alumine
    type: location
    children:
      - id: imaging
        type: system
        children:
          - id: pacs
            type: service
            children:
              - id: orthanc
                type: component
                secret_key: HOSPITAL_ALUMINE_IMAGING_PACS_ORTHANC_HOST
""".strip(),
        encoding="utf-8",
    )
    env = tmp_path / ".env"
    env.write_text(
        "HOSPITAL_ALUMINE_IMAGING_PACS_ORTHANC_HOST=10.20.10.20\n",
        encoding="utf-8",
    )

    bindings = resolve_inventory_secrets(inventory, env)

    assert bindings["HOSPITAL_ALUMINE_IMAGING_PACS_ORTHANC_HOST"] == "10.20.10.20"
