# support-agent

Operational health visibility for healthcare infrastructure, starting with PACS location health.

## Structure

```text
support-agent/
├── README.md
├── AGENTS.md
├── .env.example
├── agent/              # CLI diagnostic scaffold (not current focus)
└── observability/      # Grafana stack (current focus)
```

## Current focus

`observability/` — Grafana + Prometheus + blackbox.

First target: SSS PACS at `10.1.62.52` (ICMP + DICOM TCP `:11112` + MWL per `PACS*` AET, every 20m).

```bash
cd observability
cp .env.example .env
./run.sh
```

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

See [observability/README.md](observability/README.md).

## Agent scaffold

`agent/` contains an existing Python CLI diagnostic scaffold. It is not the current development focus. Do not expand it unless explicitly requested.

## Secrets

1. Copy the env template:

```bash
cp .env.example .env
```

2. Fill in real values.

3. Keep `.env` out of Git.

Sensitive values must not live in tracked YAML or code. Use `.env` locally and a secret manager elsewhere.

## Contributors / agents

Read [AGENTS.md](AGENTS.md) for project rules and scope.
