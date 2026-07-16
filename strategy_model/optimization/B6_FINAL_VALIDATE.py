"""Validate the canonical B6 result folder.

This checks the things Chris specifically cared about:
- exactly six runs,
- 8784 rows in every hourly CSV,
- raw revenue equals delivered power times raw realized LMP,
- zero physical constraint violations,
- final realized SoC equals the annual 20% target.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = REPO_ROOT / "strategy_model" / "optimization" / "b6_final_results"
EXPECTED_RUNS = {
    "A_ORACLE",
    "A_CAUSAL",
    "B_ORACLE",
    "B_CAUSAL",
    "C_ORACLE",
    "C_CAUSAL",
}


def validate(results_dir: Path) -> dict[str, object]:
    summary_path = results_dir / "David_B6_run_summary.csv"
    qa_path = results_dir / "David_B6_QA_summary.csv"
    config_path = results_dir / "David_B6_frozen_config.json"
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    if not qa_path.exists():
        raise FileNotFoundError(qa_path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    summary = pd.read_csv(summary_path)
    qa = pd.read_csv(qa_path)
    config = json.loads(config_path.read_text())
    run_ids = set(summary["run_id"].astype(str))
    if run_ids != EXPECTED_RUNS:
        raise AssertionError(f"Expected {EXPECTED_RUNS}, found {run_ids}")
    if set(qa["run_id"].astype(str)) != EXPECTED_RUNS:
        raise AssertionError("QA file does not contain the same six runs.")

    hourly_results = {}
    for row in summary.to_dict("records"):
        run_id = str(row["run_id"])
        hourly_path = results_dir / str(row["hourly_output_filename"])
        if not hourly_path.exists():
            raise FileNotFoundError(hourly_path)
        hourly = pd.read_csv(hourly_path)
        if len(hourly) != 8784:
            raise AssertionError(f"{run_id} has {len(hourly)} rows, expected 8784.")
        revenue = float((hourly["delivered_power_MW"] * hourly["actual_raw_price_USD_per_MWh"]).sum())
        if abs(revenue - float(row["raw_realized_revenue_usd"])) > 1e-4:
            raise AssertionError(f"{run_id} revenue mismatch: hourly={revenue}, summary={row['raw_realized_revenue_usd']}")
        if abs(float(hourly["SOC_end_MWh"].iloc[-1]) - float(row["final_soc_mwh"])) > 1e-8:
            raise AssertionError(f"{run_id} final SoC mismatch between hourly and summary.")
        if int(row["constraint_violations"]) != 0:
            raise AssertionError(f"{run_id} reports constraint violations.")
        if int(row["qa_annual_terminal_soc_violation_count"]) != 0:
            raise AssertionError(f"{run_id} reports annual terminal SoC violation.")
        hourly_results[run_id] = {
            "rows": int(len(hourly)),
            "raw_realized_revenue_usd": revenue,
            "final_soc_mwh": float(hourly["SOC_end_MWh"].iloc[-1]),
            "max_delivered_mw": float(hourly["delivered_power_MW"].max()),
            "max_revenue_abs_error_usd": float(
                np.abs(hourly["hourly_raw_revenue_USD"] - hourly["delivered_power_MW"] * hourly["actual_raw_price_USD_per_MWh"]).max()
            ),
        }

    common = config["common_configuration"]
    required_common = {
        "rte": 0.55,
        "min_soc_frac": 0.20,
        "initial_soc_frac": 0.20,
        "grid_cap_mw": 249.0,
        "causal_horizon_hours": 48,
        "execution_step_hours": 24,
    }
    for key, expected in required_common.items():
        actual = float(common[key])
        if abs(actual - expected) > 1e-12:
            raise AssertionError(f"Config {key}={actual}, expected {expected}.")

    return {
        "status": "PASS",
        "results_dir": str(results_dir),
        "runs": hourly_results,
        "common_configuration": common,
        "data_audit": config["data_audit"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate canonical B6 results.")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    report = validate(args.results_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
