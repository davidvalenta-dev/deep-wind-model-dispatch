#!/usr/bin/env python3
"""Regenerate every paper-facing Summer 2026 REU figure from frozen CSVs."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm


REU = Path(__file__).resolve().parents[1]

NAVY = "#203A5F"
TEAL = "#2F7D7A"
STEEL = "#68778C"
PLUM = "#6F627A"
GRAY = "#9AA4B2"
LIGHT = "#DCE4E8"
PALE = "#EFF3F5"
INK = "#1F2933"
GRID = "#D9E0E5"
METHOD_COLORS = [GRAY, NAVY, TEAL, STEEL, PLUM, "#4F6D7A"]


def set_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": STEEL,
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "xtick.color": INK,
            "ytick.color": INK,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "font.size": 10,
            "legend.fontsize": 9,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def new_figure(width: float = 10.0, height: float = 5.8):
    return plt.subplots(figsize=(width, height), dpi=190, constrained_layout=True)


def save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=190, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def clear_pngs(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for path in folder.glob("*.png"):
        path.unlink()


def color_best(length: int, best_index: int) -> list[str]:
    colors = [GRAY] * length
    colors[best_index] = TEAL
    return colors


def label_bars(ax, bars, values, suffix: str = "", decimals: int = 2) -> None:
    if not values:
        return
    span = max(values) - min(0.0, min(values))
    offset = max(span * 0.025, 0.04)
    for bar, value in zip(bars, values):
        y = value + offset if value >= 0 else value - offset
        va = "bottom" if value >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{value:.{decimals}f}{suffix}",
            ha="center",
            va=va,
            fontsize=9,
            color=INK,
        )


def friendly_model(name: str) -> str:
    return {
        "causal_lag_prediction_mw": "Causal lag/ridge",
        "lag1_persistence_prediction_mw": "Last-value persistence",
        "speed_power_curve_prediction_mw": "Speed-to-power curve",
        "rnn_preds": "RNN",
        "physics_preds": "Physics baseline",
        "prob_preds": "Probabilistic model",
    }.get(name, name.replace("_", " "))


def scenario_label(candidate: str) -> str:
    if candidate.startswith("single_"):
        return "1 forecast"
    for count, word in ((3, "three"), (5, "five"), (7, "seven"), (10, "ten")):
        if candidate.startswith(word):
            return f"{count} scenarios"
    return candidate.replace("_", " ")


def generate_step0() -> list[Path]:
    folder = REU / "100 MW baseload" / "figures"
    clear_pngs(folder)
    result = REU / "100 MW baseload" / "results" / "frozen_controlled"
    hourly = pd.read_csv(result / "constant_output_baseload_100mw_2014_2023_hourly.csv")
    hourly["datetime"] = pd.to_datetime(hourly["datetime"])
    summary = pd.read_csv(result / "constant_output_baseload_100mw_2014_2023_summary.csv").iloc[0]
    outputs: list[Path] = []

    week = hourly.iloc[: 24 * 7]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), dpi=190, sharex=True, constrained_layout=True)
    axes[0].plot(week["datetime"], week["actual_wind_mw"], color=STEEL, lw=1.5, label="Actual wind")
    axes[0].plot(week["datetime"], week["delivered_power_mw"], color=TEAL, lw=2.0, label="Delivered power")
    axes[0].axhline(100, color=NAVY, ls="--", lw=1.4, label="100 MW target")
    axes[0].set_ylabel("Power (MW)")
    axes[0].set_title("100 MW Constant-Output Benchmark: Representative Week")
    axes[0].legend(frameon=False, ncol=3, loc="upper center")
    axes[0].grid(True)
    axes[1].plot(week["datetime"], week["soc_end_mwh"], color=PLUM, lw=2.0)
    axes[1].fill_between(week["datetime"], 200, week["soc_end_mwh"], color=PLUM, alpha=0.12)
    axes[1].axhline(200, color=GRAY, ls="--", lw=1.2, label="Minimum SoC")
    axes[1].axhline(1000, color=GRAY, ls=":", lw=1.2, label="Maximum SoC")
    axes[1].set_ylabel("Stored energy (MWh)")
    axes[1].set_xlabel("Time")
    axes[1].set_ylim(150, 1050)
    axes[1].grid(True)
    axes[1].legend(frameon=False, ncol=2, loc="lower right")
    out = folder / "step0_100mw_baseload_2014_2023_example_week.png"
    save(fig, out)
    outputs.append(out)

    labels = ["Delivered", "Charged", "Discharged", "Curtailed", "Shortfall"]
    values = [
        summary["delivered_energy_mwh"],
        summary["total_charge_mwh"],
        summary["total_discharge_mwh"],
        summary["curtailment_mwh"],
        summary["output_shortfall_mwh"],
    ]
    values_m = [float(value) / 1e6 for value in values]
    fig, ax = new_figure()
    bars = ax.barh(labels, values_m, color=[NAVY, TEAL, STEEL, PLUM, GRAY])
    ax.invert_yaxis()
    ax.set_xlabel("Energy over evaluation period (million MWh)")
    ax.set_title("Where the Wind Energy Went in the 100 MW Benchmark")
    ax.grid(axis="x")
    for bar, value in zip(bars, values_m):
        ax.text(value + max(values_m) * 0.015, bar.get_y() + bar.get_height() / 2, f"{value:.2f}", va="center")
    ax.set_xlim(0, max(values_m) * 1.16)
    out = folder / "step0_energy_flow_totals.png"
    save(fig, out)
    outputs.append(out)

    sorted_soc = np.sort(hourly["soc_end_mwh"].to_numpy(float))[::-1]
    percentile = np.linspace(0, 100, len(sorted_soc))
    fig, ax = new_figure()
    ax.plot(percentile, sorted_soc, color=PLUM, lw=2.2)
    ax.fill_between(percentile, 200, sorted_soc, color=PLUM, alpha=0.12)
    ax.axhline(600, color=NAVY, ls="--", lw=1.3, label="Initial/year-end target = 600 MWh")
    ax.axhline(200, color=GRAY, ls=":", lw=1.2, label="Minimum = 200 MWh")
    ax.set_xlabel("Share of evaluated hours (%)")
    ax.set_ylabel("Stored energy (MWh)")
    ax.set_title("Storage Duration Curve: How Often Each SoC Level Occurred")
    ax.set_ylim(150, 1050)
    ax.grid(True)
    ax.legend(frameon=False, loc="upper right")
    out = folder / "step0_soc_duration_curve.png"
    save(fig, out)
    outputs.append(out)

    annual = hourly.assign(year=hourly["datetime"].dt.year).groupby("year")["raw_hourly_revenue_usd"].sum() / 1e6
    fig, ax = new_figure()
    bars = ax.bar(annual.index.astype(str), annual.values, color=TEAL)
    ax.set_ylabel("Raw realized revenue (million USD)")
    ax.set_title("100 MW Benchmark Raw Revenue by Evaluation Year")
    ax.grid(axis="y")
    label_bars(ax, bars, annual.tolist(), "", 1)
    ax.set_ylim(0, annual.max() * 1.15)
    out = folder / "step0_annual_raw_revenue.png"
    save(fig, out)
    outputs.append(out)
    return outputs


def generate_step1() -> list[Path]:
    folder = REU / "causal ridge regression" / "figures"
    clear_pngs(folder)
    result = REU / "causal ridge regression" / "results" / "frozen_controlled"
    compare = pd.read_csv(result / "forecast_model_rmse_comparison.csv").sort_values("rmse_mw")
    predictions = pd.read_csv(result / "causal_lag_forecast_outputs" / "causal_lag_forecast_predictions.csv")
    predictions["datetime"] = pd.to_datetime(predictions["datetime"])
    splits = pd.read_csv(result / "causal_lag_forecast_outputs" / "causal_lag_forecast_metrics.csv")
    lead = pd.read_csv(result / "canonical_dispatch_forecast" / "canonical_dispatch_forecast_accuracy_by_lead.csv")
    labels = [friendly_model(name) for name in compare["model"]]
    outputs: list[Path] = []

    fig, ax = new_figure()
    values = compare["rmse_mw"].tolist()
    bars = ax.barh(labels, values, color=color_best(len(values), 0))
    ax.invert_yaxis()
    ax.set_xlabel("RMSE (MW; lower is better)")
    ax.set_title("Forecast Model Comparison on the Common Evaluation Period")
    ax.grid(axis="x")
    for bar, value in zip(bars, values):
        ax.text(value + 1.0, bar.get_y() + bar.get_height() / 2, f"{value:.2f}", va="center")
    ax.set_xlim(0, max(values) * 1.15)
    out = folder / "step1_forecast_rmse_comparison.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    for idx, row in compare.reset_index(drop=True).iterrows():
        ax.scatter(row["rmse_mw"], row["mae_mw"], s=95, color=METHOD_COLORS[idx], label=friendly_model(row["model"]))
    ax.set_xlabel("RMSE (MW; lower is better)")
    ax.set_ylabel("MAE (MW; lower is better)")
    ax.set_title("Forecast Error Tradeoff")
    ax.grid(True)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    out = folder / "step1_rmse_mae_tradeoff.png"
    save(fig, out)
    outputs.append(out)

    week = predictions.iloc[: 24 * 7]
    fig, ax = new_figure(11, 5.8)
    ax.plot(week["datetime"], week["actual_power_mw"], color=INK, lw=2.0, label="Actual power")
    ax.plot(week["datetime"], week["causal_lag_prediction_mw"], color=TEAL, lw=1.8, label="Causal lag/ridge")
    ax.plot(week["datetime"], week["lag1_persistence_prediction_mw"], color=STEEL, lw=1.3, ls="--", label="Last-value persistence")
    ax.set_ylabel("Wind power (MW)")
    ax.set_xlabel("Time")
    ax.set_title("Representative Week: Forecasts Compared with Actual Power")
    ax.grid(True)
    ax.legend(frameon=False, ncol=3, loc="upper center")
    out = folder / "step1_example_forecast_week.png"
    save(fig, out)
    outputs.append(out)

    error = predictions["causal_lag_prediction_mw"] - predictions["actual_power_mw"]
    low, high = np.quantile(error, [0.005, 0.995])
    fig, ax = new_figure()
    ax.hist(error, bins=70, range=(low, high), color=TEAL, alpha=0.9)
    ax.axvline(0, color=INK, lw=1.3)
    ax.set_xlabel("Prediction error (forecast - actual, MW)")
    ax.set_ylabel("Number of hours")
    ax.set_title("Causal Lag/Ridge Error Distribution")
    ax.grid(axis="y")
    out = folder / "step1_causal_error_distribution.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure(7.5, 6.5)
    hb = ax.hexbin(
        predictions["actual_power_mw"],
        predictions["causal_lag_prediction_mw"],
        gridsize=48,
        mincnt=1,
        cmap="Blues",
        norm=LogNorm(),
    )
    max_power = max(predictions["actual_power_mw"].max(), predictions["causal_lag_prediction_mw"].max())
    ax.plot([0, max_power], [0, max_power], color=INK, ls="--", lw=1.3, label="Perfect forecast")
    ax.set_xlabel("Actual power (MW)")
    ax.set_ylabel("Causal lag/ridge prediction (MW)")
    ax.set_title("Actual vs Predicted Power Density")
    ax.legend(frameon=False)
    fig.colorbar(hb, ax=ax, label="Hours per hexagon", shrink=0.85)
    out = folder / "step1_actual_vs_predicted_density.png"
    save(fig, out)
    outputs.append(out)

    bins = pd.IntervalIndex.from_breaks([0, 25, 50, 100, 150, 200, 250], closed="left")
    frame = predictions.assign(abs_error=error.abs(), power_bin=pd.cut(predictions["actual_power_mw"], bins))
    grouped = frame.groupby("power_bin", observed=False)["abs_error"].mean().dropna()
    bin_labels = [f"{int(item.left)}-{int(item.right)}" for item in grouped.index]
    fig, ax = new_figure()
    bars = ax.bar(bin_labels, grouped.values, color=NAVY)
    ax.set_xlabel("Actual power range (MW)")
    ax.set_ylabel("Mean absolute error (MW)")
    ax.set_title("Forecast Error Is Larger During Higher-Power Operation")
    ax.grid(axis="y")
    label_bars(ax, bars, grouped.tolist(), "", 1)
    ax.set_ylim(0, grouped.max() * 1.18)
    out = folder / "step1_error_by_power_bin.png"
    save(fig, out)
    outputs.append(out)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=190, constrained_layout=True)
    for ax, variable, title in (
        (axes[0], "generation_mw", "Wind-generation forecast"),
        (axes[1], "price_normalized", "Normalized-price forecast"),
    ):
        data = lead[lead["variable"] == variable]
        ax.plot(data["lead_hours"], data["rmse"], marker="o", color=TEAL, lw=2.1, label="RMSE")
        ax.plot(data["lead_hours"], data["mae"], marker="s", color=STEEL, lw=1.8, label="MAE")
        ax.set_title(title)
        ax.set_xlabel("Forecast lead group (hours)")
        ax.set_ylabel("Error")
        ax.grid(True)
        ax.legend(frameon=False)
    fig.suptitle("Dispatch-Forecast Accuracy Declines with Lead Time", fontsize=15, fontweight="bold", color=INK)
    out = folder / "step1_dispatch_forecast_accuracy_by_lead.png"
    save(fig, out)
    outputs.append(out)

    keep = splits[splits["model"].isin(["causal_lag_ridge", "lag1_persistence", "speed_power_curve"])].copy()
    split_order = ["train", "validation", "test"]
    fig, ax = new_figure()
    for color, (name, data) in zip([TEAL, STEEL, PLUM], keep.groupby("model", sort=False)):
        data = data.set_index("split").loc[split_order]
        ax.plot(split_order, data["rmse_mw"], marker="o", lw=2.1, color=color, label=name.replace("_", " ").title())
    ax.set_ylabel("RMSE (MW)")
    ax.set_title("Forecast Stability Across Train, Validation, and Test Splits")
    ax.grid(True)
    ax.legend(frameon=False)
    out = folder / "step1_split_stability.png"
    save(fig, out)
    outputs.append(out)
    return outputs


def heatmap_scorecard(ax, columns: list[str], rows: list[str], values: np.ndarray, text: list[list[str]], title: str) -> None:
    normalized = values.astype(float).copy()
    for row in range(normalized.shape[0]):
        lo, hi = np.nanmin(normalized[row]), np.nanmax(normalized[row])
        normalized[row] = 0.5 if hi == lo else (normalized[row] - lo) / (hi - lo)
    ax.imshow(normalized, cmap="BuGn", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(columns)), columns)
    ax.set_yticks(range(len(rows)), rows)
    ax.set_title(title)
    for i in range(len(rows)):
        for j in range(len(columns)):
            color = "white" if normalized[i, j] >= 0.62 else INK
            ax.text(j, i, text[i][j], ha="center", va="center", fontsize=10, color=color)
    ax.tick_params(length=0)


def generate_step2() -> list[Path]:
    folder = REU / "rolling horizon" / "figures"
    clear_pngs(folder)
    data = pd.read_csv(
        REU / "rolling horizon" / "results" / "controlled_hourly_nowcast_from_knobs" / "controlled_single_forecast_horizon_summary.csv"
    ).sort_values("horizon_hours")
    horizons = data["horizon_hours"].astype(int).tolist()
    xlabels = [f"{value} h" for value in horizons]
    gains = data["cove_reduction_vs_100mw_baseload_pct"].tolist()
    coves = data["dispatch_cove_index"].tolist()
    revenues = (data["dispatch_revenue"] / 1e6).tolist()
    runtimes = data["total_solver_runtime_seconds"].tolist()
    best = int(np.argmax(gains))
    outputs: list[Path] = []

    fig, ax = new_figure()
    ax.plot(xlabels, gains, marker="o", ms=7, lw=2.3, color=TEAL)
    for x, value in zip(xlabels, gains):
        ax.text(x, value + 0.18, f"{value:.2f}%", ha="center", fontsize=9)
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Longer Planning Horizons Improved the Controlled Controller")
    ax.set_ylim(min(gains) - 0.5, max(gains) + 0.8)
    ax.grid(True)
    out = folder / "step2_controlled_hourly_horizon_improvement.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    ax.plot(xlabels, coves, marker="o", ms=7, lw=2.3, color=NAVY)
    for x, value in zip(xlabels, coves):
        ax.text(x, value + 0.012, f"{value:.3f}", ha="center", fontsize=9)
    ax.set_ylabel("COVE index (lower is better)")
    ax.set_title("COVE by Planning Horizon")
    ax.set_ylim(min(coves) - 0.06, max(coves) + 0.09)
    ax.grid(True)
    ax.text(
        0.98,
        0.94,
        f"100 MW benchmark COVE = {float(data.iloc[0]['100mw_baseload_cove']):.3f} (off scale)",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        color=STEEL,
        bbox={"facecolor": "white", "edgecolor": LIGHT, "pad": 4},
    )
    out = folder / "step2_controlled_hourly_horizon_cove.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    bars = ax.bar(xlabels, revenues, color=color_best(len(revenues), best))
    ax.set_ylabel("Normalized price-weighted revenue metric (millions)")
    ax.set_title("Reported Revenue Metric by Controlled Planning Horizon")
    ax.grid(axis="y")
    label_bars(ax, bars, revenues, "M", 2)
    ax.set_ylim(0, max(revenues) * 1.15)
    out = folder / "step2_controlled_hourly_horizon_revenue.png"
    save(fig, out)
    outputs.append(out)

    increments = [gains[0]] + [gains[index] - gains[index - 1] for index in range(1, len(gains))]
    fig, ax = new_figure()
    bars = ax.bar(xlabels, increments, color=[NAVY, TEAL, STEEL, PLUM])
    ax.set_ylabel("Additional COVE reduction (percentage points)")
    ax.set_title("Diminishing Returns from Extending the Planning Horizon")
    ax.grid(axis="y")
    label_bars(ax, bars, increments, " pp", 2)
    ax.set_ylim(0, max(increments) * 1.16)
    out = folder / "step2_incremental_cove_gain.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    ax.scatter(runtimes, gains, s=95, color=TEAL)
    for runtime, gain, horizon in zip(runtimes, gains, horizons):
        ax.annotate(f"{horizon} h", (runtime, gain), xytext=(7, 6), textcoords="offset points")
    ax.set_xlabel("Total solver runtime (seconds)")
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Planning Value vs Computational Cost")
    ax.grid(True)
    out = folder / "step2_runtime_value_tradeoff.png"
    save(fig, out)
    outputs.append(out)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=190, constrained_layout=True)
    axes[0].plot(xlabels, revenues, marker="o", color=TEAL, lw=2.2)
    axes[0].set_title("Revenue metric")
    axes[0].set_ylabel("Millions")
    axes[0].grid(True)
    axes[1].plot(xlabels, coves, marker="o", color=NAVY, lw=2.2)
    axes[1].set_title("COVE index")
    axes[1].set_ylabel("Lower is better")
    axes[1].grid(True)
    fig.suptitle("Horizon Changes Revenue and COVE Together", fontsize=15, fontweight="bold", color=INK)
    out = folder / "step2_revenue_cove_small_multiples.png"
    save(fig, out)
    outputs.append(out)

    score_values = np.array([revenues, gains, [-value for value in runtimes]])
    score_text = [
        [f"{value:.2f}M" for value in revenues],
        [f"{value:.2f}%" for value in gains],
        [f"{value:.0f}s" for value in runtimes],
    ]
    fig, ax = new_figure(10, 4.8)
    heatmap_scorecard(ax, xlabels, ["Revenue", "COVE reduction", "Runtime"], score_values, score_text, "Controlled Horizon Scorecard")
    out = folder / "step2_horizon_scorecard.png"
    save(fig, out)
    outputs.append(out)
    return outputs


def generate_step3() -> list[Path]:
    folder = REU / "different scenarios" / "figures"
    clear_pngs(folder)
    data = pd.read_csv(REU / "different scenarios" / "results" / "frozen_controlled" / "scenario_summary_vs_wind_only_and_100mw.csv")
    labels = [scenario_label(value) for value in data["candidate"]]
    counts = [1, 3, 5, 7, 10]
    gains = data["cove_reduction_vs_100mw_baseload_pct"].tolist()
    revenue_gains = data["revenue_gain_vs_100mw_baseload_pct"].tolist()
    revenues = (data["dispatch_revenue"] / 1e6).tolist()
    coves = data["dispatch_cove_index"].tolist()
    runtimes = data["total_solver_runtime_seconds"].tolist()
    best = int(np.argmax(gains))
    best_multi = 1 + int(np.argmax(gains[1:]))
    colors = color_best(len(labels), best)
    outputs: list[Path] = []

    fig, ax = new_figure()
    bars = ax.bar(labels, gains, color=colors)
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Scenario Count Did Not Automatically Improve Dispatch")
    ax.grid(axis="y")
    label_bars(ax, bars, gains, "%", 2)
    ax.set_ylim(0, max(gains) * 1.16)
    out = folder / "step3_scenario_cove_improvement.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    bars = ax.bar(labels, revenue_gains, color=colors)
    ax.set_ylabel("Revenue-metric gain vs 100 MW benchmark (%)")
    ax.set_title("Revenue-Metric Gain by Scenario Count")
    ax.grid(axis="y")
    label_bars(ax, bars, revenue_gains, "%", 2)
    ax.set_ylim(0, max(revenue_gains) * 1.16)
    out = folder / "step3_scenario_revenue_gain.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    ax.plot(revenue_gains, gains, color=STEEL, lw=1.7, zorder=1)
    for label, x, y, color in zip(labels, revenue_gains, gains, [NAVY, TEAL, STEEL, PLUM, GRAY]):
        ax.scatter(x, y, s=90, color=color, label=label, zorder=2)
    ax.set_xlabel("Revenue-metric gain vs 100 MW benchmark (%)")
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Scenario Revenue-COVE Tradeoff")
    ax.grid(True)
    ax.legend(frameon=False, ncol=2, loc="lower right")
    out = folder / "step3_revenue_cove_tradeoff.png"
    save(fig, out)
    outputs.append(out)

    ladder_labels = ["100 MW benchmark", "1 forecast", "Best multi-scenario"]
    ladder_values = [float(data.iloc[0]["100mw_baseload_revenue"]) / 1e6, revenues[0], revenues[best_multi]]
    fig, ax = new_figure()
    bars = ax.bar(ladder_labels, ladder_values, color=[GRAY, TEAL, PLUM])
    ax.set_ylabel("Normalized price-weighted revenue metric (millions)")
    ax.set_title("Benchmark, Single Forecast, and Best Multi-Scenario Case")
    ax.grid(axis="y")
    label_bars(ax, bars, ladder_values, "M", 2)
    ax.set_ylim(0, max(ladder_values) * 1.15)
    out = folder / "step3_ladder_revenue_progression.png"
    save(fig, out)
    outputs.append(out)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=190, constrained_layout=True)
    axes[0].plot(counts, revenues, marker="o", color=TEAL, lw=2.2)
    axes[0].set_title("Revenue metric")
    axes[0].set_xlabel("Number of forecast futures")
    axes[0].set_ylabel("Millions")
    axes[0].set_xticks(counts)
    axes[0].grid(True)
    axes[1].plot(counts, coves, marker="o", color=NAVY, lw=2.2)
    axes[1].set_title("COVE index")
    axes[1].set_xlabel("Number of forecast futures")
    axes[1].set_ylabel("Lower is better")
    axes[1].set_xticks(counts)
    axes[1].grid(True)
    fig.suptitle("Readable 2D Scenario Scorecard", fontsize=15, fontweight="bold", color=INK)
    out = folder / "step3_scenario_scorecard.png"
    save(fig, out)
    outputs.append(out)

    deltas = [value - gains[0] for value in gains]
    fig, ax = new_figure()
    bars = ax.bar(labels, deltas, color=[GRAY if value == 0 else PLUM for value in deltas])
    ax.axhline(0, color=INK, lw=1.1)
    ax.set_ylabel("COVE-reduction change vs one forecast (percentage points)")
    ax.set_title("Every Tested Multi-Scenario Set Trailed the Single Forecast")
    ax.grid(axis="y")
    label_bars(ax, bars, deltas, " pp", 2)
    ax.set_ylim(min(deltas) - 0.25, 0.35)
    out = folder / "step3_delta_vs_one_forecast.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    bars = ax.bar(labels, runtimes, color=[NAVY, TEAL, STEEL, PLUM, GRAY])
    ax.set_ylabel("Total solver runtime (seconds)")
    ax.set_title("Scenario Count Increased Computational Cost")
    ax.grid(axis="y")
    label_bars(ax, bars, runtimes, "s", 0)
    ax.set_ylim(0, max(runtimes) * 1.16)
    out = folder / "step3_runtime_by_scenario_count.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    ax.plot(counts, gains, marker="o", color=TEAL, lw=2.2)
    ax.axhline(gains[0], color=NAVY, ls="--", lw=1.4, label=f"Single forecast = {gains[0]:.2f}%")
    ax.set_xticks(counts)
    ax.set_xlabel("Number of forecast futures")
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Scenario-Count Sensitivity at the Frozen 168-Hour Horizon")
    ax.grid(True)
    ax.legend(frameon=False)
    out = folder / "step3_scenario_count_sensitivity.png"
    save(fig, out)
    outputs.append(out)
    return outputs


def generate_step4() -> list[Path]:
    folder = REU / "oracle upper bound" / "figures"
    clear_pngs(folder)
    data = pd.read_csv(REU / "oracle upper bound" / "results" / "frozen_controlled" / "forecast_dispatch_summary.csv").sort_values("horizon_hours")
    horizons = data["horizon_hours"].astype(int).tolist()
    xlabels = [f"{value} h" for value in horizons]
    gains = data["cove_improvement_vs_100mw_baseload_pct"].tolist()
    coves = data["cove"].tolist()
    revenues = (data["revenue_metric"] / 1e6).tolist()
    runtimes = data["solver_runtime_seconds"].tolist()
    best = int(np.argmax(gains))
    outputs: list[Path] = []

    fig, ax = new_figure()
    bars = ax.bar(xlabels, gains, color=color_best(len(gains), best))
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Perfect-Information Oracle by Rolling-Window Length")
    ax.grid(axis="y")
    label_bars(ax, bars, gains, "%", 2)
    ax.set_ylim(0, max(gains) * 1.16)
    out = folder / "step4_oracle_improvement_by_horizon.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    ax.plot(xlabels, coves, marker="o", color=NAVY, lw=2.3)
    for x, value in zip(xlabels, coves):
        ax.text(x, value + 0.0022, f"{value:.3f}", ha="center", fontsize=9)
    ax.set_ylabel("COVE index (lower is better)")
    ax.set_title("Oracle COVE Nearly Plateaus after 48-72 Hours")
    ax.set_ylim(min(coves) - 0.012, max(coves) + 0.018)
    ax.grid(True)
    ax.text(
        0.98,
        0.94,
        f"100 MW benchmark COVE = {float(data.iloc[0]['constant_output_100mw_cove']):.3f} (off scale)",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        color=STEEL,
        bbox={"facecolor": "white", "edgecolor": LIGHT, "pad": 4},
    )
    out = folder / "step4_oracle_cove_by_horizon.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    ax.scatter(runtimes, gains, color=TEAL, s=95)
    offsets = [(7, 7), (-5, 11), (8, -17), (7, 7)]
    for runtime, gain, horizon, offset in zip(runtimes, gains, horizons, offsets):
        ax.annotate(f"{horizon} h", (runtime, gain), xytext=offset, textcoords="offset points")
    ax.set_xlabel("Total solver runtime (seconds)")
    ax.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    ax.set_title("Oracle Value vs Computational Cost")
    ax.grid(True)
    out = folder / "step4_oracle_runtime_value_tradeoff.png"
    save(fig, out)
    outputs.append(out)

    fig, ax = new_figure()
    bars = ax.bar(xlabels, revenues, color=color_best(len(revenues), best))
    ax.set_ylabel("Normalized price-weighted revenue metric (millions)")
    ax.set_title("Oracle Revenue Metric by Rolling-Window Length")
    ax.grid(axis="y")
    label_bars(ax, bars, revenues, "M", 3)
    ax.set_ylim(0, max(revenues) * 1.15)
    out = folder / "step4_oracle_revenue_by_horizon.png"
    save(fig, out)
    outputs.append(out)

    increments = [gains[0]] + [gains[index] - gains[index - 1] for index in range(1, len(gains))]
    fig, ax = new_figure()
    bars = ax.bar(xlabels, increments, color=[NAVY, TEAL, STEEL, PLUM])
    ax.set_ylabel("Additional COVE reduction (percentage points)")
    ax.set_title("Additional Perfect Information Has Sharply Diminishing Returns")
    ax.grid(axis="y")
    label_bars(ax, bars, increments, " pp", 3)
    ax.set_ylim(0, max(increments) * 1.16)
    out = folder / "step4_incremental_oracle_gain.png"
    save(fig, out)
    outputs.append(out)

    gap = [gains[-1] - value for value in gains]
    fig, ax = new_figure()
    bars = ax.bar(xlabels, gap, color=[STEEL, TEAL, PLUM, GRAY])
    ax.set_ylabel("Remaining gap to 168-hour Oracle (percentage points)")
    ax.set_title("Most Oracle Value Is Already Captured by 48 Hours")
    ax.grid(axis="y")
    label_bars(ax, bars, gap, " pp", 3)
    ax.set_ylim(0, max(gap) * 1.20)
    out = folder / "step4_gap_to_168h_oracle.png"
    save(fig, out)
    outputs.append(out)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=190, constrained_layout=True)
    axes[0].plot(xlabels, revenues, marker="o", color=TEAL, lw=2.2)
    axes[0].set_title("Revenue metric")
    axes[0].set_ylabel("Millions")
    axes[0].grid(True)
    axes[1].plot(xlabels, coves, marker="o", color=NAVY, lw=2.2)
    axes[1].set_title("COVE index")
    axes[1].set_ylabel("Lower is better")
    axes[1].grid(True)
    fig.suptitle("Readable 2D Oracle Scorecard", fontsize=15, fontweight="bold", color=INK)
    out = folder / "step4_oracle_scorecard.png"
    save(fig, out)
    outputs.append(out)
    return outputs


GENERATORS = {
    "0": generate_step0,
    "1": generate_step1,
    "2": generate_step2,
    "3": generate_step3,
    "4": generate_step4,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", choices=["all", *GENERATORS], default="all")
    args = parser.parse_args()
    set_style()
    selected = GENERATORS.items() if args.step == "all" else [(args.step, GENERATORS[args.step])]
    outputs: list[Path] = []
    for step, generator in selected:
        generated = generator()
        outputs.extend(generated)
        print(f"Step {step}: generated {len(generated)} figures")
    print(f"Total generated: {len(outputs)} figures")
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
