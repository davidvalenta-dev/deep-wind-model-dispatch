"""Lower-bound/reference dispatch: baseload comparator.

Baseload is the reference case: deliver wind directly when possible and use
storage only to smooth toward a constant target.  It is not the proposed method;
it is the line that the proposed dispatch methods are compared against.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
OPT_DIR = REPO_ROOT / "strategy_model" / "optimization"
for path in (STRATEGY_SRC, OPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import util  # noqa: E402
from rolling_horizon_gurobi_dispatch import (  # noqa: E402
    continuous_baseload,
    cove_value,
    fixed_costs,
    load_data,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute the baseload lower-bound/reference result.")
    parser.add_argument("--data", default=str(REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"))
    parser.add_argument("--config", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"))
    parser.add_argument("--out-dir", default=str(OPT_DIR / "reviewer_reproduction" / "lower_bound_baseload"))
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--hours", type=int, default=None)
    parser.add_argument("--initial-soc", type=float, default=0.0)
    parser.add_argument("--storage-type", default=None)
    parser.add_argument("--storage-rating", type=float, default=None)
    parser.add_argument("--storage-duration", type=float, default=None)
    args = parser.parse_args()

    config = util.load_config(args.config)
    if args.storage_type is not None:
        config["storage_type"] = args.storage_type
    if args.storage_rating is not None:
        config["storage_rating"] = args.storage_rating
    if args.storage_duration is not None:
        config["storage_duration"] = args.storage_duration

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(Path(args.data), config, args.offset, args.hours)
    generation = df["power_generated"].to_numpy(float)
    raw_lmp = df["lmp"].to_numpy(float)
    cove_price = df["price_normalized"].to_numpy(float)
    delivered = continuous_baseload(generation, config, initial_soc=args.initial_soc)
    _, dispatch_cost = fixed_costs(config)

    summary = {
        "case": "lower_bound_baseload",
        "hours": int(len(df)),
        "data": str(Path(args.data).resolve()),
        "raw_realized_revenue_usd": float(np.sum(raw_lmp * delivered)),
        "normalized_price_revenue_metric": float(util.revenue(delivered, cove_price)),
        "cove": cove_value(delivered, cove_price, config),
        "profit_metric": float(util.revenue(delivered, cove_price) - dispatch_cost),
        "mean_delivered_mw": float(np.mean(delivered)),
        "max_delivered_mw": float(np.max(delivered)),
    }

    pd.DataFrame({"delivered_mw": delivered}).to_csv(out_dir / "lower_bound_baseload_hourly.csv", index=False)
    pd.DataFrame([summary]).to_csv(out_dir / "lower_bound_baseload_summary.csv", index=False)
    (out_dir / "lower_bound_baseload_summary.json").write_text(json.dumps(summary, indent=2))

    print("LOWER BOUND / BASELOAD")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"Saved to: {out_dir}")


if __name__ == "__main__":
    main()
