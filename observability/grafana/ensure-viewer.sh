#!/usr/bin/env bash
# Create/update a Grafana Viewer user that can only see the PACS folder/dashboard.
# Credentials: GRAFANA_VIEWER_USER / GRAFANA_VIEWER_PASSWORD in .env
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "missing .env — copy from .env.example" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-admin}"
VIEWER_USER="${GRAFANA_VIEWER_USER:-}"
VIEWER_PASSWORD="${GRAFANA_VIEWER_PASSWORD:-}"
GRAFANA_PORT="${GRAFANA_PORT:-3001}"
GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:${GRAFANA_PORT}}"
FOLDER_TITLE="PACS"
FOLDER_UID="pacs"

if [[ -z "$VIEWER_USER" || -z "$VIEWER_PASSWORD" ]]; then
  echo "GRAFANA_VIEWER_USER/PASSWORD unset — skipping viewer provisioning"
  exit 0
fi

auth=(-u "${ADMIN_USER}:${ADMIN_PASSWORD}")

echo "Waiting for Grafana at ${GRAFANA_URL} ..."
for _ in $(seq 1 60); do
  if curl -sf "${auth[@]}" "${GRAFANA_URL}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl -sf "${auth[@]}" "${GRAFANA_URL}/api/health" >/dev/null

python3 - "$GRAFANA_URL" "$ADMIN_USER" "$ADMIN_PASSWORD" "$VIEWER_USER" "$VIEWER_PASSWORD" "$FOLDER_TITLE" "$FOLDER_UID" <<'PY'
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode

base, admin_user, admin_password, viewer_user, viewer_password, folder_title, folder_uid = sys.argv[1:]
auth = b64encode(f"{admin_user}:{admin_password}".encode()).decode()


def req(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode() or "{}"
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            payload = {"message": raw}
        return exc.code, payload


# --- viewer user ---
status, users = req(
    "GET",
    f"/api/users/lookup?loginOrEmail={urllib.parse.quote(viewer_user)}",
)
if status == 200 and isinstance(users, dict) and users.get("id"):
    user_id = int(users["id"])
    print(f"viewer exists id={user_id} login={viewer_user}")
else:
    status, created = req(
        "POST",
        "/api/admin/users",
        {
            "name": viewer_user,
            "login": viewer_user,
            "password": viewer_password,
            "OrgId": 1,
        },
    )
    if status not in (200, 201) or not created.get("id"):
        raise SystemExit(f"create viewer failed ({status}): {created}")
    user_id = int(created["id"])
    print(f"created viewer id={user_id} login={viewer_user}")

# Force password sync (idempotent for rotations in .env)
status, pw = req(
    "PUT",
    f"/api/admin/users/{user_id}/password",
    {"password": viewer_password},
)
if status not in (200, 201):
    raise SystemExit(f"set viewer password failed ({status}): {pw}")

# Org role Viewer
status, role = req(
    "PATCH",
    f"/api/org/users/{user_id}",
    {"role": "Viewer"},
)
if status not in (200, 201):
    # fallback older path
    status, role = req(
        "PATCH",
        f"/api/orgs/1/users/{user_id}",
        {"role": "Viewer"},
    )
if status not in (200, 201):
    raise SystemExit(f"set viewer org role failed ({status}): {role}")

# --- PACS folder ---
status, folder = req("GET", f"/api/folders/{folder_uid}")
if status != 200:
    status, folder = req(
        "POST",
        "/api/folders",
        {"uid": folder_uid, "title": folder_title},
    )
    if status not in (200, 201):
        raise SystemExit(f"create folder failed ({status}): {folder}")
    print(f"created folder {folder_title} uid={folder_uid}")
else:
    print(f"folder exists {folder_title} uid={folder_uid}")

# Only Admins (org) + this viewer user — no org-wide Viewer on the folder
status, perms = req(
    "POST",
    f"/api/folders/{folder_uid}/permissions",
    {
        "items": [
            {"role": "Admin", "permission": 4},
            {"userId": user_id, "permission": 1},
        ]
    },
)
if status not in (200, 201):
    raise SystemExit(f"set folder permissions failed ({status}): {perms}")

print(f"viewer {viewer_user!r} can view folder {folder_title!r} only")
PY
