#!/usr/bin/env python3
"""Step 1 of the Summer 2026 REU ladder: compare forecast RMSE.

Run from this folder:
    ../../venv/bin/python RUN_1_FORECAST_RMSE.py

This script does not run Gurobi. It only checks which forecasting method best
predicts generated power. COVE starts in the dispatch steps after forecasts are
fed into Gurobi.
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
RMSE_FILE = RESULTS / "forecast_model_rmse_comparison.csv"


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required result file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = load_rows(RMSE_FILE)
    rows = sorted(rows, key=lambda row: float(row["rmse_mw"]))

    print("\nSTEP 1: FORECAST MODEL COMPARISON")
    print("Metric: power prediction RMSE in MW. Lower is better.\n")
    print(f"{'Rank':<5} {'Model':<38} {'RMSE MW':>10} {'MAE MW':>10} {'Bias MW':>10}")
    print("-" * 78)
    for rank, row in enumerate(rows, start=1):
        print(
            f"{rank:<5} "
            f"{row['model']:<38} "
            f"{float(row['rmse_mw']):>10.2f} "
            f"{float(row['mae_mw']):>10.2f} "
            f"{float(row['bias_mw']):>10.2f}"
        )

    best = rows[0]
    print("\nBest forecast model:")
    print(f"  {best['model']} with RMSE = {float(best['rmse_mw']):.2f} MW")
    print("\nImportant:")
    print("  This step does not have COVE improvement because it only predicts power.")
    print("  The next steps feed this forecast information into Gurobi for dispatch.")

    labels = [row["model"].replace("_", " ") for row in rows]
    rmse = [float(row["rmse_mw"]) for row in rows]
    colors = ["#1B9E77"] + ["#9CA3AF"] * (len(rows) - 1)

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=180)
    bars = ax.barh(labels, rmse, color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("RMSE (MW, lower is better)")
    ax.set_title("Forecast Model Comparison", fontweight="bold")
    ax.grid(axis="x", color="#E5E7EB")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, rmse):
        ax.text(value + 1.0, bar.get_y() + bar.get_height() / 2, f"{value:.2f}", va="center")
    fig.tight_layout()
    out = FIGURES / "step1_forecast_rmse_comparison.png"
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved: {out}")


if __name__ == "__main__":
    main()
