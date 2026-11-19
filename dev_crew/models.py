"""Data models for contract-verified development runs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InterfaceContract:
    """Explicit backend-to-frontend interface contract."""

    module_name: str
    class_name: str
    methods: dict[str, list[str]]


@dataclass
class SandboxBuildRun:
    """Represents an isolated per-run sandbox build."""

    run_id: str
    sandbox_dir: str
    backend_path: str
    frontend_path: str
    llm_summary: str = ""
    created_files: list[str] = field(default_factory=list)


@dataclass
class AcceptanceVerdict:
    """Verification result from contract, artifact, and acceptance checks."""

    passed: bool
    run_id: str
    contract_matched: bool
    artifacts_verified: bool
    acceptance_tests_passed: bool
    mismatches: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
