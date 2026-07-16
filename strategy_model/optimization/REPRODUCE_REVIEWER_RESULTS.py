"""One-file map for reproducing the reviewer-facing results.

The canonical Chris-compatible benchmark is the B6 final package.  It freezes
2020 data, A/B/C architectures, Oracle/Causal workflows, raw realized LMP
revenue, 48-hour causal planning, 24-hour execution, 20% annual SoC, and the
corrected planned-direct curtailment rule.

Older research folders remain in the repo, but they are not the frozen B6
benchmark because some use different storage durations, score definitions, or
exploratory scenario settings.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OPT = REPO_ROOT / "strategy_model" / "optimization"

CANONICAL_COMMANDS: dict[str, list[str]] = {
    "b6_run_all_six": [sys.executable, str(OPT / "B6_CANONICAL_RUNNER.py")],
    "b6_validate": [sys.executable, str(OPT / "B6_FINAL_VALIDATE.py")],
    "repo_audit": [sys.executable, str(OPT / "REPO_REVIEWER_AUDIT.py")],
    "chris_memo_checklist": [sys.executable, str(OPT / "CHRIS_MEMO_CHECKLIST.py")],
    "nora_constraints": [sys.executable, str(OPT / "NORA_PARAMETERS_AND_CONSTRAINTS.py")],
}

RESEARCH_HISTORY_COMMANDS: dict[str, list[str]] = {
    "lower_bound_baseload": [sys.executable, str(OPT / "LOWER_BOUND_BASELOAD.py")],
    "deterministic_forecast": [sys.executable, str(OPT / "PROPOSED_METHOD_1_DETERMINISTIC_RH_MILP.py")],
    "scenario_forecast": [sys.executable, str(OPT / "PROPOSED_METHOD_2_SCENARIO_RH_MILP.py")],
    "upper_bound_oracle": [sys.executable, str(OPT / "UPPER_BOUND_ORACLE.py")],
    "cove_dv": [sys.executable, str(OPT / "COVE_DV_TEACHER_STUDENT.py")],
}

RESULTS = {
    "b6_final_results": OPT / "b6_final_results",
    "power_forecast": REPO_ROOT / "power_model" / "evaluation",
    "nora_match": OPT / "nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp",
    "deterministic_forecast": OPT / "rolling_horizon_gurobi_results" / "forecast_backtest_2014_2023",
    "oracle_horizons": OPT / "rolling_horizon_gurobi_results" / "forecast_backtest_2014_2023",
    "perfect_information_horizon_sweep": OPT / "rolling_horizon_gurobi_results" / "horizon_comparison_full_43y",
    "scenario_forecast": OPT / "uncertainty_aware_dispatch_results",
    "cove_dv": OPT / "cove_dv_results",
    "new_proxy_data": REPO_ROOT / "data" / "newest_pyron_shaped",
}


def print_ladder() -> None:
    print("CANONICAL B6 REPRODUCTION")
    print("1. Run all six B6 cases: b6_run_all_six")
    print("2. Validate all six B6 cases: b6_validate")
    print("3. Audit repo readiness: repo_audit")
    print("4. Show Chris memo checklist: chris_memo_checklist")
    print("5. Show constraint summary: nora_constraints")
    print()
    print("CANONICAL COMMANDS")
    for name, command in CANONICAL_COMMANDS.items():
        print(f"{name}:")
        print("  " + " ".join(command))
    print()
    print("RESEARCH HISTORY COMMANDS")
    print("These are useful for the broader project story, but do not treat them as the frozen B6 packet.")
    for name, command in RESEARCH_HISTORY_COMMANDS.items():
        print(f"{name}:")
        print("  " + " ".join(command))
    print()
    print("RESULT FOLDERS")
    for name, path in RESULTS.items():
        print(f"{name}: {path}")
    print()
    print("To execute one command:")
    print(f"  {sys.executable} {Path(__file__).resolve()} --run b6_validate")
    print("For Chris/reviewer reproduction, run B6 first.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Print or run reviewer reproduction commands.")
    all_commands = {**CANONICAL_COMMANDS, **RESEARCH_HISTORY_COMMANDS}
    parser.add_argument("--run", choices=sorted(all_commands), default=None)
    args = parser.parse_args()
    if args.run is None:
        print_ladder()
        return
    subprocess.run(all_commands[args.run], cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
