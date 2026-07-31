"""Compare rolling-horizon Gurobi dispatch results across look-ahead windows.

This script expects completed runs from rolling_horizon_gurobi_dispatch.py.
It keeps the storage design and constraints fixed, then compares only the
planning horizon.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_HORIZONS = {
    24: "horizon_24h",
    48: "horizon_48h",
    72: "horizon_72h",
}


def max_constraint_violation(row: pd.Series) -> float:
    violation_columns = [
        column
        for column in row.index
        if column.startswith("max_") and column.endswith("_violation")
    ]
    return float(max(float(row[column]) for column in violation_columns))


def load_summary(result_dir: Path, horizon: int) -> dict:
    summary_path = result_dir / "rolling_horizon_gurobi_summary.csv"
    row = pd.read_csv(summary_path).iloc[0]
    return {
        "horizon_hours": horizon,
        "horizon_days": horizon / 24,
        "gurobi_cove": float(row["gurobi_cove"]),
        "baseload_cove": float(row["baseload_cove"]),
        "improvement_vs_baseload_pct": float(row["gurobi_improvement_vs_baseload_pct"]),
        "project_revenue_metric": float(row["gurobi_revenue"]),
        "solver_runtime_seconds": float(row["gurobi_runtime_seconds_sum"]),
        "mean_window_runtime_seconds": float(row["gurobi_runtime_seconds_mean"]),
        "final_soc_mwh": float(row["final_soc"]),
        "max_soc_mwh": float(row["max_soc"]),
        "max_constraint_violation": max_constraint_violation(row),
        "source_directory": str(result_dir),
    }


def style_axis(axis):
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    axis.set_axisbelow(True)


def save_performance_figures(comparison: pd.DataFrame, output_dir: Path):
    horizons = comparison["horizon_hours"].to_numpy()
    labels = [f"{int(hours)} h" for hours in horizons]
    colors = ["#2563EB", "#0F766E", "#B45309", "#7C3AED"]

    fig, axis = plt.subplots(figsize=(8.5, 4.8), dpi=220)
    axis.plot(horizons, comparison["gurobi_cove"], marker="o", linewidth=2.5, color="#1D4ED8")
    for x, y in zip(horizons, comparison["gurobi_cove"]):
        axis.annotate(f"{y:.4f}", (x, y), xytext=(0, 9), textcoords="offset points", ha="center")
    axis.set_xticks(horizons, labels)
    axis.set_ylim(
        comparison["gurobi_cove"].min() - 0.02,
        comparison["gurobi_cove"].max() + 0.04,
    )
    axis.set_ylabel("COVE (lower is better)")
    axis.set_title("Longer look-ahead lowers COVE, with diminishing returns", fontweight="bold")
    axis.text(
        0.99,
        0.95,
        f"Baseload COVE = {comparison['baseload_cove'].iloc[0]:.4f}",
        transform=axis.transAxes,
        ha="right",
        va="top",
        color="#64748B",
    )
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_01_cove_by_horizon.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8.5, 4.8), dpi=220)
    bars = axis.bar(labels, comparison["improvement_vs_baseload_pct"], color=colors, width=0.62)
    axis.axhline(32.3, color="#111827", linestyle="--", linewidth=1.5, label="Published COVE-NN: 32.3%")
    for bar, value in zip(bars, comparison["improvement_vs_baseload_pct"]):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.35,
            f"{value:.2f}%",
            ha="center",
            fontweight="bold",
        )
    axis.set_ylim(0, 36)
    axis.set_ylabel("COVE improvement vs baseload")
    axis.set_title("Dispatch value increases as Gurobi sees farther ahead", fontweight="bold")
    axis.legend(frameon=False, loc="lower right")
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_02_improvement_by_horizon.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8.5, 4.8), dpi=220)
    values = comparison["project_revenue_metric"] / 1_000_000
    bars = axis.bar(labels, values, color=colors, width=0.62)
    for bar, value in zip(bars, values):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.25,
            f"{value:.2f}M",
            ha="center",
            fontweight="bold",
        )
    axis.set_ylabel("Project value metric (millions)")
    axis.set_title("Value-weighted delivered energy by planning horizon", fontweight="bold")
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_03_value_metric_by_horizon.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8.5, 4.8), dpi=220)
    bars = axis.bar(labels, comparison["solver_runtime_seconds"], color=colors, width=0.62)
    for bar, value in zip(bars, comparison["solver_runtime_seconds"]):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.5,
            f"{value:.1f}s",
            ha="center",
            fontweight="bold",
        )
    axis.set_ylabel("Total Gurobi solver time (seconds)")
    axis.set_title("Longer horizons improve dispatch but cost more computation", fontweight="bold")
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_04_runtime_by_horizon.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def load_example_week(labels_path: Path, start: str, end: str, horizon: int) -> pd.DataFrame:
    usecols = [
        "datetime",
        "gurobi_storage_start",
        "gurobi_charge",
        "gurobi_discharge",
        "gurobi_release",
    ]
    labels = pd.read_csv(labels_path, usecols=usecols)
    labels["datetime"] = pd.to_datetime(labels["datetime"])
    selected = labels[
        (labels["datetime"] >= pd.Timestamp(start))
        & (labels["datetime"] <= pd.Timestamp(end))
    ].copy()
    selected["horizon_hours"] = horizon
    selected["net_storage_power"] = selected["gurobi_discharge"] - selected["gurobi_charge"]
    return selected


def save_example_week_figures(example: pd.DataFrame, output_dir: Path):
    palette = {24: "#2563EB", 48: "#0F766E", 72: "#B45309", 168: "#7C3AED"}

    fig, axis = plt.subplots(figsize=(11, 5.2), dpi=220)
    for horizon, group in example.groupby("horizon_hours"):
        axis.plot(
            group["datetime"],
            group["gurobi_storage_start"],
            label=f"{horizon} h",
            color=palette[horizon],
            linewidth=1.8,
        )
    axis.axhline(200, color="#64748B", linestyle="--", linewidth=1, label="Minimum SoC")
    axis.axhline(1000, color="#64748B", linestyle=":", linewidth=1, label="Maximum SoC")
    axis.set_ylabel("State of charge (MWh)")
    axis.set_title("Example week: longer horizons preserve energy for later opportunities", fontweight="bold")
    axis.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.13))
    style_axis(axis)
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(output_dir / "figure_05_example_week_soc.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(4, 1, figsize=(11, 8.5), dpi=220, sharex=True, sharey=True)
    for axis, horizon in zip(axes, sorted(example["horizon_hours"].unique())):
        group = example[example["horizon_hours"] == horizon]
        axis.plot(group["datetime"], group["net_storage_power"], color=palette[horizon], linewidth=1.2)
        axis.axhline(0, color="#94A3B8", linewidth=0.8)
        axis.fill_between(
            group["datetime"],
            group["net_storage_power"],
            0,
            where=group["net_storage_power"] >= 0,
            color="#16A34A",
            alpha=0.25,
        )
        axis.fill_between(
            group["datetime"],
            group["net_storage_power"],
            0,
            where=group["net_storage_power"] < 0,
            color="#2563EB",
            alpha=0.25,
        )
        axis.set_ylabel(f"{horizon} h\nMW")
        style_axis(axis)
    axes[0].set_title("Example week net storage power: positive discharge, negative charge", fontweight="bold")
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_06_example_week_dispatch.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Compare completed rolling-horizon Gurobi runs.")
    parser.add_argument(
        "--base-dir",
        default=str(
            Path(__file__).resolve().parent
            / "rolling_horizon_gurobi_results"
            / "horizon_comparison_full_43y"
        ),
    )
    parser.add_argument(
        "--weekly-dir",
        default=str(
            Path(__file__).resolve().parent
            / "rolling_horizon_gurobi_results"
            / "full_dataset_caes_100mw_24h_dod80_mid_soc"
        ),
    )
    parser.add_argument("--example-start", default="2020-01-06 00:00:00")
    parser.add_argument("--example-end", default="2020-01-12 23:59:59")
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    weekly_dir = Path(args.weekly_dir)

    result_dirs = {horizon: base_dir / name for horizon, name in DEFAULT_HORIZONS.items()}
    result_dirs[168] = weekly_dir

    comparison = pd.DataFrame(
        [load_summary(result_dirs[horizon], horizon) for horizon in sorted(result_dirs)]
    )
    weekly_improvement = comparison.loc[
        comparison["horizon_hours"] == 168, "improvement_vs_baseload_pct"
    ].iloc[0]
    comparison["share_of_weekly_improvement_pct"] = (
        comparison["improvement_vs_baseload_pct"] / weekly_improvement * 100
    )
    comparison["cove_gap_vs_168h"] = (
        comparison["gurobi_cove"]
        - comparison.loc[comparison["horizon_hours"] == 168, "gurobi_cove"].iloc[0]
    )
    comparison.to_csv(base_dir / "rolling_horizon_comparison.csv", index=False)

    save_performance_figures(comparison, base_dir)

    example_parts = []
    for horizon, result_dir in result_dirs.items():
        example_parts.append(
            load_example_week(
                result_dir / "rolling_horizon_gurobi_labels.csv",
                args.example_start,
                args.example_end,
                horizon,
            )
        )
    example = pd.concat(example_parts, ignore_index=True)
    example.to_csv(base_dir / "example_week_all_horizons.csv", index=False)
    save_example_week_figures(example, base_dir)

    max_violation = comparison["max_constraint_violation"].max()
    best_row = comparison.loc[comparison["gurobi_cove"].idxmin()]
    daily_row = comparison.loc[comparison["horizon_hours"] == 24].iloc[0]
    three_day_row = comparison.loc[comparison["horizon_hours"] == 72].iloc[0]

    summary_text = f"""Rolling-horizon comparison on the full 1980-2023 dataset

Fixed setup
- Storage: PNNL CAES
- Power rating: 100 MW
- Duration/capacity: 24 h / 2,400 MWh
- Round-trip efficiency: 55%
- Minimum SoC: 200 MWh
- Maximum SoC: 2,400 MWh
- Initial SoC: 1,440 MWh
- Grid export limit: 249 MW
- Execution step: 24 hours
- Terminal rule: planned terminal SoC equals the current window's initial SoC
- SoC is carried chronologically between executed windows

Results
{comparison[['horizon_hours', 'gurobi_cove', 'improvement_vs_baseload_pct', 'project_revenue_metric', 'solver_runtime_seconds', 'max_constraint_violation']].to_string(index=False)}

Interpretation
- Best perfect-information result: {int(best_row['horizon_hours'])} h, COVE {best_row['gurobi_cove']:.6f}.
- 24 h improvement: {daily_row['improvement_vs_baseload_pct']:.2f}%.
- 72 h improvement: {three_day_row['improvement_vs_baseload_pct']:.2f}%, capturing {three_day_row['share_of_weekly_improvement_pct']:.2f}% of the 168 h improvement.
- Maximum recorded constraint violation across all runs: {max_violation:.3e}.
- With historical future values available, longer horizons perform better. A 24 h horizon may still be preferable with real forecasts because short forecasts are more accurate.
"""
    (base_dir / "README.md").write_text(summary_text)

    print(comparison.to_string(index=False))
    print(f"Saved comparison and figures to {base_dir}")


if __name__ == "__main__":
    main()
