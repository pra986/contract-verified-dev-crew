# Contract-Verified Dev Crew (Project 21)

**A5: Agentic Track — Sequential 4-Agent CrewAI Engineering Team** with explicit interface contracts, per-run isolated sandbox directories, path-traversal guards, and independent human-authored acceptance tests.

## Overview

Autonomous multi-agent code generation frequently fails in production due to three systemic failure modes:
1. **Interface drift** between backend modules and frontend consumers.
2. **Unsafe filesystem writes** (path traversal or cross-run contamination).
3. **Self-grading bias** where LLM-generated summaries or LLM-authored unit tests mask missing artifacts or broken behavior.

`contract-verified-dev-crew` wraps a sequential 4-agent CrewAI engineering workflow (`Engineering Lead -> Backend Engineer -> Frontend Engineer -> Test Engineer`) with deterministic verification gates.

## Architecture

- **Agent 1 — Engineering Lead**: Produces the `InterfaceContract` specifying module name, class/function signatures, and boundary invariants.
- **Agent 2 — Backend Engineer**: Implements the backend module inside the isolated per-run sandbox directory.
- **Agent 3 — Frontend Engineer**: Builds the frontend/UI adapter strictly bound to the verified backend signatures.
- **Agent 4 — Test Engineer**: Generates agent unit tests, followed by an **independent human-authored acceptance suite** that cannot be bypassed by LLM summaries.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system diagram and gate specifications.

## 6-Stage Workflow

1. **Contract Specification**: Define `InterfaceContract` with expected module path, required class/function signatures, and invariants.
2. **Isolated Sandbox Provisioning**: Allocate a unique per-run workspace (`SandboxBuildRun`) with strict path-traversal canonicalization.
3. **Backend Implementation**: Write and validate the backend artifact within the sandbox; fail immediately if the executable file is missing even if an LLM summary claims completion.
4. **Contract Signature Verification**: Parse AST / inspect signatures to ensure backend exports match `InterfaceContract`.
5. **Frontend Binding**: Generate frontend code and verify its calls match the backend contract signatures.
6. **Independent Acceptance Gate**: Execute human-authored acceptance tests in the isolated sandbox and emit `AcceptanceVerdict`.

## Data Contract

- `InterfaceContract`: Defines `module_name`, `class_name`, `required_methods` (mapping method names to expected parameter lists), and `description`.
- `SandboxBuildRun`: Tracks `run_id`, `sandbox_dir`, `written_files`, and `created_at` with enforced root confinement.
- `AcceptanceVerdict`: Records `passed`, `contract_matched`, `artifacts_present`, `acceptance_passed`, `errors`, and `summary`.

## Production Controls

- **Per-Run Isolated Sandbox Directories**: Each build executes in an ephemeral `run_<id>` directory; no shared mutable workspace.
- **Path-Traversal Guards**: All file writes resolve `Path.resolve()` against `sandbox_dir.resolve()` and reject `..`, absolute paths, or symlink escapes.
- **Executable Artifact Verification**: Missing `.py` artifacts cause deterministic failure regardless of LLM output summaries.
- **Backend-to-Frontend Signature Checks**: AST-based signature matching ensures frontend calls align with backend definitions.
- **Independent Acceptance Testing**: Runs human-authored `pytest` acceptance suites against the generated module to catch real logic defects.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Run CLI Demo

```bash
python -m dev_crew.cli
```

### Run Test Suite

```bash
pytest -v
```

## Attribution

Inspired by and adapted with pinned attribution from [ed-donner/agents](https://github.com/ed-donner/agents) (`3_crewai/reference/engineering_team`).
