#!/usr/bin/env python3
"""Step 2: controlled single-forecast rolling-horizon comparison.

This wrapper deliberately calls the exact Step 3 scenario runner with only
``single_recourse`` enabled. Step 2 therefore changes planning horizon and
nothing else. The winning Step 2 horizon must equal the Step 3 one-forecast
row when both are rerun from the same knobs.

Run from this folder:
    ../../venv/bin/python RUN_2_ROLLING_HORIZON.py
"""

from __future__ import annotations

import csv
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENARIO_FOLDER = HERE.parent / "different scenarios"
CANONICAL_CONTROLLER = SCENARIO_FOLDER / "code" / "run_uncertainty_aware_dispatch.py"
STEP3_SUMMARY = SCENARIO_FOLDER / "results" / "frozen_controlled" / "uncertainty_aware_summary.csv"
STEP3_KNOBS_PATH = SCENARIO_FOLDER / "EXPERIMENT_KNOBS.py"

os.environ["LC_ALL"] = "C"
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "summer_reu_mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "summer_reu_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import EXPERIMENT_KNOBS as knobs


RESULTS = Path(knobs.OUTPUT_DIR)
FIGURES = HERE / "figures"
FULL_HOURLY = HERE / "results" / "full_hourly_outputs"
SUMMARY_FILE = RESULTS / "controlled_single_forecast_horizon_summary.csv"
SUMMARY_ALIAS = HERE / "results" / "causal_ridge_rolling_horizon_summary.csv"
CANONICAL_DISPATCH_COST_USD = 51_416_725.0
CANONICAL_WIND_ONLY_COST_USD = 42_559_080.0


def normalize_cove_metrics(row: dict[str, str]) -> dict[str, str]:
    """Refresh COVE fields using the frozen 100 MW / 10 h CAES cost model."""
    result = dict(row)
    dispatch_revenue = float(result["dispatch_revenue"])
    baseload_revenue = float(result["baseload_revenue"])
    wind_revenue = float(result["wind_only_revenue"])
    benchmark_revenue = float(result["100mw_baseload_revenue"])
    dispatch_cove = CANONICAL_DISPATCH_COST_USD / dispatch_revenue
    baseload_cove = CANONICAL_DISPATCH_COST_USD / baseload_revenue
    wind_cove = CANONICAL_WIND_ONLY_COST_USD / wind_revenue
    benchmark_cove = CANONICAL_DISPATCH_COST_USD / benchmark_revenue
    result.update(
        {
            "dispatch_cove_index": str(dispatch_cove),
            "annualized_dispatch_cost_usd": str(CANONICAL_DISPATCH_COST_USD),
            "baseload_cove_index": str(baseload_cove),
            "wind_only_cove_index": str(wind_cove),
            "100mw_baseload_cove": str(benchmark_cove),
            "cove_reduction_vs_baseload_pct": str((1.0 - dispatch_cove / baseload_cove) * 100.0),
            "cove_reduction_vs_wind_only_pct": str((1.0 - dispatch_cove / wind_cove) * 100.0),
            "cove_reduction_vs_100mw_baseload_pct": str(
                (1.0 - dispatch_cove / benchmark_cove) * 100.0
            ),
        }
    )
    return result


def assert_step3_settings_match() -> None:
    """Fail before a long run if a shared Step 2/Step 3 setting has drifted."""
    spec = importlib.util.spec_from_file_location("step3_experiment_knobs", STEP3_KNOBS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Step 3 knobs from {STEP3_KNOBS_PATH}")
    step3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(step3)
    shared = [
        "FORECAST_MODEL_MAX_HORIZON_HOURS",
        "EVALUATION_CUTOFF_HORIZON_HOURS",
        "EXECUTION_STEP_HOURS",
        "REPLANNING_INTERVAL_HOURS",
        "STORAGE_POWER_MW",
        "STORAGE_DURATION_H",
        "RTE",
        "DOD",
        "GRID_CAP_MW",
        "INITIAL_SOC_MWH",
        "ANNUAL_TARGET_SOC_MWH",
        "FINAL_TARGET_SOC_MWH",
        "ANNUAL_SOC_SETTLEMENT_HOURS",
        "NOWCAST_FIRST_HOUR",
        "GATE_MARGIN",
        "APPLY_GATE_TO_SINGLE_FORECAST",
        "FALLBACK_TARGET_MW",
        "DIRECT_RESERVE_MW",
        "TRAIN_ORIGIN_STRIDE",
        "RESIDUAL_ORIGIN_STRIDE",
        "CALIBRATION_MODE",
        "FORECAST_TRAIN_END",
        "CALIBRATION_END",
        "MAX_ORIGINS",
    ]
    mismatches = [
        f"{name}: Step 2={getattr(knobs, name)!r}, Step 3={getattr(step3, name)!r}"
        for name in shared
        if getattr(knobs, name) != getattr(step3, name)
    ]
    if int(step3.HORIZON_HOURS) not in [int(value) for value in knobs.HORIZONS]:
        mismatches.append(f"Step 3 horizon {step3.HORIZON_HOURS} is missing from Step 2 HORIZONS")
    if mismatches:
        raise RuntimeError("Controlled Step 2/Step 3 settings do not match:\n  " + "\n  ".join(mismatches))


def add_optional(command: list[str], flag: str, value) -> None:
    if value is not None:
        command.extend([flag, str(value)])


def command(horizon: int, out_dir: Path) -> list[str]:
    """Build the exact Step 3 single-forecast command for one horizon."""
    cmd = [
        sys.executable,
        str(CANONICAL_CONTROLLER),
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
        "single_recourse",
        "--out-dir",
        str(out_dir),
    ]
    add_optional(cmd, "--initial-soc-mwh", knobs.INITIAL_SOC_MWH)
    add_optional(cmd, "--annual-target-soc-mwh", knobs.ANNUAL_TARGET_SOC_MWH)
    add_optional(cmd, "--final-target-soc-mwh", knobs.FINAL_TARGET_SOC_MWH)
    add_optional(cmd, "--annual-soc-settlement-hours", knobs.ANNUAL_SOC_SETTLEMENT_HOURS)
    add_optional(cmd, "--max-origins", knobs.MAX_ORIGINS)
    add_optional(cmd, "--gate-margin", knobs.GATE_MARGIN)
    if knobs.APPLY_GATE_TO_SINGLE_FORECAST:
        cmd.append("--gate-single-forecast")
    cmd.append("--nowcast-first-hour" if knobs.NOWCAST_FIRST_HOUR else "--no-nowcast-first-hour")
    return cmd


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing result file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def single_row(summary_path: Path) -> dict[str, str]:
    rows = [
        row
        for row in load_rows(summary_path)
        if row.get("candidate", "").startswith("single_forecast_recourse")
    ]
    if len(rows) != 1:
        raise RuntimeError(f"Expected one single-forecast row in {summary_path}; found {len(rows)}")
    return rows[0]


def labels_name() -> str:
    suffix = "_nowcast" if knobs.NOWCAST_FIRST_HOUR else ""
    if knobs.GATE_MARGIN is not None and knobs.APPLY_GATE_TO_SINGLE_FORECAST:
        suffix += "_gated"
    return f"single_forecast_recourse{suffix}_labels.csv"


def run_or_load_horizons() -> list[dict[str, str]]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FULL_HOURLY.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []

    for horizon in knobs.HORIZONS:
        horizon = int(horizon)
        horizon_dir = RESULTS / f"horizon_{horizon}h"
        cmd = command(horizon, horizon_dir)
        print(f"\n{horizon} h controlled command:")
        print(" ".join(map(str, cmd)))
        reuse = horizon in set(getattr(knobs, "REUSE_COMPLETED_HORIZONS", []))
        if knobs.RERUN_FROM_SOURCE and not reuse:
            subprocess.run(cmd, cwd=SCENARIO_FOLDER, check=True)
        elif reuse:
            print(f"Reusing completed {horizon} h source rerun after QA validation.")

        summary_path = horizon_dir / "uncertainty_aware_summary.csv"
        if not summary_path.exists():
            raise FileNotFoundError(
                f"{summary_path} does not exist. Set RERUN_FROM_SOURCE = True to create the controlled result."
            )
        row = normalize_cove_metrics(single_row(summary_path))
        row["horizon_hours"] = str(horizon)
        row["controller_protocol"] = "hourly nowcast + gated recourse + 75 MW direct reserve"
        row["source_summary_file"] = str(summary_path)
        rows.append(row)
        write_rows(summary_path, [row])

        labels_path = horizon_dir / labels_name()
        if labels_path.exists():
            shutil.copy2(labels_path, FULL_HOURLY / f"single_forecast_{horizon}h_hourly.csv")

    rows.sort(key=lambda row: int(float(row["horizon_hours"])))
    write_rows(SUMMARY_FILE, rows)
    write_rows(SUMMARY_ALIAS, rows)
    return rows


def draw_figures(rows: list[dict[str, str]]) -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    horizons = [int(float(row["horizon_hours"])) for row in rows]
    gains = [float(row["cove_reduction_vs_100mw_baseload_pct"]) for row in rows]
    coves = [float(row["dispatch_cove_index"]) for row in rows]
    revenues = [float(row["dispatch_revenue"]) / 1e6 for row in rows]
    benchmark_cove = float(rows[0]["100mw_baseload_cove"])
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    ax.plot(horizons, gains, marker="o", linewidth=2.6, color="#2563EB")
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_title("Controlled Hourly-Replan Horizon Comparison", fontweight="bold")
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.grid(color="#E5E7EB")
    ax.set_axisbelow(True)
    for x_value, y_value in zip(horizons, gains):
        ax.annotate(f"{y_value:.2f}%", (x_value, y_value), xytext=(0, 8), textcoords="offset points", ha="center")
    fig.tight_layout()
    path = FIGURES / "step2_controlled_hourly_horizon_improvement.png"
    fig.savefig(path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    ax.plot(horizons, coves, marker="o", linewidth=2.6, color="#1D4ED8")
    ax.axhline(benchmark_cove, color="#6B7280", linestyle="--", label=f"100 MW benchmark = {benchmark_cove:.3f}")
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_title("Controlled COVE by Planning Horizon", fontweight="bold")
    ax.set_ylabel("COVE index (lower is better)")
    ax.legend(frameon=False)
    ax.grid(color="#E5E7EB")
    ax.set_axisbelow(True)
    fig.tight_layout()
    path = FIGURES / "step2_controlled_hourly_horizon_cove.png"
    fig.savefig(path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    bars = ax.bar([f"{h} h" for h in horizons], revenues, color="#0F766E")
    ax.set_title("Reported Revenue Metric by Controlled Planning Horizon", fontweight="bold")
    ax.set_ylabel("Normalized price-weighted revenue metric (millions)")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(revenues) * 1.12)
    for bar, value in zip(bars, revenues):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + max(revenues) * 0.015,
            f"{value:.2f}M",
            ha="center",
            fontsize=9,
        )
    fig.tight_layout()
    path = FIGURES / "step2_controlled_hourly_horizon_revenue.png"
    fig.savefig(path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    paths.append(path)
    return paths


def report_step3_equivalence(step2_rows: list[dict[str, str]]) -> None:
    spec = importlib.util.spec_from_file_location("step3_equivalence_knobs", STEP3_KNOBS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Step 3 knobs from {STEP3_KNOBS_PATH}")
    step3_knobs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(step3_knobs)
    selected_horizon = int(step3_knobs.HORIZON_HOURS)
    step2_selected = next(
        (row for row in step2_rows if int(float(row["horizon_hours"])) == selected_horizon),
        None,
    )
    if step2_selected is None or not STEP3_SUMMARY.exists():
        print("\nStep 2/Step 3 equality check: Step 3 controlled output is not available yet.")
        return
    step3_selected = normalize_cove_metrics(single_row(STEP3_SUMMARY))
    checks = ["hours", "test_start", "test_end", "dispatch_revenue", "dispatch_cove_index", "final_soc"]
    exact = all(step2_selected.get(key) == step3_selected.get(key) for key in checks)
    print(f"\nStep 2 {selected_horizon} h vs Step 3 one-forecast equality check:")
    print("  MATCH" if exact else "  NOT YET MATCHED: rerun Step 3 with its updated controlled knobs.")
    for key in checks:
        print(f"  {key}: Step 2={step2_selected.get(key)} | Step 3={step3_selected.get(key)}")


def main() -> None:
    assert_step3_settings_match()
    print("STEP 2: CONTROLLED CAUSAL-RIDGE HORIZON COMPARISON")
    print("Canonical controller: Step 3 run_uncertainty_aware_dispatch.py with one forecast only.")
    print("Execution: first hour, then replan; current-hour nowcast; identical gate, reserve, and CAES settings.")
    print("Primary benchmark: 100-MW Constant-Output Baseload Benchmark.")
    print("The selected-horizon row must equal the Step 3 one-forecast row after both controlled reruns.\n")

    if not knobs.RERUN_FROM_SOURCE:
        print("RERUN_FROM_SOURCE is False; reading an existing controlled run.")
    rows = run_or_load_horizons()

    benchmark_revenue = float(rows[0]["100mw_baseload_revenue"])
    benchmark_cove = float(rows[0]["100mw_baseload_cove"])
    print(f"\n100 MW benchmark revenue: {benchmark_revenue:,.2f}")
    print(f"100 MW benchmark COVE:    {benchmark_cove:.6f}\n")
    print(f"{'Horizon':>9} {'COVE':>12} {'COVE reduction':>16} {'Revenue metric':>20} {'Final SoC':>12}")
    print("-" * 75)
    for row in rows:
        print(
            f"{int(float(row['horizon_hours'])):>6} h "
            f"{float(row['dispatch_cove_index']):>12.6f} "
            f"{float(row['cove_reduction_vs_100mw_baseload_pct']):>15.2f}% "
            f"{float(row['dispatch_revenue']):>20,.2f} "
            f"{float(row['final_soc']):>12.2f}"
        )

    best = max(rows, key=lambda row: float(row["cove_reduction_vs_100mw_baseload_pct"]))
    print(
        f"\nBest controlled horizon: {int(float(best['horizon_hours']))} h, "
        f"{float(best['cove_reduction_vs_100mw_baseload_pct']):.2f}% COVE reduction vs 100 MW benchmark"
    )

    wind_revenue = float(rows[0]["wind_only_revenue"])
    wind_cove = float(rows[0]["wind_only_cove_index"])
    print("\nSecondary reference: wind-only/no storage")
    print(f"Wind-only revenue: {wind_revenue:,.2f}")
    print(f"Wind-only COVE:    {wind_cove:.6f}")
    for row in rows:
        print(
            f"  {int(float(row['horizon_hours'])):>3} h: "
            f"{float(row['revenue_gain_vs_wind_only_pct']):>7.2f}% revenue gain; "
            f"{float(row['cove_reduction_vs_wind_only_pct']):>7.2f}% COVE reduction"
        )

    report_step3_equivalence(rows)
    figures = draw_figures(rows)
    print("\nFiles written:")
    print(f"  {SUMMARY_FILE}")
    print(f"  {SUMMARY_ALIAS}")
    print(f"  {FULL_HOURLY}")
    print("Figures written:")
    for path in figures:
        print(f"  {path}")


if __name__ == "__main__":
    main()
