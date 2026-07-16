"""Upper-bound dispatch: perfect-information oracle.

The oracle gives Gurobi the realized future wind and price.  It is not a real
operating controller because it knows the future.  Its purpose is to show the
best result that the storage and constraints could produce under perfect
information.
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
        "--out-dir",
        str(out_dir),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or print the oracle upper-bound backtest command.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--run", action="store_true", help="Actually execute the full oracle+causal backtest.")
    args = parser.parse_args()
    cmd = command(Path(args.out_dir))

    print("UPPER BOUND / ORACLE COMMAND")
    print(" ".join(cmd))
    print()
    print("This runs the forecast backtest with oracle enabled. It also produces the matching causal rows.")
    print("New corrected reruns will be saved in:")
    print(Path(args.out_dir))
    print("Historical oracle CSVs remain in strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/")
    if args.run:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
