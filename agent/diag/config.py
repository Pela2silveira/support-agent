from __future__ import annotations

import os
from pathlib import Path

import yaml


def secret_key_for(*parts: str, suffix: str = "HOST") -> str:
    """Build a stable secret key from a location/resource hierarchy."""
    tokens: list[str] = []
    for part in parts:
        if not part:
            continue
        normalized = str(part).strip().replace("/", " ").replace("-", " ").replace(".", " ")
        tokens.extend(token for token in normalized.split() if token)

    if not tokens:
        raise ValueError("At least one hierarchy part is required to build a secret key")

    key = "_".join(token.upper() for token in tokens)
    return f"{key}_{suffix}"


def load_env(path: str | Path = ".env") -> dict[str, str]:
    """Load environment variables from a simple .env file."""
    env_path = Path(path)
    values: dict[str, str] = {}

    if not env_path.exists():
        return values

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    for key, value in values.items():
        os.environ.setdefault(key, value)

    return values


def resolve_inventory_secrets(inventory_path: str | Path, env_path: str | Path = ".env") -> dict[str, str]:
    """Bind secret keys declared in the inventory to runtime values from the environment."""
    inventory_file = Path(inventory_path)
    env = load_env(env_path)

    if not inventory_file.exists():
        raise FileNotFoundError(f"Inventory file not found: {inventory_file}")

    with inventory_file.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    bindings: dict[str, str] = {}

    def walk(nodes: list[dict] | None, location_prefix: str | None = None) -> None:
        if not nodes:
            return

        for node in nodes:
            current_location = node.get("id")
            current_path = [location_prefix] if location_prefix else []
            current_path.append(current_location)
            current_path = [item for item in current_path if item]

            secret_key = node.get("secret_key")
            if secret_key:
                value = env.get(secret_key)
                if value is None:
                    raise KeyError(f"Missing secret key '{secret_key}' in environment")
                bindings[secret_key] = value

            for child in node.get("children", []):
                walk([child], "/".join(current_path))

    walk(data.get("locations", []))
    return bindings
