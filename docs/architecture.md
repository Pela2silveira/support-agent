# Diagnostic & Remediation Platform

## 1. Purpose

Build an operational diagnostics and remediation platform for distributed healthcare and infrastructure environments.

The platform will provide a reusable library of:

* Health checks
* Diagnostic procedures
* Operational actions/remediation
* Dependency-aware diagnosis
* Infrastructure and application queries

The same diagnostic/action engine must eventually be usable through multiple interfaces:

* Bash/CLI
* Telegram bot
* Future web/API interfaces

The first MVP will focus exclusively on a local CLI executed from a cloned Git repository.

The architecture must allow Telegram, remote execution, agents, Ansible, and other execution mechanisms to be added later without redesigning the core domain model.

---

# 2. Core Concepts

The platform models infrastructure using two complementary structures.

## 2.1 Hierarchy

Resources are organized as:

```text
Location
└── System
    └── Service
        └── Component
```

Example:

```text
hospital-castro-rendon
└── network
    ├── internet
    │   └── gateway
    └── ipsec
        ├── central
        └── remote
└── imaging
    ├── pacs
    │   └── orthanc
    ├── dicom
    │   └── dicom-server
    └── portal
        └── api
```

This hierarchy represents **what exists**.

---

# 3. Dependency Graph

The hierarchy alone is insufficient because infrastructure contains cross-system dependencies.

For example:

```text
central/network
        │
        ▼
central/ipsec
        │
        ▼
hospital/network/ipsec
        │
        ├──────────────┐
        ▼              ▼
hospital/pacs     hospital/dicom
```

Dependencies must therefore be modeled separately.

Example:

```yaml
dependencies:

  - from: hospital-castro-rendon/imaging/pacs
    to: hospital-castro-rendon/network/ipsec

  - from: hospital-castro-rendon/imaging/dicom
    to: hospital-castro-rendon/network/ipsec

  - from: hospital-castro-rendon/network/ipsec
    to: central/network/ipsec
```

The dependency graph will eventually allow the platform to:

1. Identify a failed root dependency.
2. Determine affected components.
3. Avoid executing checks that cannot provide useful information.
4. Produce an impact analysis.

Example:

```text
IPSEC: CRITICAL

Affected:
  PACS
  DICOM
  Portal

PACS check:
  SKIPPED

Reason:
  dependency hospital/network/ipsec is unavailable
```

---

# 4. Checks

A check is a read-only operation that determines the health or state of a target.

Examples:

```text
network/ping
network/dns
network/http
network/tcp
network/route

ipsec/status
ipsec/connectivity

application/api-health
application/scheduled-studies
application/study-status

infrastructure/mongo-query
```

Each check should return a normalized structured result.

Possible states:

```text
OK
WARNING
CRITICAL
UNKNOWN
SKIPPED
```

Example:

```json
{
  "status": "CRITICAL",
  "check": "ipsec/status",
  "target": "hospital-castro-rendon/network/ipsec",
  "message": "IPSEC tunnel is down",
  "details": {
    "remote": "10.20.0.254"
  }
}
```

Checks should be small and composable.

A complex diagnosis should be built by orchestrating multiple checks rather than implementing one giant diagnostic script.

---

# 5. Actions

Actions are operations that can modify infrastructure or application state.

Examples:

```text
ipsec/restart
service/restart
application/retry
cache/clear
```

Actions are fundamentally different from checks.

Checks:

```text
read-only
```

Actions:

```text
potentially destructive
state-changing
must be explicitly authorized
should be auditable
```

An action should eventually have metadata such as:

```yaml
name: restart-ipsec
risk: high
requires_confirmation: true
```

The MVP does not need remote remediation yet, but the domain model should distinguish `Check` from `Action` from the beginning.

---

# 6. Execution / Transport

The diagnostic domain must not depend directly on a particular execution mechanism.

Possible execution backends:

```text
local shell
SSH
WinRM
HTTP/API
Fortigate API
Ansible
Site Agent
```

The conceptual model is:

```text
Check / Action
      │
      ▼
Execution interface
      │
      ├── local
      ├── ssh
      ├── winrm
      ├── http
      └── ansible
```

The MVP should implement only local execution.

Do not introduce Ansible unless a concrete requirement appears.

---

# 7. Why Python

Python should be used as the orchestration/runtime layer.

Individual checks may eventually be implemented using:

```text
Python
Bash
PowerShell
HTTP
MongoDB queries
Fortigate API
Ansible
```

Python provides:

* CLI framework
* domain model
* registry
* dependency graph
* result normalization
* orchestration
* future Telegram integration
* future API integration
* testing

The platform should not become a collection of unrelated shell scripts.

---

# 8. MVP Scope

The MVP must remain intentionally small.

## Included

### CLI

Example:

```bash
diag locations
diag systems hospital-castro-rendon
diag checks hospital-castro-rendon
diag check hospital-castro-rendon/network/dns
diag check hospital-castro-rendon/network/internet
diag diagnose hospital-castro-rendon
```

### Inventory

YAML-based inventory.

Example:

```yaml
locations:

  hospital-castro-rendon:

    description: Hospital Castro Rendón

    systems:

      network:

        services:

          internet:
            components:
              gateway:
                host: 10.20.0.1

          ipsec:
            components:
              remote:
                type: fortigate
                host: 10.20.0.254

      imaging:

        services:

          pacs:
            components:
              orthanc:
                host: 10.20.10.20
```

### Dependencies

Separate YAML definition.

### Checks

At least:

```text
ping
DNS
HTTP
```

These should demonstrate the check abstraction and normalized results.

### Dependency-aware diagnosis

A command such as:

```bash
diag diagnose hospital-castro-rendon
```

should execute applicable checks and produce a human-readable summary.

---

# 9. MVP Non-Goals

Do NOT implement initially:

* Telegram bot
* Web UI
* REST API
* Database
* Authentication
* RBAC
* Remote agents
* Ansible
* WinRM
* SSH orchestration
* Automatic remediation
* Cloud deployment
* Kubernetes deployment
* Observability stack

These are future extensions.

The architecture should not prevent them from being added later.

---

# 10. Suggested Repository Structure

```text
diagnostic-platform/
│
├── README.md
├── pyproject.toml
│
├── diag/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   │
│   ├── core/
│   │   ├── check.py
│   │   ├── result.py
│   │   ├── target.py
│   │   ├── registry.py
│   │   └── diagnosis.py
│   │
│   ├── topology/
│   │   ├── inventory.py
│   │   └── dependencies.py
│   │
│   ├── checks/
│   │   ├── __init__.py
│   │   └── network/
│   │       ├── ping.py
│   │       ├── dns.py
│   │       └── http.py
│   │
│   └── execution/
│       └── local.py
│
├── inventory/
│   ├── locations.yaml
│   └── dependencies.yaml
│
├── tests/
│   ├── unit/
│   └── integration/
│
└── docs/
    └── architecture.md
```

This is a starting point, not a rigid requirement.

---

# 11. Check Contract

Every check should expose a consistent interface.

Conceptually:

```python
class Check:
    name: str

    def run(self, target) -> CheckResult:
        ...
```

The result:

```python
class CheckResult:
    status: Status
    check: str
    target: str
    message: str
    details: dict
```

The implementation mechanism should be hidden behind the check.

For example:

```text
PingCheck
    │
    └── local execution
          │
          └── ping command
```

while a future:

```text
FortigateIPSecCheck
    │
    └── Fortigate API
```

can use a completely different mechanism while returning the same result model.

---

# 12. Diagnosis

A diagnosis is not a check.

A diagnosis orchestrates multiple checks based on:

* topology
* dependencies
* check applicability
* previous results

Conceptually:

```text
Diagnosis
    │
    ├── discover target
    ├── resolve dependencies
    ├── execute checks
    ├── evaluate results
    ├── identify failures
    ├── identify affected components
    └── produce summary
```

Example output:

```text
Hospital Castro Rendón
======================

Network
  DNS ............. OK
  Internet ........ OK
  IPSEC ........... CRITICAL

Imaging
  PACS ............ SKIPPED
  DICOM ........... SKIPPED

Root cause candidate:
  network/ipsec

Affected components:
  imaging/pacs
  imaging/dicom
```

The MVP does not need sophisticated root-cause analysis or AI.

Simple dependency propagation is sufficient.

---

# 13. CLI Design

Use a Python CLI framework such as Typer.

Commands:

```text
diag locations
diag systems <location>
diag checks <target>
diag check <target>
diag diagnose <location>
```

Future commands may include:

```text
diag actions
diag action <target>
diag topology
diag graph
diag history
```

The CLI must not contain diagnostic business logic.

It should invoke the domain/application layer.

---

# 14. Configuration

Use YAML for human-maintained topology.

Do not introduce a database in the MVP.

Credentials must NOT be stored in inventory YAML.

Future credential providers may include:

```text
environment variables
AWS Secrets Manager
Vault
Kubernetes Secrets
OS credential stores
```

For now, checks that require credentials can be stubbed or omitted.

---

# 15. Future Telegram Architecture

Telegram should eventually be another frontend.

```text
                  ┌──────────────┐
                  │     CLI      │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │ Application  │
                  │    Layer     │
                  └──────┬───────┘
                         │
              ┌──────────▼──────────┐
              │ Diagnostic Engine   │
              └─────────────────────┘
                         ▲
                         │
                  ┌──────┴───────┐
                  │   Telegram   │
                  └──────────────┘
```

Telegram must never duplicate check or action implementations.

---

# 16. Future Remote Agent

For sites where inbound connectivity is unavailable, a future architecture may use an outbound-connected site agent.

```text
Central
   │
   │ outbound/mTLS
   ▼
Site Agent
   │
   ├── Linux
   ├── Windows
   └── Network devices
```

This should be considered only after the local MVP proves the domain model.

---

# 17. Design Principles

1. Keep checks small.
2. Keep actions separate from checks.
3. Separate topology from execution.
4. Separate hierarchy from dependencies.
5. Normalize check results.
6. Make diagnosis dependency-aware.
7. Keep the CLI thin.
8. Avoid premature infrastructure.
9. Do not introduce Ansible without a concrete use case.
10. Do not duplicate business logic between interfaces.
11. Make future remote execution possible.
12. Keep every operation observable and eventually auditable.
13. Prefer explicit configuration over hidden conventions.
14. Build incrementally with working examples.

---

# 18. First Milestone

The first milestone is considered complete when the following works from a cloned repository:

```bash
pip install -e .

diag locations

diag systems hospital-castro-rendon

diag checks hospital-castro-rendon

diag check hospital-castro-rendon/network/dns

diag check hospital-castro-rendon/network/internet

diag diagnose hospital-castro-rendon
```

The implementation should use a small example topology and real local commands for the first checks.

The project should have unit tests for:

* inventory loading
* dependency resolution
* check result normalization
* check registry
* diagnosis orchestration

The goal of the first milestone is to validate the **domain model and execution flow**, not to build a production platform.
