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


RESULTS = HERE / "results"
FIGURES = HERE / "figures"
RMSE_FILE = Path(knobs.RMSE_OUTPUT)
COMPARE_SCRIPT = HERE / "code" / "compare_forecast_rmse.py"
DISPATCH_FORECAST_SCRIPT = HERE / "code" / "build_dispatch_causal_ridge.py"
PREDICTIONS_FILE = Path(knobs.CAUSAL_OUTPUT_DIR) / "causal_lag_forecast_predictions.csv"
FIGURE_GENERATOR = HERE.parent / "common" / "regenerate_all_figures.py"


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required result file: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def rebuild_rmse_table() -> None:
    cmd = [
        sys.executable,
        str(COMPARE_SCRIPT),
        "--dataset",
        str(knobs.DATASET),
        "--causal-alpha",
        str(knobs.CAUSAL_ALPHA),
        "--causal-output-dir",
        str(knobs.CAUSAL_OUTPUT_DIR),
        "--pyron-results",
        str(knobs.PYRON_RESULTS),
        "--output",
        str(RMSE_FILE),
    ]
    if getattr(knobs, "SKIP_REBUILD", False):
        cmd.append("--skip-rebuild")
    print("Running forecast/RMSE command from EXPERIMENT_KNOBS.py:")
    print(" ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=HERE, check=True)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    RMSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if getattr(knobs, "RERUN_FROM_SOURCE", True):
        rebuild_rmse_table()
        dispatch_cmd = [
            sys.executable,
            str(DISPATCH_FORECAST_SCRIPT),
            "--out-dir",
            str(knobs.DISPATCH_FORECAST_OUTPUT_DIR),
            "--max-horizon-hours",
            str(knobs.DISPATCH_FORECAST_MAX_HORIZON_HOURS),
            "--train-origin-stride",
            str(knobs.DISPATCH_FORECAST_TRAIN_ORIGIN_STRIDE),
        ]
        print("\nBuilding the exact frozen multi-lead causal ridge used by Steps 2 and 3:")
        print(" ".join(dispatch_cmd))
        subprocess.run(dispatch_cmd, cwd=HERE, check=True)
    else:
        print("STEP 1: reading the saved frozen forecast CSVs (no retraining).")
        print("Set RERUN_FROM_SOURCE = True in EXPERIMENT_KNOBS.py to rebuild them.\n")
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
    colors = ["#2F7D7A"] + ["#9AA4B2"] * (len(rows) - 1)

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

    mae = [float(row["mae_mw"]) for row in rows]
    fig, ax = plt.subplots(figsize=(9.8, 5.6), dpi=180)
    ax.scatter(rmse, mae, s=180, color=colors, edgecolor="#111827", linewidth=0.8)
    for label, x_value, y_value in zip(labels, rmse, mae):
        ax.annotate(label, (x_value, y_value), xytext=(8, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("RMSE (MW, lower is better)")
    ax.set_ylabel("MAE (MW, lower is better)")
    ax.set_title("Forecast Error Tradeoff", fontweight="bold")
    ax.grid(color="#E5E7EB")
    fig.tight_layout()
    out2 = FIGURES / "step1_rmse_mae_tradeoff.png"
    fig.savefig(out2, facecolor="white", bbox_inches="tight")
    plt.close(fig)

    if PREDICTIONS_FILE.exists():
        predictions = pd.read_csv(PREDICTIONS_FILE, parse_dates=["datetime"])
        week = predictions.iloc[:168].copy()
        fig, ax = plt.subplots(figsize=(12, 5.6), dpi=180)
        ax.plot(week["datetime"], week["actual_power_mw"], label="Actual power", color="#1F2933", linewidth=2.0)
        ax.plot(week["datetime"], week["causal_lag_prediction_mw"], label="Causal lag/ridge", color="#2F7D7A", linewidth=1.8)
        ax.plot(week["datetime"], week["lag1_persistence_prediction_mw"], label="Lag-1 persistence", color="#68778C", linewidth=1.4, alpha=0.85)
        ax.set_ylabel("Power (MW)")
        ax.set_title("Example Forecast Week", fontweight="bold")
        ax.legend(frameon=False, ncol=3)
        ax.grid(color="#E5E7EB")
        fig.autofmt_xdate(rotation=20)
        fig.tight_layout()
        out3 = FIGURES / "step1_example_forecast_week.png"
        fig.savefig(out3, facecolor="white", bbox_inches="tight")
        plt.close(fig)

        errors = predictions["causal_lag_prediction_mw"] - predictions["actual_power_mw"]
        fig, ax = plt.subplots(figsize=(9.5, 5.4), dpi=180)
        ax.hist(errors, bins=70, color="#2F7D7A", alpha=0.85)
        ax.axvline(0, color="#1F2933", linewidth=1.2)
        ax.set_xlabel("Prediction error (MW)")
        ax.set_ylabel("Hours")
        ax.set_title("Causal Lag/Ridge Error Distribution", fontweight="bold")
        ax.grid(axis="y", color="#E5E7EB")
        fig.tight_layout()
        out4 = FIGURES / "step1_causal_error_distribution.png"
        fig.savefig(out4, facecolor="white", bbox_inches="tight")
        plt.close(fig)
    else:
        out3 = None
        out4 = None

    subprocess.run([sys.executable, str(FIGURE_GENERATOR), "--step", "1"], cwd=HERE.parent, check=True)
    print("\nFigures saved:")
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure}")


if __name__ == "__main__":
    main()
