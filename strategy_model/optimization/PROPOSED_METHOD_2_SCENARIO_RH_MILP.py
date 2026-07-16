"""Proposed method 2: uncertainty-aware scenario rolling-horizon MILP.

This is the scenario controller:
1. Build a center forecast.
2. Add residual-based wind/price scenarios around that forecast.
3. Force the first-hour storage action to be shared across scenarios.
4. Execute the first hour on realized wind/price.
5. Carry SoC forward and repeat.

The stored seven-scenario result in `uncertainty_aware_dispatch_results/` is
historical.  New reruns from this wrapper go to a separate B6-aligned folder so
older tables are not overwritten silently.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "strategy_model" / "optimization" / "run_uncertainty_aware_dispatch.py"
DEFAULT_OUT = REPO_ROOT / "strategy_model" / "optimization" / "uncertainty_aware_dispatch_results_b6_aligned_rerun"
VARIANTS = [
    "single_recourse",
    "three_scenario_expected",
    "five_scenario_expected",
    "seven_scenario_expected",
    "ten_scenario_expected",
]


def command(out_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--variants",
        *VARIANTS,
        "--nowcast-first-hour",
        "--gate-margin",
        "0.0",
        "--out-dir",
        str(out_dir),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or print the scenario rolling-horizon MILP command.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--max-origins", type=int, default=None, help="Optional quick-test limit.")
    parser.add_argument("--run", action="store_true", help="Actually execute the scenario experiment.")
    args = parser.parse_args()
    cmd = command(Path(args.out_dir))
    if args.max_origins is not None:
        cmd.extend(["--max-origins", str(args.max_origins)])

    print("PROPOSED METHOD 2 / SCENARIO ROLLING-HORIZON MILP COMMAND")
    print(" ".join(cmd))
    print()
    print("New corrected reruns will be saved in:")
    print(DEFAULT_OUT)
    print()
    print("Historical June summaries/figures remain in:")
    print(REPO_ROOT / "strategy_model" / "optimization" / "uncertainty_aware_dispatch_results")
    if args.run:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
