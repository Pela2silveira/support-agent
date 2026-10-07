#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
./configure.sh
docker compose --env-file .env up -d --build
./grafana/ensure-viewer.sh
