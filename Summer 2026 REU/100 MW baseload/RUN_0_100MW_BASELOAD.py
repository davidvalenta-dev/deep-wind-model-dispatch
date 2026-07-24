#!/usr/bin/env python3
"""Step 0: 100-MW Constant-Output Baseload Benchmark.

Run from this folder:
    ../../venv/bin/python RUN_0_100MW_BASELOAD.py

This folder is the reference case Chris asked for. It is a rule-based
wind-storage benchmark, not a Gurobi revenue optimizer:

- if wind is above 100 MW, deliver 100 MW, charge with extra wind, curtail rest;
- if wind is below 100 MW, deliver wind and discharge storage toward 100 MW;
- keep SoC between 200 and 1000 MWh;
- start at 600 MWh;
- do not force final SoC back to 600 MWh.

The script also compares the canonical 2020 oracle rolling-horizon cases
against this 100-MW baseload because they use the same 2020 data and storage
configuration.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["LC_ALL"] = "C"
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "summer_reu_mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "summer_reu_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import EXPERIMENT_KNOBS as knobs


RESULTS = Path(knobs.OUTPUT_DIR)
FIGURES = HERE / "figures"
SUMMARY_FILE = RESULTS / "canonical_summary.csv"
QA_FILE = RESULTS / "canonical_QA_report.csv"
HOURLY_FILE = RESULTS / "constant_output_baseload_100mw_2020_hourly.csv"
COMPARISON_FILE = RESULTS / "oracle_vs_100mw_baseload_comparison.csv"
B6_SUMMARY_FILE = (
    HERE.parent
    / "b6 verification"
    / "b6_final_results"
    / "David_B6_run_summary.csv"
)
B6_COMPARISON_FILE = RESULTS / "b6_2020_vs_100mw_baseload_revenue_comparison.csv"
RUNNER = HERE / "code" / "canonical_benchmark_oracle_runner.py"
FULL_PERIOD_RUNNER = HERE / "code" / "build_100mw_baseload_reference.py"
FULL_PERIOD_HOURLY_FILE = RESULTS / "constant_output_baseload_100mw_2014_2023_hourly.csv"
FULL_PERIOD_SUMMARY_FILE = RESULTS / "constant_output_baseload_100mw_2014_2023_summary.csv"
FULL_PERIOD_ROLLING_COMPARISON_FILE = RESULTS / "comparison_rolling_horizon_vs_100mw_baseload.csv"
FULL_PERIOD_SCENARIO_COMPARISON_FILE = RESULTS / "comparison_scenarios_vs_100mw_baseload.csv"
FULL_PERIOD_ORACLE_COMPARISON_FILE = RESULTS / "comparison_oracle_vs_100mw_baseload.csv"
ROLLING_SUMMARY_FILE = HERE.parent / "rolling horizon" / "results" / "causal_ridge_rolling_horizon_summary.csv"
SCENARIO_SUMMARY_FILE = HERE.parent / "different scenarios" / "results" / "scenario_48h_full_ladder" / "uncertainty_aware_summary.csv"
ORACLE_SUMMARY_FILE = HERE.parent / "oracle upper bound" / "results" / "oracle_upper_bound_summary.csv"


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def pct_gain(value: float, base: float) -> float:
    return (value - base) / base * 100.0


def pct_reduction(value: float, base: float) -> float:
    return (base - value) / base * 100.0


def add_optional(cmd: list[str], flag: str, value) -> None:
    if value is not None:
        cmd.extend([flag, str(value)])


def rerun_from_knobs() -> None:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--repo",
        str(knobs.REPO_ROOT),
        "--out",
        str(RESULTS),
        "--horizons",
        *[str(horizon) for horizon in knobs.HORIZONS],
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
        "--mip-gap",
        str(knobs.MIP_GAP),
    ]
    add_optional(cmd, "--min-soc-mwh", knobs.MIN_SOC_MWH)
    add_optional(cmd, "--max-soc-mwh", knobs.MAX_SOC_MWH)
    add_optional(cmd, "--initial-soc-mwh", knobs.INITIAL_SOC_MWH)
    add_optional(cmd, "--year-end-soc-mwh", knobs.YEAR_END_SOC_MWH)
    add_optional(cmd, "--time-limit", knobs.TIME_LIMIT_SECONDS)
    print("Running 100 MW baseload/oracle command from EXPERIMENT_KNOBS.py:")
    print(" ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=HERE, check=True)


def rerun_full_period_baseload_from_knobs() -> None:
    cmd = [
        sys.executable,
        str(FULL_PERIOD_RUNNER),
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
        "--rolling-summary",
        str(ROLLING_SUMMARY_FILE),
        "--scenario-summary",
        str(SCENARIO_SUMMARY_FILE),
        "--oracle-summary",
        str(ORACLE_SUMMARY_FILE),
    ]
    add_optional(cmd, "--end", knobs.FULL_PERIOD_END)
    add_optional(cmd, "--min-soc-mwh", knobs.MIN_SOC_MWH)
    add_optional(cmd, "--max-soc-mwh", knobs.MAX_SOC_MWH)
    add_optional(cmd, "--initial-soc-mwh", knobs.INITIAL_SOC_MWH)
    print("\nRunning 2014-2023 100 MW baseload reference from EXPERIMENT_KNOBS.py:")
    print(" ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=HERE, check=True)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    rerun_from_knobs()
    rerun_full_period_baseload_from_knobs()

    summary_rows = read_rows(SUMMARY_FILE)
    qa_rows = read_rows(QA_FILE)
    qa_by_case = {row["case_id"]: row for row in qa_rows}

    baseload = next(row for row in summary_rows if row["case_id"] == "constant_output_baseload_100mw_2020")
    oracle_rows = [row for row in summary_rows if row["case_id"].startswith("oracle_rh_milp_")]
    oracle_rows = sorted(oracle_rows, key=lambda row: int(float(row["planning_horizon_hours"])))

    base_revenue = float(baseload["revenue_usd"])
    base_cove = float(baseload["COVE"])

    print("\nSTEP 0: 100-MW CONSTANT-OUTPUT BASELOAD BENCHMARK")
    print("This is the rule-based storage benchmark Chris asked for.\n")
    print(f"Rows / hours:              {int(float(baseload['row_count'])):,}")
    print(f"Revenue:                   ${base_revenue:,.2f}")
    print(f"COVE:                      {base_cove:.6f}")
    print(f"Initial SoC:               {float(baseload['initial_soc_mwh']):,.2f} MWh")
    print(f"Final SoC:                 {float(baseload['final_soc_mwh']):,.2f} MWh")
    print(f"Min / max SoC:             {float(baseload['min_soc_mwh']):,.2f} / {float(baseload['max_soc_mwh']):,.2f} MWh")
    print(f"Total curtailment:         {float(baseload['total_curtailment_mwh']):,.2f} MWh")
    print(f"Total output shortfall:    {float(baseload['total_output_shortfall_mwh']):,.2f} MWh")
    print(f"Hours exactly at 100 MW:   {int(float(baseload['hours_exactly_meeting_100mw'])):,} "
          f"({float(baseload['percent_hours_exactly_meeting_100mw']):.2f}%)")
    print(f"QA violations:             {int(float(qa_by_case[baseload['case_id']]['total_violation_count']))}")

    comparison_rows = []
    print("\nCanonical 2020 oracle cases compared against this 100-MW baseload:")
    print(f"{'Case':<14} {'Revenue':>16} {'Revenue gain':>14} {'COVE':>10} {'COVE reduction':>16} {'QA viol.':>9}")
    print("-" * 88)
    for row in oracle_rows:
        revenue = float(row["revenue_usd"])
        cove = float(row["COVE"])
        horizon = int(float(row["planning_horizon_hours"]))
        revenue_gain = pct_gain(revenue, base_revenue)
        cove_gain = pct_reduction(cove, base_cove)
        violations = int(float(qa_by_case[row["case_id"]]["total_violation_count"]))
        comparison_rows.append(
            {
                "case_id": row["case_id"],
                "case_name": row["case_name"],
                "planning_horizon_hours": horizon,
                "revenue_usd": revenue,
                "revenue_gain_vs_100mw_baseload_pct": revenue_gain,
                "COVE": cove,
                "COVE_reduction_vs_100mw_baseload_pct": cove_gain,
                "qa_total_violation_count": violations,
            }
        )
        print(
            f"{horizon:>3} h oracle "
            f"${revenue:>14,.2f} "
            f"{revenue_gain:>13.2f}% "
            f"{cove:>10.6f} "
            f"{cove_gain:>15.2f}% "
            f"{violations:>9}"
        )

    pd.DataFrame(comparison_rows).to_csv(COMPARISON_FILE, index=False)

    b6_rows = []
    if B6_SUMMARY_FILE.exists():
        b6_summary = pd.read_csv(B6_SUMMARY_FILE)
        print("\nB6 same-year raw realized revenue compared against this 100-MW baseload:")
        print("This is a revenue-only comparison because B6 was Chris's raw-LMP verification packet.")
        print(f"{'Run':<10} {'Workflow':<8} {'Storage':<12} {'Revenue':>16} {'Revenue gain':>14} {'QA viol.':>9}")
        print("-" * 78)
        for _, row in b6_summary.sort_values(["architecture_id", "workflow"]).iterrows():
            revenue = float(row["raw_realized_revenue_usd"])
            revenue_gain = pct_gain(revenue, base_revenue)
            storage_label = f"{float(row['power_mw']):.0f}MW/{float(row['duration_h']):.0f}h"
            violations = int(float(row["constraint_violations"]))
            b6_rows.append(
                {
                    "run_id": row["run_id"],
                    "architecture_id": row["architecture_id"],
                    "workflow": row["workflow"],
                    "storage_power_mw": float(row["power_mw"]),
                    "storage_duration_h": float(row["duration_h"]),
                    "energy_mwh": float(row["energy_mwh"]),
                    "raw_realized_revenue_usd": revenue,
                    "revenue_gain_vs_100mw_baseload_pct": revenue_gain,
                    "initial_soc_mwh": float(row["initial_soc_mwh"]),
                    "minimum_soc_mwh": float(row["minimum_soc_mwh"]),
                    "final_soc_mwh": float(row["final_soc_mwh"]),
                    "constraint_violations": violations,
                    "note": "same 2020 raw realized LMP; B6 annual SoC rule differs from the 100-MW baseload rule",
                }
            )
            print(
                f"{row['run_id']:<10} {row['workflow']:<8} {storage_label:<12} "
                f"${revenue:>14,.2f} {revenue_gain:>13.2f}% {violations:>9}"
            )
        pd.DataFrame(b6_rows).to_csv(B6_COMPARISON_FILE, index=False)

    hourly = pd.read_csv(HOURLY_FILE, parse_dates=["timestamp"])
    week = hourly.iloc[:168].copy()
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 7.5), dpi=180, sharex=True)
    axes[0].plot(week["timestamp"], week["actual_wind_MW"], color="#111827", linewidth=1.6, label="actual wind")
    axes[0].plot(week["timestamp"], week["delivered_power_MW"], color="#2563EB", linewidth=1.6, label="delivered power")
    axes[0].axhline(100, color="#DC2626", linestyle="--", linewidth=1.1, label="100 MW target")
    axes[0].set_ylabel("MW")
    axes[0].legend(frameon=False, ncol=3, loc="upper right")
    axes[0].set_title("100-MW Constant-Output Baseload: Example Week", fontweight="bold")

    axes[1].bar(week["timestamp"], week["charge_MW"], color="#22C55E", width=0.035, label="charge")
    axes[1].bar(week["timestamp"], -week["discharge_MW"], color="#F97316", width=0.035, label="discharge")
    axes[1].axhline(0, color="#111827", linewidth=0.8)
    axes[1].set_ylabel("charge / discharge")
    axes[1].legend(frameon=False, ncol=2, loc="upper right")

    axes[2].plot(week["timestamp"], week["SOC_end_MWh"], color="#7C3AED", linewidth=1.8)
    axes[2].axhline(200, color="#6B7280", linestyle="--", linewidth=1.0, label="SoC min/max")
    axes[2].axhline(1000, color="#6B7280", linestyle="--", linewidth=1.0)
    axes[2].set_ylabel("SoC (MWh)")
    axes[2].set_xlabel("UTC timestamp")
    axes[2].legend(frameon=False, loc="upper right")

    for ax in axes:
        ax.grid(color="#E5E7EB")
        ax.set_axisbelow(True)
    fig.autofmt_xdate(rotation=18)
    fig.tight_layout()
    fig.savefig(FIGURES / "step0_100mw_baseload_example_week.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    labels = ["100 MW\nbaseload"] + [f"{row['planning_horizon_hours']} h\noracle" for row in comparison_rows]
    revenues = [base_revenue / 1e6] + [row["revenue_usd"] / 1e6 for row in comparison_rows]
    coves = [base_cove] + [row["COVE"] for row in comparison_rows]

    fig, axes = plt.subplots(2, 1, figsize=(9.8, 7.0), dpi=180, sharex=True)
    x = range(len(labels))
    axes[0].bar(x, revenues, color=["#9CA3AF"] + ["#111827"] * len(comparison_rows))
    axes[0].set_ylabel("Revenue ($M)")
    axes[0].set_title("Oracle Cases Compared Against 100-MW Baseload", fontweight="bold")
    for i, value in enumerate(revenues):
        axes[0].text(i, value + 0.08, f"${value:.2f}M", ha="center", fontsize=9)

    axes[1].plot(list(x), coves, marker="o", color="#111827", linewidth=2.2)
    axes[1].set_ylabel("COVE (lower is better)")
    axes[1].set_xticks(list(x), labels)
    for i, value in enumerate(coves):
        axes[1].text(i, value + 0.035, f"{value:.3f}", ha="center", fontsize=9)
    for ax in axes:
        ax.grid(color="#E5E7EB")
        ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(FIGURES / "step0_oracle_vs_100mw_baseload.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    if b6_rows:
        b6_plot = pd.DataFrame(b6_rows)
        b6_plot["label"] = b6_plot["run_id"].str.replace("_", "\n", regex=False)
        b6_plot = b6_plot.sort_values("revenue_gain_vs_100mw_baseload_pct")
        fig, ax = plt.subplots(figsize=(10.2, 5.8), dpi=180)
        colors = ["#2563EB" if workflow == "Causal" else "#DC2626" for workflow in b6_plot["workflow"]]
        bars = ax.barh(b6_plot["label"], b6_plot["revenue_gain_vs_100mw_baseload_pct"], color=colors)
        ax.axvline(0, color="#111827", linewidth=1.0)
        ax.set_xlabel("Raw revenue gain vs 100-MW baseload (%)")
        ax.set_title("2020 B6 Runs Compared With 100-MW Baseload", fontweight="bold", pad=12)
        ax.grid(axis="x", color="#E5E7EB")
        ax.set_axisbelow(True)
        for bar, value in zip(bars, b6_plot["revenue_gain_vs_100mw_baseload_pct"]):
            x = value + (0.8 if value >= 0 else -0.8)
            ha = "left" if value >= 0 else "right"
            ax.text(x, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", ha=ha, fontsize=9)
        fig.tight_layout()
        fig.savefig(FIGURES / "step0_b6_revenue_vs_100mw_baseload.png", facecolor="white", bbox_inches="tight")
        plt.close(fig)

    print("\nFiles written:")
    print(f"  {COMPARISON_FILE}")
    print(f"  {FULL_PERIOD_SUMMARY_FILE}")
    print(f"  {FULL_PERIOD_HOURLY_FILE}")
    if FULL_PERIOD_ROLLING_COMPARISON_FILE.exists():
        print(f"  {FULL_PERIOD_ROLLING_COMPARISON_FILE}")
    if FULL_PERIOD_SCENARIO_COMPARISON_FILE.exists():
        print(f"  {FULL_PERIOD_SCENARIO_COMPARISON_FILE}")
    if FULL_PERIOD_ORACLE_COMPARISON_FILE.exists():
        print(f"  {FULL_PERIOD_ORACLE_COMPARISON_FILE}")
    if b6_rows:
        print(f"  {B6_COMPARISON_FILE}")
    print(f"  {FIGURES / 'step0_100mw_baseload_example_week.png'}")
    print(f"  {FIGURES / 'step0_100mw_baseload_2014_2023_example_week.png'}")
    print(f"  {FIGURES / 'step0_methods_vs_100mw_baseload.png'}")
    print(f"  {FIGURES / 'step0_oracle_vs_100mw_baseload.png'}")
    if b6_rows:
        print(f"  {FIGURES / 'step0_b6_revenue_vs_100mw_baseload.png'}")
    print("\nFull rebuild command, if Chris wants to regenerate from raw data:")
    print(
        "  "
        + " ".join(
            map(
                str,
                [
                    sys.executable,
                    RUNNER,
                    "--out",
                    RESULTS,
                    "--horizons",
                    *knobs.HORIZONS,
                    "--storage-power-mw",
                    knobs.STORAGE_POWER_MW,
                    "--storage-duration-h",
                    knobs.STORAGE_DURATION_H,
                    "--rte",
                    knobs.RTE,
                    "--target-output-mw",
                    knobs.TARGET_OUTPUT_MW,
                    "--grid-cap-mw",
                    knobs.GRID_CAP_MW,
                ],
            )
        )
    )


if __name__ == "__main__":
    main()
