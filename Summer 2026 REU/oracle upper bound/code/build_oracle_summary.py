#!/usr/bin/env python3
"""Build the oracle upper-bound summary from the rolling-horizon result table.

Oracle means Gurobi receives the realized future wind and realized future price.
That is not deployable in real life, but it is useful because it shows the
best possible value for the same storage constraints and horizons.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    HERE.parents[0]
    / "rolling horizon"
    / "results"
    / "causal_ridge_rolling_horizon_summary.csv"
)
DEFAULT_OUTPUT = HERE / "results" / "oracle_upper_bound_summary.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the oracle upper-bound summary table.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise FileNotFoundError(f"Missing rolling-horizon source summary: {source}")

    summary = pd.read_csv(source)
    oracle = summary[summary["method"] == "oracle"].copy()
    if oracle.empty:
        raise RuntimeError(f"No oracle rows found in {source}")

    oracle = oracle.sort_values("horizon_hours")
    oracle["case_type"] = "perfect_future_oracle"
    oracle["realistic"] = False
    oracle["meaning"] = (
        "Gurobi sees the realized future wind and price; this is an upper bound, not a deployable forecast."
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    oracle.to_csv(output, index=False)
    print(oracle[[
        "method",
        "horizon_hours",
        "cove",
        "baseload_cove",
        "improvement_vs_baseload_pct",
        "revenue_metric",
        "final_soc",
        "solver_runtime_seconds",
    ]].to_string(index=False))
    print(f"Saved oracle summary to {output}")


if __name__ == "__main__":
    main()
