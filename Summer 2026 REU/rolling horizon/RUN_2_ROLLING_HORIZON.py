#!/usr/bin/env python3
"""Step 2 of the Summer 2026 REU ladder: deterministic rolling horizon.

Run from this folder:
    ../../venv/bin/python RUN_2_ROLLING_HORIZON.py

This is the final 100 MW / 10-hour CAES deterministic dispatch experiment. It uses the
causal ridge forecast, sends that forecast to Gurobi, executes the first
24 hours, carries the battery state forward, and replans the next day.
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
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
SUMMARY_FILE = RESULTS / "forecast_dispatch_summary.csv"
SUMMARY_ALIAS = HERE / "results" / "causal_ridge_rolling_horizon_summary.csv"
SOURCE_RUNNER = HERE / "code" / "forecast_backtest_rolling_horizons.py"


def add_optional(command: list[str], flag: str, value) -> None:
    if value is not None:
        command.extend([flag, str(value)])


def command() -> list[str]:
    cmd = [
        sys.executable,
        str(SOURCE_RUNNER),
        "--data",
        str(knobs.DATA),
        "--config",
        str(knobs.CONFIG),
        "--train-end",
        str(knobs.TRAIN_END),
        "--alpha",
        str(knobs.ALPHA),
        "--train-origin-stride",
        str(knobs.TRAIN_ORIGIN_STRIDE),
        "--mip-gap",
        str(knobs.MIP_GAP),
        "--storage-power-mw",
        str(knobs.STORAGE_POWER_MW),
        "--storage-duration-h",
        str(knobs.STORAGE_DURATION_H),
        "--grid-cap-mw",
        str(knobs.GRID_CAP_MW),
        "--initial-soc",
        str(knobs.INITIAL_SOC_MWH),
        "--min-soc-frac",
        str(knobs.MIN_SOC_FRAC),
        "--max-soc-frac",
        str(knobs.MAX_SOC_FRAC),
        "--execution-step-hours",
        str(knobs.EXECUTION_STEP_HOURS),
        "--replanning-interval-hours",
        str(knobs.REPLANNING_INTERVAL_HOURS),
        "--terminal-policy",
        str(knobs.TERMINAL_POLICY),
        "--primary-baseline-storage-duration-h",
        str(knobs.PRIMARY_BASELINE_STORAGE_DURATION_H),
        "--direct-reserve-mw",
        str(knobs.DIRECT_RESERVE_MW),
        "--horizons",
        *[str(horizon) for horizon in knobs.HORIZONS],
        "--out-dir",
        str(RESULTS),
    ]
    add_optional(cmd, "--test-end", knobs.TEST_END)
    if not knobs.RUN_ORACLE_CONTEXT:
        cmd.append("--skip-oracle")
    return cmd


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def copy_outputs() -> None:
    SUMMARY_ALIAS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SUMMARY_FILE, SUMMARY_ALIAS)
    FULL_HOURLY.mkdir(parents=True, exist_ok=True)
    for csv_file in RESULTS.glob("*dispatch_*h.csv"):
        shutil.copy2(csv_file, FULL_HOURLY / csv_file.name)


def cove_gain_vs_wind(row: dict[str, str]) -> float:
    return float(row.get("cove_improvement_vs_wind_only_pct", row["improvement_vs_baseload_pct"]))


def cove_gain_vs_100mw(row: dict[str, str]) -> float | None:
    value = row.get("cove_improvement_vs_100mw_baseload_pct")
    return None if value in (None, "") else float(value)


def raw_revenue_gain_vs_wind(row: dict[str, str]) -> float | None:
    value = row.get("raw_revenue_gain_vs_wind_only_pct")
    return None if value in (None, "") else float(value)


def raw_revenue_gain_vs_100mw(row: dict[str, str]) -> float | None:
    value = row.get("raw_revenue_gain_vs_100mw_baseload_pct")
    return None if value in (None, "") else float(value)


def draw_figures(causal: list[dict[str, str]], oracle: list[dict[str, str]]) -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    horizons = [int(float(row["horizon_hours"])) for row in causal]
    cove = [float(row["cove"]) for row in causal]
    gains = [cove_gain_vs_100mw(row) or 0.0 for row in causal]
    revenue = [float(row["revenue_metric"]) / 1e6 for row in causal]
    benchmark_cove = float(causal[0]["constant_output_100mw_cove"])

    out_paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    bars = ax.bar([f"{h} h" for h in horizons], gains, color="#2563EB")
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_title("Deterministic Forecast-Driven RH MILP: COVE Reduction vs 100 MW Benchmark", fontweight="bold")
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.2, f"{value:.2f}%", ha="center", fontsize=9)
    fig.tight_layout()
    out = FIGURES / "step2_causal_horizon_improvement.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    ax.plot(horizons, cove, marker="o", linewidth=2.5, color="#1D4ED8")
    ax.axhline(benchmark_cove, color="#6B7280", linestyle="--", label=f"100 MW benchmark COVE = {benchmark_cove:.3f}")
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_title("COVE by Planning Window", fontweight="bold")
    ax.set_ylabel("COVE (lower is better)")
    ax.legend(frameon=False)
    ax.grid(color="#E5E7EB")
    ax.set_axisbelow(True)
    for x_value, y_value in zip(horizons, cove):
        ax.text(x_value, y_value + 0.025, f"{y_value:.3f}", ha="center", fontsize=9)
    fig.tight_layout()
    out = FIGURES / "step2_causal_horizon_cove.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    bars = ax.bar([f"{h} h" for h in horizons], revenue, color="#0F766E")
    ax.set_title("Reported Revenue Metric by Horizon", fontweight="bold")
    ax.set_ylabel("Revenue metric ($ millions)")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, revenue):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.05, f"${value:.2f}M", ha="center", fontsize=9)
    fig.tight_layout()
    out = FIGURES / "step2_revenue_by_horizon.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    if oracle:
        oracle_h = [int(float(row["horizon_hours"])) for row in oracle]
        oracle_g = [cove_gain_vs_100mw(row) or 0.0 for row in oracle]
        fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
        ax.plot(horizons, gains, marker="o", linewidth=2.5, label="Causal forecast", color="#2563EB")
        ax.plot(oracle_h, oracle_g, marker="o", linewidth=2.5, label="Oracle future information", color="#6B7280")
        ax.set_xticks(horizons, [f"{h} h" for h in horizons])
        ax.set_title("Causal Result vs Oracle Context", fontweight="bold")
        ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
        ax.legend(frameon=False)
        ax.grid(color="#E5E7EB")
        ax.set_axisbelow(True)
        fig.tight_layout()
        out = FIGURES / "step2_causal_vs_oracle_context.png"
        fig.savefig(out, facecolor="white", bbox_inches="tight")
        plt.close(fig)
        out_paths.append(out)

    return out_paths


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    print("STEP 2: CAUSAL RIDGE + DAILY ROLLING-HORIZON GUROBI")
    print("This is the final 100 MW / 10-hour CAES deterministic result.")
    print("Primary comparison: 100-MW Constant-Output Baseload Benchmark.")
    print("Wind-only baseline is printed at the bottom as secondary reference only.")
    print("Execution rule: solve a multi-hour horizon, execute first 24 hours, then replan.")
    print()
    cmd = command()
    print("Command:")
    print(" ".join(map(str, cmd)))
    print()
    if knobs.RERUN_FROM_SOURCE:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    else:
        print("RERUN_FROM_SOURCE is False, so I am reading the existing frozen CSV.")

    copy_outputs()
    rows = load_rows(SUMMARY_FILE)
    causal = sorted(
        [row for row in rows if row["method"] == "causal_forecast_direct_reserve"],
        key=lambda row: int(float(row["horizon_hours"])),
    )
    oracle = sorted(
        [row for row in rows if row["method"] == "oracle"],
        key=lambda row: int(float(row["horizon_hours"])),
    )
    if not causal:
        raise RuntimeError("No causal_forecast_direct_reserve rows were generated.")

    benchmark_revenue = float(causal[0]["constant_output_100mw_revenue_metric"])
    benchmark_cove = float(causal[0]["constant_output_100mw_cove"])
    print(f"100 MW benchmark revenue metric: {benchmark_revenue:,.2f}")
    print(f"100 MW benchmark COVE:           {benchmark_cove:.6f}")
    print()
    print(f"{'Planning':>10} {'COVE':>10} {'COVE reduction %':>12} {'Revenue metric':>18} {'Raw rev gain':>13} {'Final SoC':>12}")
    print("-" * 86)
    for row in causal:
        raw_gain = raw_revenue_gain_vs_100mw(row)
        print(
            f"{int(float(row['horizon_hours'])):>6} h "
            f"{float(row['cove']):>10.6f} "
            f"{(cove_gain_vs_100mw(row) or 0.0):>12.2f} "
            f"{float(row['revenue_metric']):>18,.2f} "
            f"{'' if raw_gain is None else f'{raw_gain:.2f}%':>13} "
            f"{float(row['final_soc']):>12.2f}"
        )

    best = max(causal, key=lambda row: cove_gain_vs_100mw(row) or float("-inf"))
    print("\nBest deterministic case:")
    print(
        f"  {int(float(best['horizon_hours']))} h, "
        f"{(cove_gain_vs_100mw(best) or 0.0):.2f}% COVE reduction vs 100 MW benchmark"
    )

    wind_revenue = float(causal[0].get("wind_only_revenue_metric", causal[0]["baseload_revenue_metric"]))
    wind_cove = float(causal[0].get("wind_only_cove", causal[0]["baseload_cove"]))
    print("\nSecondary reference only: Wind-only baseline")
    print("No storage; actual wind delivered directly up to the 249 MW grid cap.")
    print(f"Wind-only revenue metric: {wind_revenue:,.2f}")
    print(f"Wind-only COVE:           {wind_cove:.6f}")
    print(f"{'Planning':>10} {'COVE reduction vs wind-only':>24} {'Raw rev gain vs wind-only':>28}")
    print("-" * 66)
    for row in causal:
        raw_gain_wind = raw_revenue_gain_vs_wind(row)
        print(
            f"{int(float(row['horizon_hours'])):>6} h "
            f"{cove_gain_vs_wind(row):>24.2f}% "
            f"{'' if raw_gain_wind is None else f'{raw_gain_wind:.2f}%':>28}"
        )

    if oracle:
        best_oracle = max(oracle, key=lambda row: cove_gain_vs_100mw(row) or float("-inf"))
        print("\nOracle context only:")
        print(
            f"  {int(float(best_oracle['horizon_hours']))} h, "
            f"{(cove_gain_vs_100mw(best_oracle) or 0.0):.2f}% COVE reduction vs 100 MW benchmark"
        )

    figures = draw_figures(causal, oracle)
    print("\nFiles updated:")
    print(f"  {SUMMARY_ALIAS}")
    print(f"  {RESULTS / 'forecast_dispatch_summary.csv'}")
    print(f"  {FULL_HOURLY}")
    print("\nFigures saved:")
    for path in figures:
        print(f"  {path}")


if __name__ == "__main__":
    main()
