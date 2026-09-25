# AGENTS.md

## Project

`diagnostic-platform` is an operational diagnostics and remediation framework for distributed infrastructure and healthcare systems.

The project provides:

* Infrastructure health checks
* Application diagnostics
* Dependency-aware diagnosis
* Operational actions/remediation
* A reusable execution layer

The long-term goal is to expose the same capabilities through multiple interfaces, initially:

* CLI
* Telegram bot

The current MVP is CLI-only.

---

# 1. Primary Engineering Principle

**Build the smallest useful thing first.**

This project is intentionally evolving incrementally.

Do not introduce infrastructure, abstractions, dependencies, or technologies unless they solve a concrete current requirement.

Prefer:

```text
simple
explicit
testable
extensible
```

over:

```text
generic
abstract
distributed
prematurely scalable
```

---

# 2. Read the Architecture First

Before making architectural changes, read:

```text
docs/architecture.md
```

The architecture document describes the intended domain model and current MVP scope.

If the implementation and architecture document disagree:

1. Determine whether the implementation represents an intentional evolution.
2. If it does, update the architecture documentation.
3. Do not silently introduce architectural changes.

---

# 3. MVP Scope

The current MVP consists of:

```text
Inventory
    +
Targets
    +
Checks
    +
Execution
    +
Dependencies
    +
Diagnosis
    +
CLI
```

The MVP should run locally from a cloned repository.

Current technologies:

* Python 3.12+
* Typer
* PyYAML
* pytest
* Python standard library whenever practical

---

# 4. Explicit Non-Goals

Do not introduce the following unless the project requirements explicitly change:

* Telegram
* REST API
* Web UI
* Database
* Kubernetes
* Docker deployment
* Cloud infrastructure
* Ansible
* SSH orchestration
* WinRM
* Remote agents
* Authentication
* RBAC
* Automatic remediation
* Message queues
* Event-driven architecture
* Microservices

These are potential future capabilities, not MVP requirements.

---

# 5. Architecture

The core architecture is:

```text
CLI
 │
 ▼
Application / Domain Layer
 │
 ├── Inventory
 ├── Targets
 ├── Checks
 ├── Dependencies
 ├── Diagnosis
 └── Execution
```

The CLI must remain a thin interface.

Do not place business logic inside CLI commands.

---

# 6. Domain Model

The infrastructure hierarchy is:

```text
Location
└── System
    └── Service
        └── Component
```

Examples:

```text
hospital-castro-rendon
hospital-castro-rendon/network
hospital-castro-rendon/network/ipsec
hospital-castro-rendon/network/ipsec/remote
```

Hierarchy represents what exists.

Dependencies represent how resources depend on one another.

Do not attempt to encode all dependencies into the hierarchy.

---

# 7. Dependency Graph

Dependencies are directional.

Example:

```text
PACS
  │
  ▼
IPSEC
  │
  ▼
Central Network
```

If a dependency fails, dependent checks may be skipped.

Example:

```text
IPSEC ........ CRITICAL

PACS ......... SKIPPED
DICOM ........ SKIPPED
```

Do not claim a dependent component is healthy simply because its direct check was not executed.

Use:

```text
SKIPPED
```

when appropriate.

---

# 8. Checks

Checks are read-only operations.

Examples:

```text
network/ping
network/dns
network/http
network/tcp

ipsec/status
ipsec/connectivity

application/api-health
```

Checks must:

* Be small
* Have a single responsibility
* Return normalized `CheckResult`
* Avoid embedding orchestration logic
* Be independently testable

A check should not know how a Telegram message is formatted.

A check should not know about CLI arguments.

A check should not know about dependency traversal.

---

# 9. Check Results

Use normalized statuses:

```text
OK
WARNING
CRITICAL
UNKNOWN
SKIPPED
```

A result should contain enough information for different future interfaces.

Conceptually:

```python
CheckResult(
    status=Status.OK,
    check="network/dns",
    target="hospital-castro-rendon/network/dns",
    message="DNS resolution successful",
    details={...},
)
```

Do not make the result model CLI-specific.

Future interfaces such as Telegram or REST must be able to consume the same result.

---

# 10. Actions

Actions are different from checks.

Checks:

```text
read-only
```

Actions:

```text
state-changing
```

Examples of future actions:

```text
ipsec/restart
service/restart
application/retry
```

Do not implement automatic remediation unless explicitly requested.

Do not turn a check into an action.

For example:

```text
BAD:

ipsec/status
  if down:
      restart tunnel
```

The correct model is:

```text
ipsec/status

ipsec/restart
```

with orchestration deciding whether an action should be executed.

---

# 11. Execution Layer

Checks should not directly depend on subprocess implementation details.

Use an execution abstraction.

Current MVP:

```text
LocalExecutor
```

Future possibilities:

```text
SSHExecutor
WinRMExecutor
FortigateExecutor
AnsibleExecutor
AgentExecutor
```

Do not implement future executors until there is a real use case.

---

# 12. External Commands

When invoking commands such as:

```text
ping
dig
curl
```

use safe subprocess handling.

Prefer:

```python
subprocess.run(
    [...],
    capture_output=True,
    text=True,
    timeout=...
)
```

over:

```python
subprocess.run("some command " + user_input, shell=True)
```

Avoid `shell=True` unless there is a documented reason.

Never interpolate untrusted user input into shell commands.

---

# 13. Inventory

Inventory is configuration, not application logic.

Use YAML.

Example:

```yaml
locations:
  hospital-castro-rendon:
    systems:
      network:
        services:
          ipsec:
            components:
              remote:
                type: fortigate
                host: 10.20.0.254
```

Do not store secrets in inventory files.

Never commit:

* passwords
* API tokens
* private keys
* certificates containing private material
* Telegram bot tokens
* cloud credentials

Use environment variables or a future secret provider.

---

# 14. Credentials

Credential handling must be separated from topology.

Do not add credentials directly to:

```text
locations.yaml
dependencies.yaml
```

Bad:

```yaml
password: super-secret
api_key: abc123
```

Good:

```yaml
credential_ref: fortigate-prod
```

with the actual implementation deferred until required.

---

# 15. Error Handling

Distinguish between:

### Diagnostic failure

Example:

```text
PING → CRITICAL
```

The system executed correctly and discovered an unhealthy target.

### Execution failure

Example:

```text
ping command not found
```

The diagnostic mechanism itself could not run.

### Configuration error

Example:

```text
Unknown location
```

The inventory/configuration is invalid.

Do not collapse all three into the same error.

---

# 16. CLI

The CLI should be thin.

Expected commands include:

```bash
diag locations

diag systems <location>

diag checks <target>

diag check <target>

diag diagnose <location>
```

Business logic should live below the CLI layer.

Do not implement diagnostic algorithms directly in Typer command functions.

---

# 17. CLI Output

Human-readable output is important.

Prefer:

```text
Hospital Castro Rendón
======================

Network
  DNS ............. OK
  Internet ........ OK
  IPSEC ........... CRITICAL
```

over dumping raw Python objects.

However, keep domain results structured internally.

Future machine-readable output may be added:

```bash
diag check ... --json
```

but this is not required for the initial MVP.

---

# 18. Testing

Every new domain feature should include tests.

Use pytest.

Tests should prefer deterministic behavior.

Do not make unit
