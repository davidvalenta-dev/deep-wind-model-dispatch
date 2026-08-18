#!/usr/bin/env python3
"""Step 3 of the Summer 2026 REU ladder: uncertainty-aware scenarios.

Run from this folder:
    ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py

This reruns baseload, single-forecast dispatch, and multi-scenario dispatch
using the settings in EXPERIMENT_KNOBS.py.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIGURE_GENERATOR = HERE.parent / "common" / "regenerate_all_figures.py"
os.environ["LC_ALL"] = "C"
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "summer_reu_mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "summer_reu_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import EXPERIMENT_KNOBS as knobs


RESULTS = Path(knobs.OUTPUT_DIR)
FIGURES = HERE / "figures"
SUMMARY_FILE = RESULTS / "uncertainty_aware_summary.csv"
ENRICHED_SUMMARY_FILE = RESULTS / "scenario_summary_vs_wind_only_and_100mw.csv"
RUNNER = HERE / "code" / "run_uncertainty_aware_dispatch.py"
COMPARISON_100MW_FILE = (
    HERE.parent
    / "100 MW baseload"
    / "results"
    / "comparison_scenarios_vs_100mw_baseload.csv"
)
CONTROLLED_STEP2_RESULTS = (
    HERE.parent
    / "rolling horizon"
    / "results"
    / "controlled_hourly_nowcast_from_knobs"
)

FCR = 0.065
WF_CAPEX = 1968.0
WF_OPEX = 43.0
WIND_GRID_CAP_MW = 249.0


def annualized_wind_only_cost() -> float:
    return ((WF_CAPEX * WIND_GRID_CAP_MW * 1000.0) * FCR) + (WF_OPEX * WIND_GRID_CAP_MW * 1000.0)


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required result file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def selected_horizon() -> int:
    summary = CONTROLLED_STEP2_RESULTS / "controlled_single_forecast_horizon_summary.csv"
    if not getattr(knobs, "USE_BEST_STEP2_HORIZON", False) or not summary.exists():
        return int(knobs.HORIZON_HOURS)
    rows = load_rows(summary)
    best = max(rows, key=lambda row: float(row["cove_reduction_vs_100mw_baseload_pct"]))
    return int(float(best["horizon_hours"]))


def assert_step2_matches(rows: list[dict[str, str]], horizon: int) -> None:
    """Require Step 3 one forecast to equal Step 2 at the selected horizon."""
    step2_summary = CONTROLLED_STEP2_RESULTS / f"horizon_{horizon}h" / "uncertainty_aware_summary.csv"
    if not step2_summary.exists():
        print(f"Controlled Step 2 {horizon} h output is unavailable; equality check skipped.")
        return
    step2_rows = load_rows(step2_summary)
    step2 = next(row for row in step2_rows if row["candidate"].startswith("single_forecast_recourse"))
    step3 = next(row for row in rows if row["candidate"].startswith("single_forecast_recourse"))
    checks = [
        "hours",
        "test_start",
        "test_end",
        "dispatch_revenue",
        "dispatch_cove_index",
        "100mw_baseload_revenue",
        "100mw_baseload_cove",
        "cove_reduction_vs_100mw_baseload_pct",
        "final_soc",
        "annual_soc_target_mwh",
        "annual_soc_target_violation_count",
        "final_soc_target_violation_count",
        "causal_ridge_forecast_sha256",
    ]
    numeric = {
        "dispatch_revenue",
        "dispatch_cove_index",
        "100mw_baseload_revenue",
        "100mw_baseload_cove",
        "cove_reduction_vs_100mw_baseload_pct",
        "final_soc",
        "annual_soc_target_mwh",
    }
    mismatches = []
    for key in checks:
        left = step2.get(key)
        right = step3.get(key)
        equal = (
            abs(float(left) - float(right)) <= 1e-9
            if key in numeric
            else left == right
        )
        if not equal:
            mismatches.append(f"{key}: Step 2={left!r}, Step 3={right!r}")
    if mismatches:
        raise RuntimeError(
            f"Step 3 one forecast does not match controlled Step 2 {horizon} h. "
            "Rerun Step 3 with the synchronized knobs before using its results:\n  "
            + "\n  ".join(mismatches)
        )
    print(f"Controlled equality check: Step 3 one forecast exactly matches Step 2 {horizon} h.")


def short_name(candidate: str) -> str:
    names = {
        "single_forecast_recourse": "1 forecast",
        "three_scenario_expected": "3 scenarios",
        "five_scenario_expected": "5 scenarios",
        "seven_scenario_expected": "7 scenarios",
        "ten_scenario_expected": "10 scenarios",
        "three_scenario_expected_gated": "3 scenarios + safety gate",
        "five_scenario_expected_gated": "5 scenarios + safety gate",
        "seven_scenario_expected_gated": "7 scenarios + safety gate",
        "ten_scenario_expected_gated": "10 scenarios + safety gate",
        "single_forecast_recourse_nowcast": "1 forecast",
        "three_scenario_expected_nowcast": "3 scenarios",
        "five_scenario_expected_nowcast": "5 scenarios",
        "seven_scenario_expected_nowcast": "7 scenarios",
        "ten_scenario_expected_nowcast": "10 scenarios",
        "single_forecast_recourse_nowcast_gated": "1 forecast",
        "three_scenario_expected_nowcast_gated": "3 scenarios",
        "five_scenario_expected_nowcast_gated": "5 scenarios",
        "seven_scenario_expected_nowcast_gated": "7 scenarios",
        "ten_scenario_expected_nowcast_gated": "10 scenarios",
    }
    return names.get(candidate, candidate)


def revenue_metric(value: str) -> str:
    return f"{float(value):,.2f}"


def add_wind_only_columns(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    wind_cost = annualized_wind_only_cost()
    updated: list[dict[str, str]] = []
    for row in rows:
        copied = dict(row)
        if "wind_only_cove_index" not in copied:
            copied["wind_only_cove_index"] = str(wind_cost / float(copied["wind_only_revenue"]))
        if "revenue_gain_vs_wind_only_pct" not in copied:
            copied["revenue_gain_vs_wind_only_pct"] = str(
                (float(copied["dispatch_revenue"]) / float(copied["wind_only_revenue"]) - 1.0) * 100.0
            )
        if "cove_reduction_vs_wind_only_pct" not in copied:
            copied["cove_reduction_vs_wind_only_pct"] = str(
                (float(copied["wind_only_cove_index"]) - float(copied["dispatch_cove_index"]))
                / float(copied["wind_only_cove_index"])
                * 100.0
            )
        updated.append(copied)
    return updated


def add_100mw_side_columns(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not COMPARISON_100MW_FILE.exists():
        return rows
    comparison = {
        row["candidate"]: row
        for row in load_rows(COMPARISON_100MW_FILE)
    }
    updated: list[dict[str, str]] = []
    for row in rows:
        copied = dict(row)
        side = comparison.get(copied["candidate"])
        if side is not None:
            for key in [
                "100mw_baseload_revenue",
                "100mw_baseload_cove",
                "revenue_gain_vs_100mw_baseload_pct",
                "cove_reduction_vs_100mw_baseload_pct",
            ]:
                if key in side and key not in copied:
                    copied[key] = side[key]
        updated.append(copied)
    return updated


def add_optional(cmd: list[str], flag: str, value) -> None:
    if value is not None:
        cmd.extend([flag, str(value)])


def rerun_from_knobs() -> None:
    horizon = selected_horizon()
    cmd = [
        sys.executable,
        str(RUNNER),
        "--horizon-hours",
        str(horizon),
        "--forecast-model-max-horizon-hours",
        str(knobs.FORECAST_MODEL_MAX_HORIZON_HOURS),
        "--evaluation-cutoff-horizon-hours",
        str(knobs.EVALUATION_CUTOFF_HORIZON_HOURS),
        "--execution-step-hours",
        str(knobs.EXECUTION_STEP_HOURS),
        "--replanning-interval-hours",
        str(knobs.REPLANNING_INTERVAL_HOURS),
        "--storage-power-mw",
        str(knobs.STORAGE_POWER_MW),
        "--storage-duration-h",
        str(knobs.STORAGE_DURATION_H),
        "--rte",
        str(knobs.RTE),
        "--dod",
        str(knobs.DOD),
        "--grid-cap-mw",
        str(knobs.GRID_CAP_MW),
        "--direct-reserve-mw",
        str(knobs.DIRECT_RESERVE_MW),
        "--train-origin-stride",
        str(knobs.TRAIN_ORIGIN_STRIDE),
        "--residual-origin-stride",
        str(knobs.RESIDUAL_ORIGIN_STRIDE),
        "--fallback-target-mw",
        str(knobs.FALLBACK_TARGET_MW),
        "--calibration-mode",
        str(knobs.CALIBRATION_MODE),
        "--forecast-train-end",
        str(knobs.FORECAST_TRAIN_END),
        "--calibration-end",
        str(knobs.CALIBRATION_END),
        "--variants",
        *list(knobs.VARIANTS),
        "--out-dir",
        str(RESULTS),
    ]
    add_optional(cmd, "--initial-soc-mwh", knobs.INITIAL_SOC_MWH)
    add_optional(cmd, "--annual-target-soc-mwh", knobs.ANNUAL_TARGET_SOC_MWH)
    add_optional(cmd, "--final-target-soc-mwh", knobs.FINAL_TARGET_SOC_MWH)
    add_optional(cmd, "--annual-soc-settlement-hours", knobs.ANNUAL_SOC_SETTLEMENT_HOURS)
    add_optional(cmd, "--max-origins", knobs.MAX_ORIGINS)
    add_optional(cmd, "--gate-margin", knobs.GATE_MARGIN)
    if getattr(knobs, "APPLY_GATE_TO_SINGLE_FORECAST", False):
        cmd.append("--gate-single-forecast")
    if knobs.NOWCAST_FIRST_HOUR:
        cmd.append("--nowcast-first-hour")
    else:
        cmd.append("--no-nowcast-first-hour")
    print("Running scenario-dispatch Gurobi command from EXPERIMENT_KNOBS.py:")
    print(" ".join(map(str, cmd)))
    print("Note: a full scenario rerun can take a long time. Set MAX_ORIGINS in EXPERIMENT_KNOBS.py for a quick test.")
    subprocess.run(cmd, cwd=HERE, check=True)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    if getattr(knobs, "RERUN_FROM_SOURCE", False):
        rerun_from_knobs()
    else:
        print("STEP 3: SCENARIO DISPATCH COMPARISON")
        print("RERUN_FROM_SOURCE is False, so I am reading the committed frozen 100 MW / 10-hour CAES CSV.")
        print("Set RERUN_FROM_SOURCE = True in EXPERIMENT_KNOBS.py only if you intentionally want a full rerun.\n")
    rows = add_100mw_side_columns(add_wind_only_columns(load_rows(SUMMARY_FILE)))
    assert_step2_matches(rows, selected_horizon())
    order = {
        "single_forecast_recourse": 1,
        "three_scenario_expected": 3,
        "five_scenario_expected": 5,
        "seven_scenario_expected": 7,
        "ten_scenario_expected": 10,
        "three_scenario_expected_gated": 3,
        "five_scenario_expected_gated": 5,
        "seven_scenario_expected_gated": 7,
        "ten_scenario_expected_gated": 10,
        "single_forecast_recourse_nowcast": 1,
        "three_scenario_expected_nowcast": 3,
        "five_scenario_expected_nowcast": 5,
        "seven_scenario_expected_nowcast": 7,
        "ten_scenario_expected_nowcast": 10,
        "single_forecast_recourse_nowcast_gated": 1,
        "three_scenario_expected_nowcast_gated": 3,
        "five_scenario_expected_nowcast_gated": 5,
        "seven_scenario_expected_nowcast_gated": 7,
        "ten_scenario_expected_nowcast_gated": 10,
    }
    rows = sorted(rows, key=lambda row: order.get(row["candidate"], 99))
    if not rows:
        raise RuntimeError("No scenario rows found.")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with ENRICHED_SUMMARY_FILE.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    wind_only_revenue = float(rows[0]["wind_only_revenue"])
    wind_only_cove = float(rows[0]["wind_only_cove_index"])
    benchmark_revenue = float(rows[0]["100mw_baseload_revenue"])
    benchmark_cove = float(rows[0]["100mw_baseload_cove"])
    horizon = int(float(rows[0]["horizon_hours"]))
    execution_policy = rows[0].get("execution_policy", "").strip()
    if not execution_policy:
        execution_policy = f"first {knobs.EXECUTION_STEP_HOURS} h, then replan"

    print("\nSTEP 3: SCENARIO-BASED ROLLING-HORIZON MILP")
    print("Primary comparison: 100-MW Constant-Output Baseload Benchmark.")
    print("Wind-only baseline is printed at the bottom as secondary reference only.")
    print("Higher revenue gain is better. COVE reduction is positive when COVE is lower than the 100 MW benchmark.")
    print(f"Scenario lookahead: {horizon} h; execution: {execution_policy}.\n")
    print(f"100 MW benchmark revenue: {benchmark_revenue:,.2f}")
    print(f"100 MW benchmark COVE:    {benchmark_cove:.6f}\n")
    print(
        f"{'Method':<16} {'Revenue metric':>18} {'Revenue gain':>14} "
        f"{'COVE':>10} {'COVE reduction':>12}"
    )
    print("-" * 76)
    print(f"{'100 MW bench':<16} {revenue_metric(str(benchmark_revenue)):>18} {'0.00%':>14} {benchmark_cove:>10.6f} {'0.00%':>12}")
    for row in rows:
        print(
            f"{short_name(row['candidate']):<16} "
            f"{revenue_metric(row['dispatch_revenue']):>18} "
            f"{float(row['revenue_gain_vs_100mw_baseload_pct']):>13.2f}% "
            f"{float(row['dispatch_cove_index']):>10.6f} "
            f"{float(row['cove_reduction_vs_100mw_baseload_pct']):>11.2f}%"
        )

    best = max(rows, key=lambda row: float(row["cove_reduction_vs_100mw_baseload_pct"]))
    print("\nBest scenario case:")
    print(
        f"  {short_name(best['candidate'])}, "
        f"{float(best['revenue_gain_vs_100mw_baseload_pct']):.2f}% revenue gain vs 100 MW benchmark, "
        f"{float(best['cove_reduction_vs_100mw_baseload_pct']):.2f}% COVE reduction vs 100 MW benchmark"
    )
    print("\nMeaning:")
    print("  This keeps the Step 2 controller fixed, then changes only the number of forecast futures.")
    print("  The winning row is the scenario count that gives the best COVE reduction against the 100 MW benchmark.")

    print("\nSecondary reference only: Wind-only baseline")
    print("No storage; actual wind delivered directly up to the 249 MW grid cap.")
    print(f"Wind-only revenue: {wind_only_revenue:,.2f}")
    print(f"Wind-only COVE:    {wind_only_cove:.6f}")
    print(f"{'Method':<16} {'Revenue gain vs wind-only':>26} {'COVE reduction vs wind-only':>26}")
    print("-" * 72)
    for row in rows:
        print(
            f"{short_name(row['candidate']):<16} "
            f"{float(row['revenue_gain_vs_wind_only_pct']):>25.2f}% "
            f"{float(row['cove_reduction_vs_wind_only_pct']):>25.2f}%"
        )

    labels = ["100 MW benchmark"] + [short_name(row["candidate"]) for row in rows]
    gains = [0.0] + [float(row["cove_reduction_vs_100mw_baseload_pct"]) for row in rows]
    rev_gains = [0.0] + [float(row["revenue_gain_vs_100mw_baseload_pct"]) for row in rows]
    revenues = [benchmark_revenue] + [float(row["dispatch_revenue"]) for row in rows]
    coves = [benchmark_cove] + [float(row["dispatch_cove_index"]) for row in rows]
    colors = ["#9AA4B2", "#203A5F", "#2F7D7A", "#68778C", "#6F627A", "#4F6D7A"]

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=180)
    bars = ax.bar(labels, gains, color=colors)
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Scenario Dispatch: COVE vs 100 MW Benchmark", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.25, f"{value:.2f}%", ha="center")
    fig.autofmt_xdate(rotation=15)
    fig.tight_layout()
    out1 = FIGURES / "step3_scenario_cove_improvement.png"
    fig.savefig(out1, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=180)
    bars = ax.bar(labels, rev_gains, color=colors)
    ax.set_ylabel("Revenue gain vs 100 MW benchmark (%)")
    ax.set_title("Scenario Dispatch: Revenue vs 100 MW Benchmark", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, rev_gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.25, f"{value:.2f}%", ha="center")
    fig.autofmt_xdate(rotation=15)
    fig.tight_layout()
    out2 = FIGURES / "step3_scenario_revenue_gain.png"
    fig.savefig(out2, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=180)
    ax.plot(rev_gains, gains, linewidth=1.8, color="#68778C", zorder=1)
    for label, x_value, y_value, color in zip(labels, rev_gains, gains, colors):
        ax.scatter(x_value, y_value, s=70, color=color, label=label, zorder=2)
    ax.set_xlabel("Revenue gain vs 100 MW benchmark (%)")
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Scenario Tradeoff: Revenue and COVE Move Together", fontweight="bold")
    ax.grid(color="#E5E7EB")
    ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9)
    fig.subplots_adjust(left=0.04, right=0.88, bottom=0.12, top=0.90)
    out3 = FIGURES / "step3_revenue_cove_tradeoff.png"
    fig.savefig(out3, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    ladder_labels = ["100 MW benchmark", "1 forecast", "Best scenarios"]
    ladder_values = [
        benchmark_revenue / 1e6,
        float(rows[0]["dispatch_revenue"]) / 1e6,
        float(best["dispatch_revenue"]) / 1e6,
    ]
    fig, ax = plt.subplots(figsize=(9.2, 5.2), dpi=180)
    bars = ax.bar(ladder_labels, ladder_values, color=["#9AA4B2", "#2F7D7A", "#6F627A"])
    ax.set_ylabel("Normalized price-weighted revenue metric (millions)")
    ax.set_title("Ladder Result: Forecast Dispatch to Scenario Dispatch", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, ladder_values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.05, f"{value:.2f}M", ha="center")
    fig.subplots_adjust(left=0.04, right=0.87, bottom=0.12, top=0.90)
    out4 = FIGURES / "step3_ladder_revenue_progression.png"
    fig.savefig(out4, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    subprocess.run([sys.executable, str(FIGURE_GENERATOR), "--step", "3"], cwd=HERE.parent, check=True)
    print("\nFigures saved:")
    print(f"\nEnriched summary saved:\n  {ENRICHED_SUMMARY_FILE}")
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure}")


if __name__ == "__main__":
    main()
