#!/usr/bin/env python3
"""Step 2 of the Summer 2026 REU ladder: causal forecast rolling horizon.

Run from this folder:
    ../../venv/bin/python RUN_2_ROLLING_HORIZON.py

This reruns the causal ridge + direct-reserve Gurobi result using the settings
in EXPERIMENT_KNOBS.py. Gurobi gets a forecast window, executes only the first
24 hours, carries the battery state forward, and repeats.
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
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

import EXPERIMENT_KNOBS as knobs


RESULTS = Path(knobs.OUTPUT_DIR)
FIGURES = HERE / "figures"
SUMMARY_FILE = RESULTS / "forecast_dispatch_summary.csv"
RUNNER = HERE / "code" / "forecast_backtest_rolling_horizons.py"


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required result file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def fmt_money(value: str) -> str:
    return f"{float(value):,.2f}"


def add_optional(cmd: list[str], flag: str, value) -> None:
    if value is not None:
        cmd.extend([flag, str(value)])


def rerun_from_knobs() -> None:
    cmd = [
        sys.executable,
        str(RUNNER),
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
        "--min-soc-frac",
        str(knobs.MIN_SOC_FRAC),
        "--max-soc-frac",
        str(knobs.MAX_SOC_FRAC),
        "--direct-reserve-mw",
        str(knobs.DIRECT_RESERVE_MW),
        "--horizons",
        *[str(horizon) for horizon in knobs.HORIZONS],
        "--out-dir",
        str(RESULTS),
    ]
    add_optional(cmd, "--test-end", knobs.TEST_END)
    add_optional(cmd, "--initial-soc", knobs.INITIAL_SOC_MWH)
    if not knobs.RUN_ORACLE_CONTEXT:
        cmd.append("--skip-oracle")
    print("Running rolling-horizon Gurobi command from EXPERIMENT_KNOBS.py:")
    print(" ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=HERE, check=True)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    rerun_from_knobs()
    all_rows = load_rows(SUMMARY_FILE)
    causal = [
        row for row in all_rows
        if row["method"] == "causal_forecast_direct_reserve"
    ]
    oracle = [row for row in all_rows if row["method"] == "oracle"]
    causal = sorted(causal, key=lambda row: int(float(row["horizon_hours"])))
    oracle = sorted(oracle, key=lambda row: int(float(row["horizon_hours"])))
    if not causal:
        raise RuntimeError("No causal_forecast_direct_reserve rows found.")

    baseload_cove = float(causal[0]["baseload_cove"])
    baseload_revenue = float(causal[0]["baseload_revenue_metric"])

    print("\nSTEP 2: CAUSAL RIDGE + ROLLING-HORIZON GUROBI")
    print("Compared against baseload. COVE improvement is positive when COVE is lower.\n")
    print(f"Baseload revenue metric: {baseload_revenue:,.2f}")
    print(f"Baseload COVE:           {baseload_cove:.6f}\n")
    print(
        f"{'Horizon':>8} {'Reserve':>9} {'COVE':>10} {'COVE gain %':>12} "
        f"{'Revenue metric':>18} {'Final SoC':>12}"
    )
    print("-" * 80)
    for row in causal:
        print(
            f"{int(float(row['horizon_hours'])):>6} h "
            f"{float(row['direct_reserve_mw']):>7.0f} MW "
            f"{float(row['cove']):>10.6f} "
            f"{float(row['improvement_vs_baseload_pct']):>12.2f} "
            f"{fmt_money(row['revenue_metric']):>18} "
            f"{float(row['final_soc']):>12.2f}"
        )

    best = max(causal, key=lambda row: float(row["improvement_vs_baseload_pct"]))
    print("\nBest realistic causal rolling-horizon case:")
    print(
        f"  {int(float(best['horizon_hours']))} h horizon, "
        f"{float(best['improvement_vs_baseload_pct']):.2f}% COVE improvement vs baseload"
    )
    print("\nMeaning:")
    print("  48 hours was best because it looked far enough ahead to use storage,")
    print("  but not so far that forecast errors overwhelmed the plan.")

    horizons = [int(float(row["horizon_hours"])) for row in causal]
    gains = [float(row["improvement_vs_baseload_pct"]) for row in causal]
    cove = [float(row["cove"]) for row in causal]
    revenue = [float(row["revenue_metric"]) for row in causal]
    runtime = [float(row["solver_runtime_seconds"]) for row in causal]

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=180)
    bars = ax.bar([f"{h} h" for h in horizons], gains, color="#2563EB")
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_ylabel("COVE improvement vs baseload (%)")
    ax.set_title("Causal Ridge + Rolling-Horizon Gurobi", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.12, f"{value:.2f}%", ha="center")
    fig.tight_layout()
    out1 = FIGURES / "step2_causal_horizon_improvement.png"
    fig.savefig(out1, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=180)
    ax.plot(horizons, cove, marker="o", linewidth=2.8, color="#1D4ED8")
    ax.axhline(baseload_cove, color="#6B7280", linestyle="--", label="Baseload COVE")
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_ylabel("COVE (lower is better)")
    ax.set_title("Realistic Forecast COVE by Horizon", fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(color="#E5E7EB")
    ax.set_axisbelow(True)
    for x, y in zip(horizons, cove):
        ax.text(x, y + 0.025, f"{y:.3f}", ha="center")
    fig.tight_layout()
    out2 = FIGURES / "step2_causal_horizon_cove.png"
    fig.savefig(out2, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=180)
    bars = ax.bar([f"{h} h" for h in horizons], [value / 1e6 for value in revenue], color="#0F766E")
    ax.set_ylabel("Revenue metric (millions)")
    ax.set_title("Realized Revenue by Planning Horizon", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, revenue):
        ax.text(bar.get_x() + bar.get_width() / 2, value / 1e6 + 0.025, f"{value/1e6:.2f}M", ha="center")
    fig.tight_layout()
    out3 = FIGURES / "step2_revenue_by_horizon.png"
    fig.savefig(out3, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=180)
    ax.scatter(runtime, gains, s=[80 + h for h in horizons], color="#7C3AED", alpha=0.85)
    for h, x_value, y_value in zip(horizons, runtime, gains):
        ax.annotate(f"{h} h", (x_value, y_value), xytext=(7, 5), textcoords="offset points")
    ax.set_xlabel("Solver runtime (seconds)")
    ax.set_ylabel("COVE improvement vs baseload (%)")
    ax.set_title("Runtime vs Dispatch Value", fontweight="bold")
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    out4 = FIGURES / "step2_runtime_value_tradeoff.png"
    fig.savefig(out4, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig = plt.figure(figsize=(8.4, 6.4), dpi=180)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(horizons, [value / 1e6 for value in revenue], cove, color="#2563EB", linewidth=2.2)
    ax.scatter(horizons, [value / 1e6 for value in revenue], cove, color="#EF4444", s=55)
    for h, rev, cove_value in zip(horizons, revenue, cove):
        ax.text(h, rev / 1e6, cove_value, f"{h}h", fontsize=9)
    ax.set_xlabel("Planning horizon (h)")
    ax.set_ylabel("Revenue metric (M)")
    ax.set_zlabel("COVE")
    ax.set_title("3D Horizon View: More Lookahead Is Not Always Better", fontweight="bold")
    ax.view_init(elev=24, azim=-52)
    fig.tight_layout()
    out5 = FIGURES / "step2_3d_horizon_revenue_cove.png"
    fig.savefig(out5, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    if oracle:
        best_oracle = max(oracle, key=lambda row: float(row["improvement_vs_baseload_pct"]))
        print("\nOracle context only, not realistic:")
        print(
            f"  Best oracle horizon = {int(float(best_oracle['horizon_hours']))} h, "
            f"{float(best_oracle['improvement_vs_baseload_pct']):.2f}% COVE improvement"
        )

    print("\nFigures saved:")
    for figure in [out1, out2, out3, out4, out5]:
        print(f"  {figure}")


if __name__ == "__main__":
    main()
