"""Checklist for the July 16 research memo.

Run this before a meeting or review.  It prints the exact repo files that answer
the items Chris asked to see: canonical benchmark, baseline, scenario status,
recourse logic, B6 QA, and decision points.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OPT = REPO_ROOT / "strategy_model" / "optimization"

SECTIONS = {
    "SECTION 3 - RESULT RECONCILIATION": [
        ("Frozen B6 summary", OPT / "b6_final_results" / "David_B6_run_summary.csv"),
        ("Frozen B6 QA", OPT / "b6_final_results" / "David_B6_QA_summary.csv"),
        ("Frozen B6 config", OPT / "b6_final_results" / "David_B6_frozen_config.json"),
        ("Historical deterministic forecast summary", OPT / "rolling_horizon_gurobi_results" / "forecast_backtest_2014_2023" / "forecast_dispatch_summary.csv"),
        ("Historical scenario summary", OPT / "uncertainty_aware_dispatch_results" / "uncertainty_aware_summary.csv"),
        ("Historical scenario final table", OPT / "uncertainty_aware_dispatch_results" / "final_breakthrough_summary.csv"),
    ],
    "SECTION 5 - METHODS AND RECOURSE": [
        ("Core Gurobi constraint model", OPT / "rolling_horizon_gurobi_dispatch.py"),
        ("B6 canonical runner", OPT / "B6_CANONICAL_RUNNER.py"),
        ("B6 validator", OPT / "B6_FINAL_VALIDATE.py"),
        ("Deterministic forecast runner", OPT / "forecast_backtest_rolling_horizons.py"),
        ("Scenario runner", OPT / "run_uncertainty_aware_dispatch.py"),
        ("Nora parameters and constraints", OPT / "NORA_PARAMETERS_AND_CONSTRAINTS.py"),
    ],
    "SECTION 6 - SCREEN SHARE PATHS": [
        ("One command map", OPT / "REPRODUCE_REVIEWER_RESULTS.py"),
        ("Repo cheat sheet", REPO_ROOT / "PYTHON_REPRODUCTION_CHEAT_SHEET.md"),
        ("Optimization README", OPT / "README.md"),
        ("B6 README", OPT / "B6_FINAL_README.md"),
    ],
    "SECTION 8 - DECISION RECORD": [
        ("Canonical frozen benchmark", OPT / "B6_CANONICAL_RUNNER.py"),
        ("Canonical frozen outputs", OPT / "b6_final_results"),
        ("Research history deterministic outputs", OPT / "rolling_horizon_gurobi_results" / "forecast_backtest_2014_2023"),
        ("Research history scenario outputs", OPT / "uncertainty_aware_dispatch_results"),
    ],
}


DECISIONS = [
    "B6 is the canonical reviewer-safe benchmark because it has one frozen configuration and a validator.",
    "Historical deterministic and scenario results are useful research history, but should not be mixed with B6 unless rerun under B6 rules.",
    "The B6 rulebook is: raw PYR_PYRON1 LMP, 2020 only, 249 MW grid cap, RTE 0.55, wind-only charging, 48 h causal planning, 24 h execution, 20% min/initial/final SoC, planned-direct curtailment.",
    "Scenario dispatch is promising, but any final paper claim should state whether it was rerun under the same frozen storage and recourse policy.",
]


def exists_label(path: Path) -> str:
    return "FOUND" if path.exists() else "MISSING"


def main() -> None:
    print("CHRIS MEMO CHECKLIST")
    print(f"Repo root: {REPO_ROOT}")
    print()
    for section, rows in SECTIONS.items():
        print(section)
        for label, path in rows:
            print(f"  {exists_label(path):7} | {label}: {path}")
        print()
    print("DECISION POINTS")
    for number, decision in enumerate(DECISIONS, start=1):
        print(f"  {number}. {decision}")
    print()
    print("FAST VALIDATION COMMAND")
    print(f"  ./venv/bin/python {OPT / 'B6_FINAL_VALIDATE.py'}")


if __name__ == "__main__":
    main()
