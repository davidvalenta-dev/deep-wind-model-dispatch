#!/usr/bin/env python3
"""Step 3 of the Summer 2026 REU ladder: uncertainty-aware scenarios.

Run from this folder:
    ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py

This compares baseload, single-forecast dispatch, and multi-scenario dispatch.
It uses the full 48-hour scenario ladder run.
"""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "summer_reu_mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "summer_reu_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RESULTS = HERE / "results"
FIGURES = HERE / "figures"
SUMMARY_FILE = RESULTS / "scenario_48h_full_ladder" / "uncertainty_aware_summary.csv"


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


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
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

    print(f"\nFigures saved:\n  {out1}\n  {out2}")


if __name__ == "__main__":
    main()
