from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "best_forecast_dispatch_search_results"

sys.path.insert(0, str(BASE_DIR))
import run_nora_matching_forecast_horizons as base  # noqa: E402


MAX_HORIZON = 168
HORIZONS = [24, 48, 72, 168]
PRICE_CLIP = (-500.0, 1500.0)


def matrix_from_indices(values: np.ndarray, origins: np.ndarray, indexer) -> np.ndarray:
    forecasts = np.empty((len(origins), MAX_HORIZON), dtype=float)
    for row, origin in enumerate(origins):
        for lead in range(MAX_HORIZON):
            idx = indexer(int(origin), lead)
            forecasts[row, lead] = values[idx]
    return forecasts


def actual_future_matrix(values: np.ndarray, origins: np.ndarray) -> np.ndarray:
    return np.vstack([values[origin : origin + MAX_HORIZON] for origin in origins])


def hourly_climatology_matrix(
    values: np.ndarray,
    datetimes: pd.Series,
    train_end: int,
    origins: np.ndarray,
    statistic: str,
) -> np.ndarray:
    train_dt = pd.DatetimeIndex(datetimes.iloc[:train_end])
    hour_of_week = train_dt.dayofweek * 24 + train_dt.hour
    train = pd.DataFrame({"how": hour_of_week, "value": values[:train_end]})
    if statistic == "median":
        lookup = train.groupby("how")["value"].median()
    else:
        lookup = train.groupby("how")["value"].mean()

    target_dt = pd.DatetimeIndex(datetimes)
    target_how = target_dt.dayofweek * 24 + target_dt.hour
    forecasts = np.empty((len(origins), MAX_HORIZON), dtype=float)
    for row, origin in enumerate(origins):
        for lead in range(MAX_HORIZON):
            forecasts[row, lead] = float(lookup.loc[int(target_how[origin + lead])])
    return forecasts


def clip_generation(forecasts: np.ndarray) -> np.ndarray:
    return np.clip(forecasts, 0.0, max(base.GRID_CAP, float(forecasts.max())))


def clip_price(forecasts: np.ndarray) -> np.ndarray:
    return np.clip(forecasts, PRICE_CLIP[0], PRICE_CLIP[1])


def cove_reduction_from_revenues(dispatch_revenue: float, baseload_revenue: float) -> float:
    return (1.0 - baseload_revenue / dispatch_revenue) * 100.0


def candidate_summary(
    labels: pd.DataFrame,
    candidate: str,
    wind_forecast: str,
    price_forecast: str,
    horizon: int,
    is_oracle: bool,
) -> dict[str, float | str | int | bool]:
    actual_generation = labels["actual_generation_mw"].to_numpy(float)
    actual_price = labels["actual_price"].to_numpy(float)
    baseload = base.continuous_baseload(actual_generation)
    wind_only = np.minimum(actual_generation, base.GRID_CAP)
    delivered = labels["realized_delivered_mw"].to_numpy(float)

    baseload_revenue = base.revenue(baseload, actual_price)
    wind_only_revenue = base.revenue(wind_only, actual_price)
    dispatch_revenue = base.revenue(delivered, actual_price)
    cost = base.annualized_dispatch_cost()

    row: dict[str, float | str | int | bool] = {
        "candidate": candidate,
        "wind_forecast": wind_forecast,
        "price_forecast": price_forecast,
        "horizon_hours": int(horizon),
        "is_oracle": bool(is_oracle),
        "hours": int(len(labels)),
        "test_start": str(labels["datetime"].iloc[0]),
        "test_end": str(labels["datetime"].iloc[-1]),
        "wind_only_revenue": wind_only_revenue,
        "baseload_revenue": baseload_revenue,
        "dispatch_revenue": dispatch_revenue,
        "dispatch_cove_index": cost / dispatch_revenue,
        "baseload_cove_index": cost / baseload_revenue,
        "revenue_gain_vs_baseload_pct": (dispatch_revenue / baseload_revenue - 1.0) * 100.0,
        "cove_reduction_vs_baseload_pct": cove_reduction_from_revenues(dispatch_revenue, baseload_revenue),
        "final_soc": float(labels["soc_end_mwh"].iloc[-1]),
        "min_soc": float(min(labels["soc_start_mwh"].min(), labels["soc_end_mwh"].min())),
        "max_soc": float(max(labels["soc_start_mwh"].max(), labels["soc_end_mwh"].max())),
        "sum_charge_mwh": float(labels["realized_charge_mw"].sum()),
        "sum_discharge_mwh": float(labels["realized_discharge_mw"].sum()),
    }
    row.update(base.check_realized_constraints(labels))
    return row


def evaluate_forecasts(
    values: np.ndarray,
    origins: np.ndarray,
    forecast_map: dict[str, np.ndarray],
    variable: str,
) -> pd.DataFrame:
    rows = []
    for name, forecasts in forecast_map.items():
        metrics = base.forecast_metrics(values, origins, forecasts, variable)
        metrics.insert(0, "forecast", name)
        rows.append(metrics)
    return pd.concat(rows, ignore_index=True)


def legacy_power_model_metrics() -> pd.DataFrame:
    rows: list[dict[str, float | str | int]] = []

    causal_path = REPO / "power_model" / "evaluation" / "causal_lag_forecast_predictions.csv"
    if causal_path.exists():
        causal = pd.read_csv(causal_path, parse_dates=["datetime"])
        actual = causal["actual_power_mw"].to_numpy(float)
        for column in [
            "causal_lag_prediction_mw",
            "speed_power_curve_prediction_mw",
            "lag1_persistence_prediction_mw",
        ]:
            pred = causal[column].to_numpy(float)
            error = pred - actual
            rows.append(
                {
                    "source": "causal_lag_forecast_predictions.csv",
                    "model": column,
                    "start": str(causal["datetime"].iloc[0]),
                    "end": str(causal["datetime"].iloc[-1]),
                    "samples": int(len(causal)),
                    "rmse_mw": float(np.sqrt(np.mean(error**2))),
                    "mae_mw": float(np.mean(np.abs(error))),
                    "bias_mw": float(np.mean(error)),
                }
            )

    pyron_path = REPO / "power_model" / "evaluation" / "pyron_model_results.csv"
    if pyron_path.exists():
        pyron = pd.read_csv(pyron_path, parse_dates=["datetime"])
        actual = pyron["historical_power"].to_numpy(float)
        for column in ["physics_preds", "prob_preds", "rnn_preds"]:
            pred = pyron[column].to_numpy(float)
            error = pred - actual
            rows.append(
                {
                    "source": "pyron_model_results.csv",
                    "model": column,
                    "start": str(pyron["datetime"].iloc[0]),
                    "end": str(pyron["datetime"].iloc[-1]),
                    "samples": int(len(pyron)),
                    "rmse_mw": float(np.sqrt(np.mean(error**2))),
                    "mae_mw": float(np.mean(np.abs(error))),
                    "bias_mw": float(np.mean(error)),
                }
            )

    return pd.DataFrame(rows)


def make_figures(summary: pd.DataFrame, forecast_metrics: pd.DataFrame, legacy_metrics: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    real = summary[~summary["is_oracle"]].copy()
    best_by_candidate = (
        real.sort_values("dispatch_revenue", ascending=False)
        .groupby("candidate", as_index=False)
        .head(1)
        .sort_values("dispatch_revenue", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(11, 6), dpi=220)
    bars = ax.barh(best_by_candidate["candidate"], best_by_candidate["dispatch_revenue"] / 1e6, color="#2563eb")
    best_idx = int(np.argmax(best_by_candidate["dispatch_revenue"].to_numpy()))
    bars[best_idx].set_color("#16a34a")
    ax.axvline(best_by_candidate["baseload_revenue"].iloc[0] / 1e6, color="#64748b", linestyle="--", label="Baseload")
    ax.set_xlabel("Realized revenue, 2014-2023 ($ millions)")
    ax.set_title("Best horizon from each strict forecast candidate")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figure_01_best_candidate_revenue.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    top_candidates = best_by_candidate.tail(5)["candidate"].tolist()
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=220)
    for candidate in top_candidates:
        selected = real[real["candidate"] == candidate].sort_values("horizon_hours")
        ax.plot(
            selected["horizon_hours"],
            selected["dispatch_revenue"] / 1e6,
            marker="o",
            linewidth=2.0,
            label=candidate,
        )
    ax.axhline(real["baseload_revenue"].iloc[0] / 1e6, color="#64748b", linestyle="--", label="Baseload")
    ax.set_xlabel("Planning horizon (hours)")
    ax.set_ylabel("Realized revenue ($ millions)")
    ax.set_title("Horizon sensitivity for the best strict forecast candidates")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "figure_02_horizon_sensitivity.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=220)
    for axis, variable, title in [
        (axes[0], "generation_mw", "Wind forecast RMSE"),
        (axes[1], "price_raw", "Price forecast RMSE"),
    ]:
        subset = forecast_metrics[forecast_metrics["variable"] == variable]
        for name, group in subset.groupby("forecast"):
            axis.plot(group["lead_hours"], group["rmse"], marker="o", linewidth=1.8, label=name)
        axis.set_title(title)
        axis.set_xlabel("Forecast lead")
        axis.set_ylabel("RMSE")
        axis.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "figure_03_forecast_rmse_by_method.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    if not legacy_metrics.empty:
        ordered = legacy_metrics.sort_values("rmse_mw", ascending=True)
        fig, ax = plt.subplots(figsize=(10, 5), dpi=220)
        ax.barh(ordered["model"], ordered["rmse_mw"], color="#0f766e")
        ax.set_xlabel("RMSE (MW)")
        ax.set_title("Existing power-model output files: lower RMSE is better")
        fig.tight_layout()
        fig.savefig(OUT / "figure_04_existing_power_model_rmse.png", facecolor="white", bbox_inches="tight")
        plt.close(fig)

    oracle = summary[summary["is_oracle"]].copy()
    if not oracle.empty:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=220)
        best_real = real.sort_values("dispatch_revenue", ascending=False).iloc[0]
        best_oracle = oracle.sort_values("dispatch_revenue", ascending=False).iloc[0]
        values = [
            best_real["baseload_revenue"] / 1e6,
            best_real["dispatch_revenue"] / 1e6,
            best_oracle["dispatch_revenue"] / 1e6,
        ]
        names = ["Baseload", "Best realistic", "Oracle upper bound"]
        ax.bar(names, values, color=["#64748b", "#16a34a", "#7c3aed"])
        ax.set_ylabel("Realized revenue ($ millions)")
        ax.set_title("Realistic best vs perfect-future upper bound")
        fig.tight_layout()
        fig.savefig(OUT / "figure_05_realistic_vs_oracle.png", facecolor="white", bbox_inches="tight")
        plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(base.DATA_PATH, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df[["datetime", "power_generated", "lmp", "user_load_zonal"]].dropna().reset_index(drop=True)

    train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64("2014-01-01")))
    origins = np.arange(train_end, len(df), base.STEP_HOURS)
    origins = origins[origins + MAX_HORIZON <= len(df)]

    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)

    print("Validating Nora one-week convention...", flush=True)
    nora_validation = base.validate_nora_week()
    print(nora_validation, flush=True)
    print(
        f"Strict test: train forecasts through {df['datetime'].iloc[train_end - 1]}, "
        f"test daily origins {df['datetime'].iloc[origins[0]]} through "
        f"{df['datetime'].iloc[origins[-1] + MAX_HORIZON - 1]}",
        flush=True,
    )

    print("Building wind forecast variants...", flush=True)
    generation_models = base.fit_direct_models(
        generation,
        df["datetime"],
        train_end,
        MAX_HORIZON,
        0.0,
        max(float(generation[:train_end].max()), base.GRID_CAP),
        alpha=10.0,
        origin_stride=24,
    )
    wind_ridge = base.make_generation_forecasts(generation, df["datetime"], origins, generation_models)
    wind_weekly = matrix_from_indices(generation, origins, lambda origin, lead: origin + lead - 168)
    wind_daily = matrix_from_indices(generation, origins, lambda origin, lead: origin + lead - 24)
    wind_last = matrix_from_indices(generation, origins, lambda origin, lead: origin - 1)
    wind_how_mean = hourly_climatology_matrix(generation, df["datetime"], train_end, origins, "mean")
    wind_blend = 0.65 * wind_ridge + 0.35 * wind_weekly

    wind_forecasts = {
        "ridge_direct": clip_generation(wind_ridge),
        "weekly_persistence": clip_generation(wind_weekly),
        "daily_persistence": clip_generation(wind_daily),
        "last_value": clip_generation(wind_last),
        "hour_of_week_mean": clip_generation(wind_how_mean),
        "ridge_weekly_blend": clip_generation(wind_blend),
    }

    print("Building price forecast variants...", flush=True)
    price_models = base.fit_direct_models(
        price,
        df["datetime"],
        train_end,
        MAX_HORIZON,
        float(max(PRICE_CLIP[0], np.nanmin(price[:train_end]))),
        float(min(PRICE_CLIP[1], np.nanmax(price[:train_end]))),
        alpha=100.0,
        origin_stride=24,
    )
    price_ridge = base.make_generation_forecasts(price, df["datetime"], origins, price_models)
    price_weekly = base.make_weekly_price_forecasts(price, origins, MAX_HORIZON)
    price_daily = matrix_from_indices(price, origins, lambda origin, lead: origin + lead - 24)
    price_last = matrix_from_indices(price, origins, lambda origin, lead: origin - 1)
    price_how_median = hourly_climatology_matrix(price, df["datetime"], train_end, origins, "median")
    price_blend = 0.45 * price_ridge + 0.55 * price_weekly

    price_forecasts = {
        "weekly_persistence": clip_price(price_weekly),
        "daily_persistence": clip_price(price_daily),
        "last_value": clip_price(price_last),
        "ridge_direct": clip_price(price_ridge),
        "hour_of_week_median": clip_price(price_how_median),
        "ridge_weekly_blend": clip_price(price_blend),
    }

    forecast_metrics = pd.concat(
        [
            evaluate_forecasts(generation, origins, wind_forecasts, "generation_mw"),
            evaluate_forecasts(price, origins, price_forecasts, "price_raw"),
        ],
        ignore_index=True,
    )
    forecast_metrics.to_csv(OUT / "strict_forecast_variant_metrics.csv", index=False)

    legacy_metrics = legacy_power_model_metrics()
    legacy_metrics.to_csv(OUT / "existing_power_model_metrics.csv", index=False)

    candidates = [
        ("current_ridge_wind_weekly_price", "ridge_direct", "weekly_persistence"),
        ("ridge_wind_daily_price", "ridge_direct", "daily_persistence"),
        ("ridge_wind_last_price", "ridge_direct", "last_value"),
        ("ridge_wind_ridge_price", "ridge_direct", "ridge_direct"),
        ("ridge_wind_price_blend", "ridge_direct", "ridge_weekly_blend"),
        ("weekly_wind_weekly_price", "weekly_persistence", "weekly_persistence"),
        ("daily_wind_weekly_price", "daily_persistence", "weekly_persistence"),
        ("blend_wind_weekly_price", "ridge_weekly_blend", "weekly_persistence"),
        ("blend_wind_price_blend", "ridge_weekly_blend", "ridge_weekly_blend"),
        ("how_mean_wind_weekly_price", "hour_of_week_mean", "weekly_persistence"),
    ]

    summary_rows: list[dict[str, float | str | int | bool]] = []
    best_labels: pd.DataFrame | None = None
    best_revenue = -math.inf
    total_runs = len(candidates) * len(HORIZONS)
    run_number = 0

    for candidate, wind_name, price_name in candidates:
        for horizon in HORIZONS:
            run_number += 1
            print(f"[{run_number}/{total_runs}] {candidate}, horizon={horizon}h", flush=True)
            labels, _ = base.run_forecast_horizon(
                df,
                origins,
                wind_forecasts[wind_name],
                price_forecasts[price_name],
                horizon,
            )
            row = candidate_summary(labels, candidate, wind_name, price_name, horizon, False)
            summary_rows.append(row)
            pd.DataFrame(summary_rows).to_csv(OUT / "dispatch_search_summary_partial.csv", index=False)

            if float(row["dispatch_revenue"]) > best_revenue:
                best_revenue = float(row["dispatch_revenue"])
                best_labels = labels.copy()
                best_labels.to_csv(OUT / "best_realistic_dispatch_labels.csv", index=False)

    print("Running perfect-future oracle upper bound for context...", flush=True)
    actual_wind = actual_future_matrix(generation, origins)
    actual_price = actual_future_matrix(price, origins)
    for horizon in HORIZONS:
        labels, _ = base.run_forecast_horizon(df, origins, actual_wind, actual_price, horizon)
        summary_rows.append(
            candidate_summary(labels, "oracle_actual_wind_actual_price", "actual_future", "actual_future", horizon, True)
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "dispatch_search_summary.csv", index=False)

    metadata = {
        "nora_validation": nora_validation,
        "data_path": str(base.DATA_PATH),
        "training_end_exclusive": str(df["datetime"].iloc[train_end]),
        "test_start": str(df["datetime"].iloc[origins[0]]),
        "test_end": str(df["datetime"].iloc[origins[-1] + MAX_HORIZON - 1]),
        "strict_rule": "Forecasts are generated from information available at the daily origin, Gurobi optimizes the full horizon, only the first 24h are executed, and realized SoC carries forward.",
        "storage_constraints": {
            "power_mw": base.PS,
            "duration_hours": base.DURATION_HOURS,
            "cmax_mwh": base.CMAX,
            "cmin_mwh": base.CMIN,
            "soc0_mwh": base.SOC0,
            "rte": base.RTE,
            "grid_cap_mw": base.GRID_CAP,
        },
        "price_clip": PRICE_CLIP,
    }
    (OUT / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2))

    make_figures(summary, forecast_metrics, legacy_metrics)

    real = summary[~summary["is_oracle"]].sort_values("dispatch_revenue", ascending=False)
    oracle = summary[summary["is_oracle"]].sort_values("dispatch_revenue", ascending=False)

    print("\nTOP STRICT REALISTIC DISPATCH RESULTS")
    print(
        real[
            [
                "candidate",
                "horizon_hours",
                "dispatch_revenue",
                "baseload_revenue",
                "revenue_gain_vs_baseload_pct",
                "cove_reduction_vs_baseload_pct",
                "min_soc",
                "max_soc",
                "final_soc",
            ]
        ]
        .head(12)
        .to_string(index=False)
    )

    print("\nORACLE UPPER BOUND")
    print(
        oracle[
            [
                "candidate",
                "horizon_hours",
                "dispatch_revenue",
                "revenue_gain_vs_baseload_pct",
                "cove_reduction_vs_baseload_pct",
            ]
        ].to_string(index=False)
    )

    max_violation = max(
        float(summary[column].max())
        for column in summary.columns
        if column.startswith("max_") and column.endswith("_violation")
    )
    print(f"\nMaximum realized constraint violation across all runs: {max_violation:.3e}")
    print(f"Saved outputs to {OUT}")


if __name__ == "__main__":
    main()
