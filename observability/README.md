# Observability

Local Grafana + Prometheus + blackbox + dcm4chee MWL exporter + FortiGate SD-WAN (Docker Compose).

Goal: visibility into PACS location health. First target: SSS PACS (central LAN).

## Structure

```text
observability/
├── .env.example
├── configure.sh
├── docker-compose.yml
├── run.sh
├── stop.sh
├── blackbox/
├── fortigate/
│   ├── aet-healthcheck.yaml.example
│   ├── aet-healthcheck.yaml   # local map (gitignored)
│   └── fortigate-key.yaml     # generated (gitignored)
├── prometheus/
│   ├── prometheus.yml         # no host IPs — uses file_sd
│   ├── file_sd/               # generated targets (gitignored)
│   └── rules/                 # generated SD-WAN rules (gitignored)
├── exporters/
│   └── dcm4chee-mwl/
├── grafana/
│   ├── dashboards/
│   │   └── sss-pacs.json
│   └── provisioning/
└── README.md
```

## Requirements

- Docker
- Docker Compose
- Host network must reach the PACS host (`SSS_PACS_HOST`), Keycloak / archive API, and FortiGate HTTPS API

## Checks

| Check | Target | Interval |
|-------|--------|----------|
| ICMP | `SSS_PACS_HOST` | 1m scrape |
| DICOM TCP | `SSS_PACS_HOST`:`SSS_PACS_DICOM_PORT` | 1m scrape |
| Keycloak auth | client_credentials token | MWL interval |
| REST API | any successful dcm4chee-arc query → `sss_pacs_rest_up` | MWL interval |
| MWL today | AETs `PACS*` — items with SPS date `00400002` = today | MWL interval |
| Studies | `AS_RECEIVED` QIDO — per AET, StudyDate = today (absolute gauge) | MWL interval |
| FortiGate | probe via fortigate-exporter | 1m |
| SD-WAN | per AET — any health-check member up → `sss_pacs_sdwan_up` | 1m |

MWL flow:

1. Keycloak `client_credentials` token
2. `GET /dcm4chee-arc/aets` → filter prefix `PACS`
3. Per AET: list `.../mwlitems` and count client-side items with SPS date today
   → `sss_pacs_mwl_count_day`

Studies flow (same token):

1. Per `PACS*` AET, `StudyDate` = today (exporter TZ):
   `GET .../aets/AS_RECEIVED/rs/studies/count?StudyDate=...&ReceivingApplicationEntityTitleOfSeries=<AET>`
2. Total → `sss_pacs_studies_total{aet}`
3. With `StudyInstanceUID=<SSS_STUDY_INSTANCE_UID_PREFIX>*` → `sss_pacs_studies_worklist_uid{aet}`
4. Grafana uses the dashboard time picker (`last_over_time(...[$__range])`);
   **fuera_mwl** = total − worklist

### SD-WAN (SSS FortiGate)

1. `configure.sh` writes `fortigate/fortigate-key.yaml` from `SSS_FORTIGATE_URL` + `SSS_FORTIGATE_TOKEN`
2. fortigate_exporter probes `VirtualWAN/HealthCheck` (API `.../monitor/virtual-wan/health-check`)
3. Map in [`fortigate/aet-healthcheck.yaml`](fortigate/aet-healthcheck.yaml):
   - `PACSHMM: mmoreno` → aggregate only
   - `PACSHMM: mmoreno,iface1,iface2` → also columns **m1** / **m2** (interface names = Prometheus label `interface`)
4. Recording rules:
   - `sss_pacs_sdwan_up{aet}` = any member up
   - `sss_pacs_sdwan_member_up{aet,slot,interface}` = per listed interface
5. **UP** if **any** member of that health-check is up

Discover interface names:

```bash
curl -s "http://localhost:9710/probe?target=${SSS_FORTIGATE_URL}" \
  | grep 'fortigate_virtual_wan_status{.*sla="mmoreno"'
```

API user needs read on `netgrp.cfg` (and status).
Dashboard **PACS**: table uses the Grafana time picker (last value in range). Historical granularity ≈ exporter collect interval.

## Start

```bash
cd observability
cp .env.example .env
# fill SSS_* keys including SSS_FORTIGATE_URL / SSS_FORTIGATE_TOKEN
# edit fortigate/aet-healthcheck.yaml
./run.sh
```

`run.sh` runs `configure.sh` then compose up (builds the MWL exporter image on first start).

If the MWL build fails with `Temporary failure in name resolution` while installing pip packages, Docker DNS cannot reach PyPI. The compose file builds that image with `network: host`. Retry:

```bash
docker compose --env-file .env build --no-cache dcm4chee-mwl
./run.sh
```

After changing FortiGate URL/token or the AET map:

```bash
./configure.sh
docker compose --env-file .env up -d fortigate-exporter prometheus grafana
```

## Access

- Grafana: http://localhost:${GRAFANA_PORT:-3001} (dashboard **PACS**)
  - Admin: `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`
  - Viewer (solo PACS): `GRAFANA_VIEWER_USER` / `GRAFANA_VIEWER_PASSWORD` (`./grafana/ensure-viewer.sh`)
- Prometheus: http://localhost:9090
- Blackbox: http://localhost:9115
- MWL exporter: http://localhost:9100/metrics
- FortiGate exporter: http://localhost:9710/probe?target=https://&lt;fg-host&gt;

## Environment

Secrets and host addresses live in **`.env`** and gitignored generated files (`prometheus/file_sd/*.yml`, `fortigate/fortigate-key.yaml`, `fortigate/aet-healthcheck.yaml`). Commit only `.env.example` and `*.example` maps.


See `.env.example`. Required for MWL:

```dotenv
SSS_DCM4CHEE_MULTI_PACS=true
SSS_DCM4CHEE_AUTH_HOST=
SSS_DCM4CHEE_AUTH_REALM=dcm4che
SSS_AUTH_CLIENT=
SSS_AUTH_TOKEN=
SSS_DCM4CHEE_HOST=
```

When `SSS_DCM4CHEE_MULTI_PACS=true`, AETs are discovered and filtered by `SSS_DCM4CHEE_AET_PREFIX` (default `PACS`). When `false`, set `SSS_DCM4CHEE_AET`.

Optional: `SSS_DCM4CHEE_MWL_INTERVAL_SECONDS` (default `1200`), `SSS_DCM4CHEE_TLS_VERIFY`, `SSS_DCM4CHEE_TZ`.

Studies: `SSS_STUDIES_RS_AET` (default `AS_RECEIVED`), `SSS_STUDY_INSTANCE_UID_PREFIX`.

FortiGate:

```dotenv
SSS_PACS_HOST=
SSS_PACS_DICOM_PORT=11112
SSS_FORTIGATE_URL=
SSS_FORTIGATE_TOKEN=
```

Keep `.env` and `fortigate/fortigate-key.yaml` out of Git.

## Stop

```bash
cd observability
./stop.sh
```
