# System Architecture

## 1. Sequential 4-Agent CrewAI Pipeline

`ContractVerifiedDevCrew` orchestrates four specialized agents in a strict sequential process:

1. **Engineering Lead**: Translates requirements into a typed `InterfaceContract` (`module_name`, `class_name`, `required_methods`).
2. **Backend Engineer**: Writes the target Python module inside an isolated `SandboxBuildRun` directory.
3. **Frontend Engineer**: Generates a UI/adapter module whose method calls are statically verified against the backend's actual signatures.
4. **Test Engineer**: Produces unit tests, followed by an independent human-authored acceptance test execution gate.

## 2. Deterministic Security & Verification Gates

- **Per-Run Sandbox Isolation**: Every run creates a dedicated directory (`<sandbox_root>/<run_id>`) so artifacts never collide across concurrent or sequential builds.
- **Path-Traversal Guard (`safe_write`)**: Any relative path containing `..`, absolute prefixes, or resolving outside `sandbox_dir.resolve()` raises `SandboxSecurityError`.
- **Executable Artifact Check**: Even if an LLM agent emits a glowing completion summary, `AcceptanceVerdict` fails if the expected `.py` files do not exist on disk.
- **AST Interface Signature Verification**: Parses both backend and frontend Python ASTs to verify that every required method exists with matching parameter names/arities and that frontend calls conform to the backend contract.
- **Independent Acceptance Execution**: Runs human-authored `pytest` cases against the sandboxed module in a subprocess with `PYTHONPATH` scoped to the sandbox.
