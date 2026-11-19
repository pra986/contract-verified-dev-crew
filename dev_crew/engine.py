"""Contract-verified development crew execution engine."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Callable

from .models import AcceptanceVerdict, InterfaceContract, SandboxBuildRun


class SandboxPathError(ValueError):
    """Raised when a requested artifact path escapes the run sandbox."""


class MissingArtifactError(FileNotFoundError):
    """Raised when a required executable artifact is missing on disk."""


class ContractVerifiedDevCrew:
    """Enforces sandbox isolation, contract signatures, and acceptance tests."""

    def __init__(self, base_sandbox_dir: str | Path) -> None:
        self.base_sandbox_dir = Path(base_sandbox_dir).resolve()
        self.base_sandbox_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self, run_id: str) -> SandboxBuildRun:
        if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
            raise SandboxPathError(f"Invalid run_id: {run_id!r}")
        sandbox_dir = (self.base_sandbox_dir / run_id).resolve()
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        return SandboxBuildRun(
            run_id=run_id,
            sandbox_dir=str(sandbox_dir),
            backend_path=str(sandbox_dir / "backend.py"),
            frontend_path=str(sandbox_dir / "frontend.py"),
        )

    def resolve_sandbox_path(self, run: SandboxBuildRun, relative_path: str) -> Path:
        sandbox_root = Path(run.sandbox_dir).resolve()
        candidate = (sandbox_root / relative_path).resolve()
        if candidate != sandbox_root and not candidate.is_relative_to(sandbox_root):
            raise SandboxPathError(
                f"Path traversal blocked: {relative_path!r} escapes {sandbox_root}"
            )
        return candidate

    def safe_write(self, run: SandboxBuildRun, relative_path: str, content: str) -> Path:
        target = self.resolve_sandbox_path(run, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        if relative_path not in run.created_files:
            run.created_files.append(relative_path)
        return target

    def verify_artifacts(self, run: SandboxBuildRun, required_files: list[str]) -> list[str]:
        errors: list[str] = []
        for rel_path in required_files:
            target = self.resolve_sandbox_path(run, rel_path)
            if not target.is_file() or target.stat().st_size == 0:
                errors.append(f"Missing or empty executable artifact: {rel_path}")
        return errors

    def verify_contract(
        self, run: SandboxBuildRun, contract: InterfaceContract
    ) -> list[str]:
        mismatches: list[str] = []
        backend_file = Path(run.backend_path)
        frontend_file = Path(run.frontend_path)
        if not backend_file.is_file() or not frontend_file.is_file():
            return ["Backend or frontend file missing for contract verification"]

        backend_tree = ast.parse(backend_file.read_text(encoding="utf-8"))
        frontend_tree = ast.parse(frontend_file.read_text(encoding="utf-8"))

        backend_methods = self._extract_class_methods(backend_tree, contract.class_name)
        if backend_methods is None:
            return [f"Backend class {contract.class_name!r} not found"]

        for method_name, expected_params in contract.methods.items():
            actual_params = backend_methods.get(method_name)
            if actual_params is None:
                mismatches.append(f"Backend missing method {method_name!r}")
            elif actual_params != expected_params:
                mismatches.append(
                    f"Backend signature mismatch for {method_name}: "
                    f"expected {expected_params}, got {actual_params}"
                )

        for node in ast.walk(frontend_tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                if method_name in contract.methods:
                    expected_count = len(contract.methods[method_name])
                    actual_count = len(node.args) + len(node.keywords)
                    if actual_count != expected_count:
                        mismatches.append(
                            f"Frontend call to {method_name} passes {actual_count} args, "
                            f"contract requires {expected_count}"
                        )
        return mismatches

    def _extract_class_methods(
        self, tree: ast.Module, class_name: str
    ) -> dict[str, list[str]] | None:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                methods: dict[str, list[str]] = {}
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        params = [a.arg for a in item.args.args if a.arg != "self"]
                        methods[item.name] = params
                return methods
        return None

    def run_acceptance_tests(
        self,
        run: SandboxBuildRun,
        acceptance_fn: Callable[[Path], tuple[bool, list[str]]],
    ) -> tuple[bool, list[str]]:
        sandbox_path = Path(run.sandbox_dir).resolve()
        sys.path.insert(0, str(sandbox_path))
        try:
            return acceptance_fn(sandbox_path)
        finally:
            if str(sandbox_path) in sys.path:
                sys.path.remove(str(sandbox_path))

    def evaluate_run(
        self,
        run: SandboxBuildRun,
        contract: InterfaceContract,
        required_files: list[str],
        acceptance_fn: Callable[[Path], tuple[bool, list[str]]] | None = None,
    ) -> AcceptanceVerdict:
        artifact_errors = self.verify_artifacts(run, required_files)
        artifacts_verified = len(artifact_errors) == 0

        mismatches = self.verify_contract(run, contract) if artifacts_verified else []
        contract_matched = artifacts_verified and len(mismatches) == 0

        acceptance_passed = False
        test_errors: list[str] = []
        if artifacts_verified and contract_matched and acceptance_fn is not None:
            acceptance_passed, test_errors = self.run_acceptance_tests(run, acceptance_fn)
        elif acceptance_fn is None and artifacts_verified and contract_matched:
            acceptance_passed = True

        all_errors = artifact_errors + test_errors
        passed = artifacts_verified and contract_matched and acceptance_passed
        return AcceptanceVerdict(
            passed=passed,
            run_id=run.run_id,
            contract_matched=contract_matched,
            artifacts_verified=artifacts_verified,
            acceptance_tests_passed=acceptance_passed,
            mismatches=mismatches,
            errors=all_errors,
        )
