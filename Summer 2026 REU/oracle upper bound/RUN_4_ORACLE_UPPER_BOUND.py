#!/usr/bin/env python3
"""Step 4: perfect-future oracle upper bound.

Run from this folder:
    ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py

This is not a realistic controller. It shows the best possible Gurobi result
when the optimizer is allowed to know future wind and future price perfectly.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "summer_reu_mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "summer_reu_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


RESULTS = HERE / "results"
FIGURES = HERE / "figures"
SUMMARY_FILE = RESULTS / "oracle_upper_bound_summary.csv"
BUILD_SCRIPT = HERE / "code" / "build_oracle_summary.py"


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing oracle result file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def rebuild_oracle_summary() -> None:
    subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--output", str(SUMMARY_FILE)],
        cwd=HERE,
        check=True,
    )


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rebuild_oracle_summary()
    rows = sorted(load_rows(SUMMARY_FILE), key=lambda row: int(float(row["horizon_hours"])))
    if not rows:
        raise RuntimeError("No oracle rows found.")

    baseload_cove = float(rows[0]["baseload_cove"])
    baseload_revenue = float(rows[0]["baseload_revenue_metric"])
    best = max(rows, key=lambda row: float(row["improvement_vs_baseload_pct"]))

    print("\nSTEP 4: ORACLE UPPER BOUND")
    print("This is the perfect-future case. It is not deployable, but it shows the ceiling.\n")
    print(f"Baseload revenue metric: {baseload_revenue:,.2f}")
    print(f"Baseload COVE:           {baseload_cove:.6f}\n")
    print(f"{'Horizon':>8} {'COVE':>10} {'COVE gain %':>12} {'Revenue metric':>18} {'Final SoC':>12}")
    print("-" * 68)
    for row in rows:
        print(
            f"{int(float(row['horizon_hours'])):>6} h "
            f"{float(row['cove']):>10.6f} "
            f"{float(row['improvement_vs_baseload_pct']):>12.2f} "
            f"{float(row['revenue_metric']):>18,.2f} "
            f"{float(row['final_soc']):>12.2f}"
        )

    print("\nBest oracle case:")
    print(
        f"  {int(float(best['horizon_hours']))} h perfect-future horizon, "
        f"{float(best['improvement_vs_baseload_pct']):.2f}% COVE improvement vs baseload"
    )
    print("\nMeaning:")
    print("  This is the upper bound because Gurobi already knows future wind and future price.")
    print("  The realistic methods should be compared against baseload and viewed relative to this ceiling.")

    horizons = [int(float(row["horizon_hours"])) for row in rows]
    gains = [float(row["improvement_vs_baseload_pct"]) for row in rows]
    cove = [float(row["cove"]) for row in rows]
    revenue = [float(row["revenue_metric"]) for row in rows]
    runtime = [float(row["solver_runtime_seconds"]) for row in rows]

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=180)
    bars = ax.bar([f"{h} h" for h in horizons], gains, color="#DC2626")
    ax.set_ylabel("COVE improvement vs baseload (%)")
    ax.set_title("Oracle Upper Bound by Planning Horizon", fontweight="bold")
    ax.grid(axis="y", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.3, f"{value:.2f}%", ha="center")
    fig.tight_layout()
    out1 = FIGURES / "step4_oracle_improvement_by_horizon.png"
    fig.savefig(out1, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=180)
    ax.plot(horizons, cove, marker="o", linewidth=2.8, color="#B91C1C")
    ax.axhline(baseload_cove, color="#6B7280", linestyle="--", label="Baseload COVE")
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_ylabel("COVE (lower is better)")
    ax.set_title("Oracle COVE Falls as Perfect Lookahead Increases", fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(color="#E5E7EB")
    for x_value, y_value in zip(horizons, cove):
        ax.text(x_value, y_value + 0.025, f"{y_value:.3f}", ha="center")
    fig.tight_layout()
    out2 = FIGURES / "step4_oracle_cove_by_horizon.png"
    fig.savefig(out2, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=180)
    ax.scatter(runtime, gains, s=[80 + h for h in horizons], color="#EF4444", alpha=0.85)
    for h, x_value, y_value in zip(horizons, runtime, gains):
        ax.annotate(f"{h} h", (x_value, y_value), xytext=(7, 5), textcoords="offset points")
    ax.set_xlabel("Solver runtime (seconds)")
    ax.set_ylabel("COVE improvement vs baseload (%)")
    ax.set_title("Oracle Runtime vs Upper-Bound Value", fontweight="bold")
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    out3 = FIGURES / "step4_oracle_runtime_value_tradeoff.png"
    fig.savefig(out3, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig = plt.figure(figsize=(8.4, 6.4), dpi=180)
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(horizons, [value / 1e6 for value in revenue], cove, color="#DC2626", linewidth=2.2)
    ax.scatter(horizons, [value / 1e6 for value in revenue], cove, color="#111827", s=55)
    for h, rev, cove_value in zip(horizons, revenue, cove):
        ax.text(h, rev / 1e6, cove_value, f"{h}h", fontsize=9)
    ax.set_xlabel("Perfect lookahead (h)")
    ax.set_ylabel("Revenue metric (M)")
    ax.set_zlabel("COVE")
    ax.set_title("3D Oracle View: The Best Possible Dispatch Ceiling", fontweight="bold")
    ax.view_init(elev=24, azim=-52)
    fig.tight_layout()
    out4 = FIGURES / "step4_3d_oracle_revenue_cove.png"
    fig.savefig(out4, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    print("\nFigures saved:")
    for figure in [out1, out2, out3, out4]:
        print(f"  {figure}")


if __name__ == "__main__":
    main()
