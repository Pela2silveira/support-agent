# AGENTS.md

## Project

Operational health visibility for healthcare infrastructure (PACS locations and related systems).

## Current focus

`observability/` — Grafana + Prometheus + blackbox for PACS health.

First target: SSS PACS (central LAN) — ICMP, DICOM TCP `:11112`, and MWL counts
per `PACS*` AET (Keycloak + dcm4chee API) every 20m.

## Agent scaffold

`agent/` is an existing CLI diagnostic scaffold. Do not expand it unless explicitly requested.

Archived design notes: `agent/docs/archive/`.

## Secrets

Do not put sensitive values in YAML or other tracked files.

Use:

- `.env` for local runtime values
- `.env.example` as the shared template
- a secret manager for shared or production environments

Keep `.env` out of Git. Track only templates and public topology.

## Near-term checks

Needed for PACS location health:

- ICMP / TCP from different hosts
- HTTP requests and status codes
- IPsec status (MikroTik and FortiGate)
- Simple Windows host script (pull or push) with check results
- MongoDB collection query (read-only, low impact on the application)

## Do not add

Unless explicitly requested:

- Telegram
- REST API / Web UI
- Automatic remediation
- Remote agents
- Ansible / SSH orchestration / WinRM
- Authentication / RBAC
- Message queues / microservices
- Kubernetes or cloud deployment for the agent

## Repo layout

```text
support-agent/
├── AGENTS.md
├── README.md
├── .env.example
├── agent/           # CLI scaffold — do not expand unless asked
└── observability/   # current focus
```
