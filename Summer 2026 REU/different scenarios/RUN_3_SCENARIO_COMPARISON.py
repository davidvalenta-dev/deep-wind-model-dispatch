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
SUMMARY_FILE = RESULTS / "uncertainty_aware_summary.csv"
RUNNER = HERE / "code" / "run_uncertainty_aware_dispatch.py"


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required result file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def short_name(candidate: str) -> str:
    names = {
        "single_forecast_recourse_nowcast_gated": "1 forecast",
        "three_scenario_expected_nowcast_gated": "3 scenarios",
        "five_scenario_expected_nowcast_gated": "5 scenarios",
        "seven_scenario_expected_nowcast_gated": "7 scenarios",
        "ten_scenario_expected_nowcast_gated": "10 scenarios",
    }
    return names.get(candidate, candidate)


def money(value: str) -> str:
    return f"${float(value):,.2f}"


def add_optional(cmd: list[str], flag: str, value) -> None:
    if value is not None:
        cmd.extend([flag, str(value)])


def rerun_from_knobs() -> None:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--horizon-hours",
        str(knobs.HORIZON_HOURS),
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
    add_optional(cmd, "--max-origins", knobs.MAX_ORIGINS)
    add_optional(cmd, "--gate-margin", knobs.GATE_MARGIN)
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
    rerun_from_knobs()
    rows = load_rows(SUMMARY_FILE)
    order = {
        "single_forecast_recourse_nowcast_gated": 1,
        "three_scenario_expected_nowcast_gated": 3,
        "five_scenario_expected_nowcast_gated": 5,
        "seven_scenario_expected_nowcast_gated": 7,
        "ten_scenario_expected_nowcast_gated": 10,
    }
    rows = sorted(rows, key=lambda row: order.get(row["candidate"], 99))
    if not rows:
        raise RuntimeError("No scenario rows found.")

    baseload_revenue = float(rows[0]["baseload_revenue"])
    baseload_cove = float(rows[0]["baseload_cove_index"])
    horizon = int(float(rows[0]["horizon_hours"]))

    print("\nSTEP 3: SCENARIO DISPATCH COMPARISON")
    print("Compared against baseload. Higher revenue gain and COVE reduction are better.")
    print(f"Scenario lookahead: {horizon} h; execution: first hour, then replan.\n")
    print(f"Baseload revenue: {baseload_revenue:,.2f}")
    print(f"Baseload COVE:    {baseload_cove:.6f}\n")
    print(
        f"{'Method':<16} {'Revenue':>18} {'Revenue gain':>14} "
        f"{'COVE':>10} {'COVE gain':>12}"
    )
    print("-" * 76)
    print(f"{'Baseload':<16} {money(str(baseload_revenue)):>18} {'0.00%':>14} {baseload_cove:>10.6f} {'0.00%':>12}")
    for row in rows:
        print(
            f"{short_name(row['candidate']):<16} "
            f"{money(row['dispatch_revenue']):>18} "
            f"{float(row['revenue_gain_vs_baseload_pct']):>13.2f}% "
            f"{float(row['dispatch_cove_index']):>10.6f} "
            f"{float(row['cove_reduction_vs_baseload_pct']):>11.2f}%"
        )

    best = max(rows, key=lambda row: float(row["cove_reduction_vs_baseload_pct"]))
    print("\nBest scenario case:")
    print(
        f"  {short_name(best['candidate'])}, "
        f"{float(best['cove_reduction_vs_baseload_pct']):.2f}% COVE reduction, "
        f"{float(best['revenue_gain_vs_baseload_pct']):.2f}% revenue gain"
    )
    print("\nMeaning:")
    print("  Multiple forecast futures helped Gurobi avoid trusting one bad forecast.")
    print("  Three scenarios was best in the full 48 h run; ten became too conservative.")

    labels = ["Baseload"] + [short_name(row["candidate"]) for row in rows]
    gains = [0.0] + [float(row["cove_reduction_vs_baseload_pct"]) for row in rows]
    rev_gains = [0.0] + [float(row["revenue_gain_vs_baseload_pct"]) for row in rows]
    revenues = [baseload_revenue] + [float(row["dispatch_revenue"]) for row in rows]
    coves = [baseload_cove] + [float(row["dispatch_cove_index"]) for row in rows]
    colors = ["#9CA3AF"] + ["#60A5FA", "#38BDF8", "#22C55E", "#16A34A", "#F97316"]

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=180)
    bars = ax.bar(labels, gains, color=colors)
    ax.set_ylabel("COVE reduction vs baseload (%)")
    ax.set_title("Scenario Dispatch: COVE Improvement", fontweight="bold")
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
    ax.set_ylabel("Revenue gain vs baseload (%)")
    ax.set_title("Scenario Dispatch: Revenue Gain", fontweight="bold")
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
    ax.plot(rev_gains, gains, marker="o", linewidth=2.4, color="#2563EB")
    for label, x_value, y_value in zip(labels, rev_gains, gains):
        ax.annotate(label, (x_value, y_value), xytext=(7, 5), textcoords="offset points")
    ax.set_xlabel("Revenue gain vs baseload (%)")
    ax.set_ylabel("COVE reduction vs baseload (%)")
    ax.set_title("Scenario Tradeoff: Revenue and COVE Move Together", fontweight="bold")
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    out3 = FIGURES / "step3_revenue_cove_tradeoff.png"
    fig.savefig(out3, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    ladder_labels = ["Baseload", "1 forecast", "3 scenarios"]
    ladder_values = [
        baseload_revenue / 1e6,
        float(rows[0]["dispatch_revenue"]) / 1e6,
        float(best["dispatch_revenue"]) / 1e6,
    ]
    fig, ax = plt.subplots(figsize=(9.2, 5.2), dpi=180)
    bars = ax.bar(ladder_labels, ladder_values, color=["#9CA3AF", "#60A5FA", "#22C55E"])
    ax.set_ylabel("Revenue (millions)")
    ax.set_title("Ladder Result: Forecast Dispatch to Scenario Dispatch", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, ladder_values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 2.0, f"${value:.1f}M", ha="center")
    fig.tight_layout()
    out4 = FIGURES / "step3_ladder_revenue_progression.png"
    fig.savefig(out4, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    scenario_counts = [0, 1, 3, 5, 7, 10]
    fig = plt.figure(figsize=(8.8, 6.4), dpi=180)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(scenario_counts, [value / 1e6 for value in revenues], coves, color="#0F766E", linewidth=2.2)
    ax.scatter(scenario_counts, [value / 1e6 for value in revenues], coves, color="#EF4444", s=55)
    for count, label, revenue_value, cove_value in zip(scenario_counts, labels, revenues, coves):
        ax.text(count, revenue_value / 1e6, cove_value, label.replace(" scenarios", "sc"), fontsize=8)
    ax.set_xlabel("Scenario count")
    ax.set_ylabel("Revenue (M)")
    ax.set_zlabel("COVE")
    ax.set_title("3D Scenario View: More Scenarios Is Not Automatically Better", fontweight="bold")
    ax.view_init(elev=24, azim=-48)
    fig.tight_layout()
    out5 = FIGURES / "step3_3d_scenario_revenue_cove.png"
    fig.savefig(out5, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    print("\nFigures saved:")
    for figure in [out1, out2, out3, out4, out5]:
        print(f"  {figure}")


if __name__ == "__main__":
    main()
