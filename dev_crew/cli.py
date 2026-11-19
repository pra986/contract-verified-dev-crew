"""Runnable CLI demo entrypoint for Contract-Verified Dev Crew."""

from __future__ import annotations

import argparse
import importlib
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from .engine import ContractVerifiedDevCrew
from .models import InterfaceContract


def run_demo(sandbox_root: str | None = None) -> int:
    """Execute a self-contained contract-verified build and acceptance run."""
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(sandbox_root) if sandbox_root else Path(tmp)
        crew = ContractVerifiedDevCrew(base_dir)
        run = crew.create_run("demo-ledger-001")

        contract = InterfaceContract(
            module_name="backend",
            class_name="LedgerService",
            methods={
                "record_entry": ["account", "amount"],
                "get_balance": ["account"],
            },
        )

        crew.safe_write(
            run,
            "backend.py",
            (
                "class LedgerService:\n"
                "    def __init__(self):\n"
                "        self._balances = {}\n\n"
                "    def record_entry(self, account, amount):\n"
                "        self._balances[account] = self._balances.get(account, 0) + amount\n"
                "        return self._balances[account]\n\n"
                "    def get_balance(self, account):\n"
                "        return self._balances.get(account, 0)\n"
            ),
        )
        crew.safe_write(
            run,
            "frontend.py",
            (
                "from backend import LedgerService\n\n"
                "def main():\n"
                "    svc = LedgerService()\n"
                "    svc.record_entry('cash', 250)\n"
                "    return svc.get_balance('cash')\n"
            ),
        )

        def acceptance_tests(sandbox: Path) -> tuple[bool, list[str]]:
            mod = importlib.import_module("backend")
            importlib.reload(mod)
            svc = mod.LedgerService()
            svc.record_entry("cash", 100)
            svc.record_entry("cash", 50)
            if svc.get_balance("cash") != 150:
                return False, ["Expected cash balance 150"]
            return True, []

        verdict = crew.evaluate_run(
            run=run,
            contract=contract,
            required_files=["backend.py", "frontend.py"],
            acceptance_fn=acceptance_tests,
        )
        print(json.dumps(asdict(verdict), indent=2))
        return 0 if verdict.passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Contract-Verified Dev Crew CLI")
    parser.add_argument("--sandbox-dir", default=None, help="Optional sandbox root")
    args = parser.parse_args()
    raise SystemExit(run_demo(args.sandbox_dir))


if __name__ == "__main__":
    main()
