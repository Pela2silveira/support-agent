You are a senior Python software architect and engineer.

Create the initial MVP scaffold for a project called `diagnostic-platform`.

The project is a reusable operational diagnostics and remediation framework for distributed infrastructure and healthcare systems.

The detailed architecture is described in `docs/architecture.md`. Read and follow that document.

## Primary goal

Build the smallest working implementation that validates the following architecture:

```text
CLI
 │
 ▼
Application / Domain Layer
 │
 ├── Inventory
 ├── Dependency Graph
 ├── Check Registry
 ├── Checks
 └── Diagnosis
```

Do NOT build Telegram, REST APIs, Ansible, remote agents, databases, authentication, RBAC, Kubernetes, or cloud infrastructure yet.

The MVP must run locally from a cloned Git repository.

---

## Technology

Use:

* Python 3.12+
* Typer for the CLI
* PyYAML for inventory
* pytest for tests
* standard Python libraries where possible
* type hints throughout the code
* `pyproject.toml` for project configuration

Keep dependencies minimal.

Use a clean package structure.

---

## Required repository structure

Create:

```text
diagnostic-platform/
│
├── README.md
├── pyproject.toml
│
├── docs/
│   └── architecture.md
│
├── diag/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── check.py
│   │   ├── result.py
│   │   ├── target.py
│   │   ├── registry.py
│   │   └── diagnosis.py
│   │
│   ├── topology/
│   │   ├── __init__.py
│   │   ├── inventory.py
│   │   └── dependencies.py
│   │
│   ├── checks/
│   │   ├── __init__.py
│   │   └── network/
│   │       ├── __init__.py
│   │       ├── ping.py
│   │       ├── dns.py
│   │       └── http.py
│   │
│   └── execution/
│       ├── __init__.py
│       └── local.py
│
├── inventory/
│   ├── locations.yaml
│   └── dependencies.yaml
│
└── tests/
    ├── unit/
    │   ├── test_inventory.py
    │   ├── test_dependencies.py
    │   ├── test_registry.py
    │   └── test_checks.py
    │
    └── integration/
        └── test_cli.py
```

You may adjust the structure slightly if there is a strong technical reason, but keep the architecture simple.

---

# Domain Model

Implement the following concepts.

## Target

A target identifies a resource using:

```text
location/system/service/component
```

Not every level needs to exist.

Examples:

```text
hospital-castro-rendon
hospital-castro-rendon/network
hospital-castro-rendon/network/dns
hospital-castro-rendon/network/ipsec/remote
```

Use a structured target representation rather than passing arbitrary strings throughout the application.

---

## Check

Create a check abstraction.

Conceptually:

```python
class Check:
    name: str

    def run(self, target) -> CheckResult:
        ...
```

Do not over-engineer the interface.

---

## CheckResult

Create a normalized result model.

Statuses:

```text
OK
WARNING
CRITICAL
UNKNOWN
SKIPPED
```

The result should contain at least:

```text
status
check
target
message
details
```

Prefer a dataclass or another simple typed model.

---

# Check Registry

Implement a registry that maps check names to implementations.

For example:

```text
network/ping
network/dns
network/http
```

The registry should allow the application layer to resolve a check without hard-coding the implementation in the CLI.

Avoid magic global state where possible.

---

# Local Execution

Implement a minimal local execution abstraction.

It should allow checks to execute local commands without embedding subprocess management logic in every check.

For example:

```python
executor.run(...)
```

Handle:

* command execution
* return code
* stdout
* stderr
* timeout

Do not build SSH, WinRM, Ansible, or remote execution yet.

---

# Checks

Implement three real checks.

## 1. Ping

Example:

```text
network/ping
```

Use the local system ping command.

The target should provide a hostname or IP address.

Return:

```text
OK
```

when the command succeeds.

Return:

```text
CRITICAL
```

when it fails.

Handle command-not-found and timeout as `UNKNOWN` or an appropriate failure state.

Do not assume Linux-specific behavior where avoidable.

---

## 2. DNS

Implement:

```text
network/dns
```

Use a simple system resolver mechanism or an appropriate portable approach.

The check should validate that the configured hostname can be resolved.

---

## 3. HTTP

Implement:

```text
network/http
```

Use Python's standard HTTP libraries if practical.

Validate that an HTTP/HTTPS endpoint can be reached.

Return useful details such as:

```text
HTTP status code
response time
```

Avoid introducing a large HTTP dependency unless necessary.

---

# Inventory

Implement YAML inventory loading.

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
                host: 8.8.8.8

          dns:
            components:
              resolver:
                host: example.com

          portal:
            components:
              health:
                url: https://example.com
```

The exact example may be adjusted so that the checks can actually run locally.

The inventory loader must validate malformed configuration and produce useful errors.

---

# Dependencies

Implement dependency loading from:

```text
inventory/dependencies.yaml
```

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

Implement enough dependency logic to:

1. resolve direct dependencies
2. determine affected descendants
3. avoid checking dependent components when a required dependency has already failed

Do not implement sophisticated graph algorithms unless needed.

A simple directed graph is sufficient.

---

# Diagnosis

Implement:

```text
diag diagnose <location>
```

The diagnosis engine should:

1. Load the location.
2. Determine applicable checks.
3. Execute checks.
4. Evaluate dependency results.
5. Skip checks whose dependencies are already known to be unavailable.
6. Produce a human-readable summary.

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

The first implementation can use explicit check configuration in the inventory.

Do not attempt AI-based root cause analysis.

---

# CLI

Implement:

```bash
diag locations
```

```bash
diag systems <location>
```

```bash
diag checks <target>
```

```bash
diag check <target>
```

```bash
diag diagnose <location>
```

The CLI should be thin.

Do not put inventory parsing, subprocess execution, dependency resolution, or diagnostic business logic directly in CLI commands.

---

# CLI usability

Commands should provide useful error messages.

Examples:

```text
Location not found: hospital-foo
```

```text
Unknown check: network/foo
```

```text
Invalid target: hospital-x/network
```

Exit codes should eventually be automation-friendly.

At minimum:

* 0 for successful command execution
* non-zero when a diagnostic command has a CRITICAL result or an operational error

Keep the distinction between:

1. command execution failure
2. diagnostic result being CRITICAL

as clear as possible.

---

# Testing

Write meaningful pytest tests.

At minimum test:

## Inventory

* valid YAML
* invalid YAML
* missing location
* target resolution

## Dependencies

* direct dependency
* transitive dependency
* affected descendants
* unknown dependency

## Registry

* registration
* lookup
* unknown check

## Check results

* OK
* CRITICAL
* UNKNOWN
* SKIPPED

## CLI

Test representative commands.

Avoid tests that depend on external Internet connectivity.

Mock external command execution where appropriate.

---

# README

Create a concise README containing:

1. Project purpose
2. Architecture overview
3. Installation
4. Example commands
5. Example inventory
6. How to add a new check
7. Current MVP limitations
8. Future roadmap

The README should make it clear that this is an evolving framework.

---

# Important architectural constraints

Do NOT:

* create a database
* create a REST API
* create a Telegram bot
* add Ansible
* add Docker/Kubernetes deployment
* add cloud resources
* add authentication
* add RBAC
* add a plugin marketplace
* implement automatic remediation
* introduce unnecessary abstractions

Do NOT build speculative features.

The objective is to validate the core model:

```text
Inventory
   +
Dependencies
   +
Checks
   +
Execution
   +
Diagnosis
   +
CLI
```

---

# Future compatibility

Keep the architecture extensible enough to eventually support:

```text
CLI
Telegram
REST API

local execution
SSH
WinRM
Fortigate API
Ansible
site agent
```

But do not implement these now.

A future Telegram bot must call the same application/domain layer as the CLI.

A future remote executor must implement the execution abstraction rather than modifying checks.

A future remediation action must be separate from read-only checks.

---

# Development approach

Work incrementally.

First create:

1. project scaffold
2. domain models
3. inventory loader
4. local executor
5. check registry
6. ping check
7. DNS check
8. HTTP check
9. dependency graph
10. diagnosis engine
11. CLI
12. tests
13. README

After each meaningful step, run the test suite.

At the end, run the CLI against the example inventory and demonstrate:

```bash
diag locations

diag systems hospital-castro-rendon

diag checks hospital-castro-rendon

diag check hospital-castro-rendon/network/dns

diag check hospital-castro-rendon/network/internet

diag diagnose hospital-castro-rendon
```

The final implementation must be runnable with:

```bash
pip install -e .
```

and expose:

```bash
diag
```

as a console script.

Before finishing, verify that all tests pass and that the documented commands actually work.
