"""Audit the repo for reviewer reproduction readiness."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OPT = REPO_ROOT / "strategy_model" / "optimization"

REQUIRED_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "PYTHON_REPRODUCTION_CHEAT_SHEET.md",
    REPO_ROOT / "RESEARCH_MEETING_MEMO_ANSWER_PACKET_REPO_ALIGNED.md",
    OPT / "README.md",
    OPT / "B6_FINAL_README.md",
    OPT / "B6_CANONICAL_RUNNER.py",
    OPT / "B6_FINAL_VALIDATE.py",
    OPT / "CHRIS_MEMO_CHECKLIST.py",
    OPT / "REPRODUCE_REVIEWER_RESULTS.py",
    OPT / "NORA_PARAMETERS_AND_CONSTRAINTS.py",
    OPT / "rolling_horizon_gurobi_dispatch.py",
    OPT / "forecast_backtest_rolling_horizons.py",
    OPT / "run_uncertainty_aware_dispatch.py",
    OPT / "b6_final_results" / "David_B6_run_summary.csv",
    OPT / "b6_final_results" / "David_B6_QA_summary.csv",
    OPT / "b6_final_results" / "David_B6_frozen_config.json",
]


def load_validator():
    validator_path = OPT / "B6_FINAL_VALIDATE.py"
    spec = importlib.util.spec_from_file_location("b6_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    missing = [str(path) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        raise SystemExit("Missing required files:\n" + "\n".join(missing))

    validator = load_validator()
    b6_report = validator.validate(OPT / "b6_final_results")

    py_files = [
        OPT / "B6_CANONICAL_RUNNER.py",
        OPT / "B6_FINAL_VALIDATE.py",
        OPT / "CHRIS_MEMO_CHECKLIST.py",
        OPT / "REPRODUCE_REVIEWER_RESULTS.py",
        OPT / "NORA_PARAMETERS_AND_CONSTRAINTS.py",
        OPT / "forecast_backtest_rolling_horizons.py",
        OPT / "run_uncertainty_aware_dispatch.py",
        OPT / "run_nora_matching_forecast_horizons.py",
        OPT / "run_best_forecast_dispatch_search.py",
    ]
    subprocess.run([sys.executable, "-m", "py_compile", *map(str, py_files)], check=True)

    text_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "PYTHON_REPRODUCTION_CHEAT_SHEET.md",
        OPT / "README.md",
        OPT / "B6_FINAL_README.md",
    ]
    banned_phrase_hits = []
    banned_phrase = "plain" + " " + "english"
    for path in text_files:
        text = path.read_text(errors="ignore").lower()
        if banned_phrase in text:
            banned_phrase_hits.append(str(path))
    if banned_phrase_hits:
        raise SystemExit("Remove banned phrase from:\n" + "\n".join(banned_phrase_hits))

    result = {
        "status": "PASS",
        "repo_root": str(REPO_ROOT),
        "b6_status": b6_report["status"],
        "required_file_count": len(REQUIRED_FILES),
        "compiled_python_count": len(py_files),
        "b6_result_dir": str(OPT / "b6_final_results"),
        "reviewer_start_file": str(REPO_ROOT / "PYTHON_REPRODUCTION_CHEAT_SHEET.md"),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
