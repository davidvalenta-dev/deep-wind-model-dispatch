#!/usr/bin/env python3
"""Step 4 of the Summer 2026 REU ladder: oracle upper bound.

Run from this folder:
    ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py

This is the final 100 MW / 10-hour CAES oracle table. The oracle gives Gurobi the realized
future wind and realized future price, so it is not deployable. It is included
only to show the upper bound.
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
ORACLE_ONLY_FILE = HERE / "results" / "oracle_upper_bound_summary.csv"
SOURCE_RUNNER = HERE / "code" / "forecast_backtest_rolling_horizons.py"


def add_optional(command: list[str], flag: str, value) -> None:
    if value is not None:
        command.extend([flag, str(value)])


def command(
    out_dir: Path,
    horizons: list[int],
    execution_step_hours: int,
    replanning_interval_hours: int,
    terminal_policy: str,
) -> list[str]:
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
        str(execution_step_hours),
        "--replanning-interval-hours",
        str(replanning_interval_hours),
        "--terminal-policy",
        str(terminal_policy),
        "--primary-baseline-storage-duration-h",
        str(knobs.PRIMARY_BASELINE_STORAGE_DURATION_H),
        "--direct-reserve-mw",
        "0",
        "--oracle-only",
        "--horizons",
        *[str(horizon) for horizon in horizons],
        "--out-dir",
        str(out_dir),
    ]
    add_optional(cmd, "--test-end", knobs.TEST_END)
    return cmd


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def copy_outputs() -> None:
    FULL_HOURLY.mkdir(parents=True, exist_ok=True)
    for csv_file in RESULTS.glob("oracle_dispatch_*h.csv"):
        shutil.copy2(csv_file, FULL_HOURLY / csv_file.name)


def save_oracle_only(rows: list[dict[str, str]]) -> None:
    ORACLE_ONLY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ORACLE_ONLY_FILE.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


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


def draw_figures(rows: list[dict[str, str]]) -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    horizons = [int(float(row["horizon_hours"])) for row in rows]
    cove = [float(row["cove"]) for row in rows]
    gains = [cove_gain_vs_100mw(row) or 0.0 for row in rows]
    revenue = [float(row["revenue_metric"]) / 1e6 for row in rows]
    runtime = [float(row["solver_runtime_seconds"]) for row in rows]
    baseline_cove = float(rows[0]["constant_output_100mw_cove"])

    out_paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    bars = ax.bar([f"{h} h" for h in horizons], gains, color="#B91C1C")
    ax.set_title("Daily-Replan Oracle: COVE Gain vs 100 MW Benchmark", fontweight="bold")
    ax.set_ylabel("COVE gain vs 100 MW benchmark (%)")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.25, f"{value:.2f}%", ha="center", fontsize=9)
    fig.tight_layout()
    out = FIGURES / "step4_oracle_improvement_by_horizon.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    ax.plot(horizons, cove, marker="o", linewidth=2.5, color="#B91C1C")
    ax.axhline(baseline_cove, color="#6B7280", linestyle="--", label=f"100 MW benchmark COVE = {baseline_cove:.3f}")
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_title("Daily-Replan Oracle COVE by Horizon", fontweight="bold")
    ax.set_ylabel("COVE (lower is better)")
    ax.legend(frameon=False)
    ax.grid(color="#E5E7EB")
    ax.set_axisbelow(True)
    for x_value, y_value in zip(horizons, cove):
        ax.text(x_value, y_value + 0.03, f"{y_value:.3f}", ha="center", fontsize=9)
    fig.tight_layout()
    out = FIGURES / "step4_oracle_cove_by_horizon.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    ax.scatter(runtime, gains, s=[70 + h for h in horizons], color="#DC2626", alpha=0.85)
    for h, x_value, y_value in zip(horizons, runtime, gains):
        ax.annotate(f"{h} h", (x_value, y_value), xytext=(7, 5), textcoords="offset points")
    ax.set_title("Oracle Runtime vs Value", fontweight="bold")
    ax.set_xlabel("Solver runtime (seconds)")
    ax.set_ylabel("COVE gain vs 100 MW benchmark (%)")
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    out = FIGURES / "step4_oracle_runtime_value_tradeoff.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    fig = plt.figure(figsize=(8.4, 6.2), dpi=200)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(horizons, revenue, cove, color="#B91C1C", linewidth=2.2)
    ax.scatter(horizons, revenue, cove, color="#111827", s=55)
    for h, rev, cove_value in zip(horizons, revenue, cove):
        ax.text(h, rev, cove_value, f"{h}h", fontsize=9)
    ax.set_xlabel("Lookahead (h)")
    ax.set_ylabel("Revenue metric ($M)")
    ax.set_zlabel("COVE")
    ax.set_title("3D Oracle Revenue-COVE View", fontweight="bold")
    ax.view_init(elev=24, azim=-52)
    fig.tight_layout()
    out = FIGURES / "step4_3d_oracle_revenue_cove.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    return out_paths


def draw_daily_hourly_figures(
    daily_rows: list[dict[str, str]],
    hourly_rows: list[dict[str, str]],
) -> list[Path]:
    if not daily_rows or not hourly_rows:
        return []
    out_paths: list[Path] = []
    daily_168 = next((row for row in daily_rows if int(float(row["horizon_hours"])) == 168), daily_rows[-1])
    hourly_168 = hourly_rows[-1]
    labels = ["Daily replan\n168 h", "Hourly replan\n168 h"]
    gains = [
        cove_gain_vs_100mw(daily_168) or 0.0,
        cove_gain_vs_100mw(hourly_168) or 0.0,
    ]
    coves = [float(daily_168["cove"]), float(hourly_168["cove"])]
    revenues = [float(daily_168["revenue_metric"]) / 1e6, float(hourly_168["revenue_metric"]) / 1e6]

    fig, ax = plt.subplots(figsize=(8.2, 5.0), dpi=200)
    bars = ax.bar(labels, gains, color=["#F97316", "#B91C1C"])
    ax.set_ylabel("COVE gain vs 100 MW benchmark (%)")
    ax.set_title("Oracle Replanning Frequency: Daily vs Hourly", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.25, f"{value:.2f}%", ha="center", fontsize=10)
    fig.tight_layout()
    out = FIGURES / "step4_daily_vs_hourly_oracle_gain.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)

    fig, ax1 = plt.subplots(figsize=(8.6, 5.0), dpi=200)
    x = range(len(labels))
    ax1.bar([value - 0.18 for value in x], revenues, width=0.36, color="#DC2626", label="Revenue metric")
    ax2 = ax1.twinx()
    ax2.plot(list(x), coves, marker="o", color="#111827", linewidth=2.4, label="COVE")
    ax1.set_xticks(list(x), labels)
    ax1.set_ylabel("Revenue metric ($M)")
    ax2.set_ylabel("COVE (lower is better)")
    ax1.set_title("Oracle Ceiling: Revenue and COVE", fontweight="bold")
    ax1.grid(axis="y", color="#E5E7EB")
    for idx, value in enumerate(revenues):
        ax1.text(idx - 0.18, value + 0.05, f"${value:.2f}M", ha="center", fontsize=9)
    for idx, value in enumerate(coves):
        ax2.text(idx + 0.06, value + 0.01, f"{value:.3f}", ha="left", fontsize=9)
    fig.tight_layout()
    out = FIGURES / "step4_oracle_daily_hourly_revenue_cove.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    out_paths.append(out)
    return out_paths


def print_oracle_block(title: str, rows: list[dict[str, str]]) -> None:
    if not rows:
        print(f"\n{title}: no rows found.")
        return
    benchmark_revenue = float(rows[0]["constant_output_100mw_revenue_metric"])
    benchmark_cove = float(rows[0]["constant_output_100mw_cove"])
    print(f"\n{title}")
    print("Primary comparison: 100-MW Constant-Output Baseload Benchmark.")
    print(f"100 MW benchmark revenue metric: {benchmark_revenue:,.2f}")
    print(f"100 MW benchmark COVE:           {benchmark_cove:.6f}")
    print()
    print(f"{'Horizon':>8} {'COVE':>10} {'COVE gain %':>12} {'Revenue metric':>18} {'Raw rev gain':>13} {'Final SoC':>12}")
    print("-" * 86)
    for row in rows:
        raw_gain = raw_revenue_gain_vs_100mw(row)
        print(
            f"{int(float(row['horizon_hours'])):>6} h "
            f"{float(row['cove']):>10.6f} "
            f"{(cove_gain_vs_100mw(row) or 0.0):>12.2f} "
            f"{float(row['revenue_metric']):>18,.2f} "
            f"{'' if raw_gain is None else f'{raw_gain:.2f}%':>13} "
            f"{float(row['final_soc']):>12.2f}"
        )

    best = max(rows, key=lambda row: cove_gain_vs_100mw(row) or float("-inf"))
    print("\nBest in this oracle block:")
    print(
        f"  {int(float(best['horizon_hours']))} h, "
        f"{(cove_gain_vs_100mw(best) or 0.0):.2f}% COVE gain vs 100 MW benchmark"
    )

    wind_revenue = float(rows[0].get("wind_only_revenue_metric", rows[0]["baseload_revenue_metric"]))
    wind_cove = float(rows[0].get("wind_only_cove", rows[0]["baseload_cove"]))
    print("\nSecondary reference only: Wind-only baseline")
    print("No storage; actual wind delivered directly up to the 249 MW grid cap.")
    print(f"Wind-only revenue metric: {wind_revenue:,.2f}")
    print(f"Wind-only COVE:           {wind_cove:.6f}")
    print(f"{'Horizon':>8} {'COVE gain vs wind-only':>24} {'Raw rev gain vs wind-only':>28}")
    print("-" * 66)
    for row in rows:
        raw_gain_wind = raw_revenue_gain_vs_wind(row)
        print(
            f"{int(float(row['horizon_hours'])):>6} h "
            f"{cove_gain_vs_wind(row):>24.2f}% "
            f"{'' if raw_gain_wind is None else f'{raw_gain_wind:.2f}%':>28}"
        )


def run_or_read(out_dir: Path, cmd: list[str], enabled: bool) -> list[dict[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    print("Command:")
    print(" ".join(map(str, cmd)))
    print()
    if enabled:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    else:
        print("RERUN_FROM_SOURCE is False, so I am reading the existing frozen CSV.")
    rows = load_rows(out_dir / "forecast_dispatch_summary.csv")
    oracle = sorted(
        [row for row in rows if row["method"] == "oracle"],
        key=lambda row: int(float(row["horizon_hours"])),
    )
    return oracle


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    print("STEP 4: ORACLE UPPER BOUND")
    print("This uses the final 100 MW / 10-hour CAES storage setup.")
    print("Primary comparison: 100-MW Constant-Output Baseload Benchmark.")
    print("Wind-only appears only as the secondary reference at the bottom of each block.")
    print("There are two oracle views:")
    print("  1. Daily-replan oracle: execute first 24 hours, then replan.")
    print("  2. Hourly-replan oracle ceiling: execute first hour, then replan.")
    print()

    daily_cmd = command(
        RESULTS,
        list(knobs.HORIZONS),
        int(knobs.EXECUTION_STEP_HOURS),
        int(knobs.REPLANNING_INTERVAL_HOURS),
        str(knobs.TERMINAL_POLICY),
    )
    daily_oracle = run_or_read(RESULTS, daily_cmd, getattr(knobs, "RERUN_FROM_SOURCE", False))
    if not daily_oracle:
        raise RuntimeError("No daily-replan oracle rows were found.")
    save_oracle_only(daily_oracle)
    copy_outputs()
    print_oracle_block("DAILY-REPLAN ORACLE (execute 24 hours, then replan)", daily_oracle)

    hourly_dir = Path(knobs.HOURLY_CEILING_OUTPUT_DIR)
    hourly_cmd = command(
        hourly_dir,
        [int(knobs.HOURLY_CEILING_HORIZON)],
        int(knobs.HOURLY_CEILING_EXECUTION_STEP_HOURS),
        int(knobs.HOURLY_CEILING_REPLANNING_INTERVAL_HOURS),
        str(knobs.HOURLY_CEILING_TERMINAL_POLICY),
    )
    print("\nHOURLY-REPLAN ORACLE CEILING COMMAND")
    hourly_oracle = run_or_read(hourly_dir, hourly_cmd, getattr(knobs, "RUN_HOURLY_168H_CEILING", False))
    if hourly_oracle:
        hourly_summary_file = hourly_dir / "oracle_hourly_168h_ceiling_summary.csv"
        with hourly_summary_file.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(hourly_oracle[0].keys()))
            writer.writeheader()
            writer.writerows(hourly_oracle)
        print_oracle_block("HOURLY-REPLAN ORACLE CEILING (execute 1 hour, then replan)", hourly_oracle)

    print("\nMeaning:")
    print("  Oracle is not realistic because it knows future wind and future price.")
    print("  Daily oracle matches the ladder's daily execution style.")
    print("  Hourly oracle is a separate perfect-information ceiling.")

    figures = draw_figures(daily_oracle)
    figures.extend(draw_daily_hourly_figures(daily_oracle, hourly_oracle))
    print("\nFiles updated:")
    print(f"  {ORACLE_ONLY_FILE}")
    if hourly_oracle:
        print(f"  {Path(knobs.HOURLY_CEILING_OUTPUT_DIR) / 'oracle_hourly_168h_ceiling_summary.csv'}")
    print(f"  {FULL_HOURLY}")
    print("\nFigures saved:")
    for path in figures:
        print(f"  {path}")


if __name__ == "__main__":
    main()
