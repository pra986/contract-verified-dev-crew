"""Pytest suite for ContractVerifiedDevCrew."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from dev_crew import ContractVerifiedDevCrew, InterfaceContract
from dev_crew.engine import SandboxPathError


def _sample_contract() -> InterfaceContract:
    return InterfaceContract(
        module_name="backend",
        class_name="LedgerService",
        methods={
            "record_entry": ["account", "amount"],
            "get_balance": ["account"],
        },
    )


def test_sandbox_path_traversal_blocked(tmp_path: Path) -> None:
    crew = ContractVerifiedDevCrew(tmp_path)
    run = crew.create_run("run-traversal")

    with pytest.raises(SandboxPathError):
        crew.safe_write(run, "../escape.py", "print('escaped')")


def test_backend_defect_detected_by_independent_acceptance_tests(tmp_path: Path) -> None:
    crew = ContractVerifiedDevCrew(tmp_path)
    run = crew.create_run("run-defect")
    contract = _sample_contract()

    crew.safe_write(
        run,
        "backend.py",
        (
            "class LedgerService:\n"
            "    def record_entry(self, account, amount):\n"
            "        return 0  # defect: ignores entry\n"
            "    def get_balance(self, account):\n"
            "        return 0\n"
        ),
    )
    crew.safe_write(
        run,
        "frontend.py",
        (
            "def run_ui(svc):\n"
            "    svc.record_entry('cash', 100)\n"
            "    return svc.get_balance('cash')\n"
        ),
    )

    def independent_acceptance(sandbox: Path) -> tuple[bool, list[str]]:
        mod = importlib.import_module("backend")
        importlib.reload(mod)
        svc = mod.LedgerService()
        svc.record_entry("cash", 100)
        if svc.get_balance("cash") != 100:
            return False, ["Backend failed to persist recorded entry"]
        return True, []

    verdict = crew.evaluate_run(
        run=run,
        contract=contract,
        required_files=["backend.py", "frontend.py"],
        acceptance_fn=independent_acceptance,
    )
    assert verdict.contract_matched is True
    assert verdict.acceptance_tests_passed is False
    assert verdict.passed is False


def test_missing_executable_artifact_fails_despite_llm_summary(tmp_path: Path) -> None:
    crew = ContractVerifiedDevCrew(tmp_path)
    run = crew.create_run("run-missing")
    run.llm_summary = "Successfully generated backend.py and frontend.py!"

    crew.safe_write(run, "backend.py", "class LedgerService:\n    pass\n")

    verdict = crew.evaluate_run(
        run=run,
        contract=_sample_contract(),
        required_files=["backend.py", "frontend.py"],
    )
    assert verdict.artifacts_verified is False
    assert verdict.passed is False
    assert any("frontend.py" in err for err in verdict.errors)


def test_frontend_to_backend_contract_signature_matching(tmp_path: Path) -> None:
    crew = ContractVerifiedDevCrew(tmp_path)
    run = crew.create_run("run-contract")
    contract = _sample_contract()

    crew.safe_write(
        run,
        "backend.py",
        (
            "class LedgerService:\n"
            "    def record_entry(self, account, amount):\n"
            "        return amount\n"
            "    def get_balance(self, account):\n"
            "        return 0\n"
        ),
    )
    crew.safe_write(
        run,
        "frontend.py",
        (
            "def run_ui(svc):\n"
            "    svc.record_entry('cash')  # missing amount arg\n"
        ),
    )

    verdict = crew.evaluate_run(
        run=run,
        contract=contract,
        required_files=["backend.py", "frontend.py"],
    )
    assert verdict.contract_matched is False
    assert verdict.passed is False
    assert len(verdict.mismatches) == 1
