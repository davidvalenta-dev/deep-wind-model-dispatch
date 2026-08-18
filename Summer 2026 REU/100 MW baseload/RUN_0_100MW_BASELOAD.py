#!/usr/bin/env python3
"""Run or display the frozen Step 0 constant-output benchmark."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import EXPERIMENT_KNOBS as knobs


HERE = Path(__file__).resolve().parent
RESULTS = Path(knobs.OUTPUT_DIR)
FIGURES = HERE / "figures"
RUNNER = HERE / "code" / "build_100mw_baseload_reference.py"
HOURLY = RESULTS / "constant_output_baseload_100mw_2014_2023_hourly.csv"
SUMMARY = RESULTS / "constant_output_baseload_100mw_2014_2023_summary.csv"


def command() -> list[str]:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--data",
        str(knobs.FULL_PERIOD_DATA),
        "--out-dir",
        str(RESULTS),
        "--figures-dir",
        str(FIGURES),
        "--start",
        str(knobs.FULL_PERIOD_START),
        "--storage-power-mw",
        str(knobs.STORAGE_POWER_MW),
        "--storage-duration-h",
        str(knobs.STORAGE_DURATION_H),
        "--rte",
        str(knobs.RTE),
        "--target-output-mw",
        str(knobs.TARGET_OUTPUT_MW),
        "--grid-cap-mw",
        str(knobs.GRID_CAP_MW),
        "--price-threshold",
        str(knobs.PRICE_THRESHOLD),
        "--normalized-price-train-end",
        str(knobs.NORMALIZED_PRICE_TRAIN_END),
        "--min-soc-mwh",
        str(knobs.MIN_SOC_MWH),
        "--max-soc-mwh",
        str(knobs.MAX_SOC_MWH),
        "--initial-soc-mwh",
        str(knobs.INITIAL_SOC_MWH),
        "--annual-target-soc-mwh",
        str(knobs.YEAR_END_SOC_MWH),
        "--final-target-soc-mwh",
        str(knobs.YEAR_END_SOC_MWH),
        "--annual-soc-settlement-hours",
        str(knobs.ANNUAL_SOC_SETTLEMENT_HOURS),
    ]
    if knobs.FULL_PERIOD_END is not None:
        cmd.extend(["--end", str(knobs.FULL_PERIOD_END)])
    return cmd


def draw_example_week(hourly: pd.DataFrame) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    week = hourly.iloc[:168].copy()
    timestamp = pd.to_datetime(week["datetime"])
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.8), dpi=180, sharex=True)
    ax1.plot(timestamp, week["actual_wind_mw"], label="Actual wind", color="#2563EB", linewidth=1.5)
    ax1.plot(timestamp, week["delivered_power_mw"], label="Delivered power", color="#0F766E", linewidth=1.7)
    ax1.axhline(knobs.TARGET_OUTPUT_MW, color="#D97706", linestyle="--", label="100 MW target")
    ax1.set_ylabel("Power (MW)")
    ax1.legend(frameon=False, ncol=3)
    ax1.grid(color="#E5E7EB")
    soc_column = "soc_end_mwh"
    ax2.plot(timestamp, week[soc_column], color="#7C3AED", linewidth=1.7)
    ax2.axhline(knobs.MIN_SOC_MWH, color="#6B7280", linestyle=":")
    ax2.axhline(knobs.MAX_SOC_MWH, color="#6B7280", linestyle=":")
    ax2.set_ylabel("Stored energy (MWh)")
    ax2.set_xlabel("Time")
    ax2.grid(color="#E5E7EB")
    fig.suptitle("100 MW Constant-Output Benchmark: Example Week", fontweight="bold")
    fig.tight_layout()
    out = FIGURES / "step0_100mw_baseload_2014_2023_example_week.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    if knobs.RERUN_FROM_SOURCE:
        print("Running the frozen Step 0 source command:")
        print(" ".join(command()))
        subprocess.run(command(), cwd=HERE, check=True)
    else:
        print("STEP 0: reading committed frozen CSVs without recomputing.\n")

    if not SUMMARY.exists() or not HOURLY.exists():
        raise FileNotFoundError("Frozen Step 0 outputs are missing. Set RERUN_FROM_SOURCE = True to rebuild them.")

    row = pd.read_csv(SUMMARY).iloc[0]
    hourly = pd.read_csv(HOURLY)
    figure = draw_example_week(hourly)
    print("STEP 0: 100-MW CONSTANT-OUTPUT BASELOAD BENCHMARK")
    print(f"Period:          {row['period_start']} to {row['period_end']}")
    print(f"Hours:           {int(row['hours']):,}")
    print(f"Revenue metric:  {float(row['normalized_revenue_metric']):,.2f}")
    print(f"COVE index:      {float(row['normalized_cove_index']):.6f}")
    print(f"Raw revenue:     ${float(row['raw_revenue_usd']):,.2f}")
    print(f"Initial/final SoC: {float(row['initial_soc_mwh']):.2f} / {float(row['final_soc_mwh']):.2f} MWh")
    print(f"Annual/final violations: {int(row['annual_soc_target_violation_count'])} / {int(row['final_soc_target_violation_count'])}")
    print(f"Hourly CSV:      {HOURLY}")
    print(f"Summary CSV:     {SUMMARY}")
    print(f"Figure:          {figure}")


if __name__ == "__main__":
    main()
