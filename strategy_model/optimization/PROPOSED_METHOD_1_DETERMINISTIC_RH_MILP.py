"""Proposed method 1: deterministic forecast-driven rolling-horizon MILP.

This is the realistic single-forecast controller.  The stored June result in
`forecast_backtest_2014_2023/` is historical.  New reruns from this wrapper go
to a separate B6-aligned folder so older tables are not overwritten silently.

Workflow:
1. Train causal wind/price forecasts on past data.
2. Give those forecasts to Gurobi.
3. Execute only the first day.
4. Carry the battery state forward and replan.
5. Score using what actually happened.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "strategy_model" / "optimization" / "forecast_backtest_rolling_horizons.py"
DEFAULT_OUT = REPO_ROOT / "strategy_model" / "optimization" / "rolling_horizon_gurobi_results" / "forecast_backtest_2014_2023_b6_aligned_rerun"


def command(out_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--skip-oracle",
        "--out-dir",
        str(out_dir),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or print the deterministic rolling-horizon MILP command.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--run", action="store_true", help="Actually execute the deterministic forecast backtest.")
    args = parser.parse_args()
    cmd = command(Path(args.out_dir))

    print("PROPOSED METHOD 1 / DETERMINISTIC FORECAST ROLLING-HORIZON MILP COMMAND")
    print(" ".join(cmd))
    print()
    print("New corrected reruns will be saved in:")
    print(DEFAULT_OUT)
    print()
    print("Historical June summaries/figures remain in:")
    print(REPO_ROOT / "strategy_model" / "optimization" / "rolling_horizon_gurobi_results" / "forecast_backtest_2014_2023")
    if args.run:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
