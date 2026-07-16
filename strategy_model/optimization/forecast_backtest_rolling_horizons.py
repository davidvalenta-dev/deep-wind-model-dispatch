"""Backtest rolling-horizon Gurobi dispatch with causal forecasts.

The forecasting models are trained on an early chronological period and frozen.
During the later backtest, every daily forecast uses only values observed before
that forecast was issued. Gurobi plans from forecast wind generation and price,
but only the first 24 hours are executed and scored against actual outcomes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
OPTIMIZATION_DIR = REPO_ROOT / "strategy_model" / "optimization"
for module_path in (STRATEGY_SRC, OPTIMIZATION_DIR):
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))

import util  # noqa: E402
from rolling_horizon_gurobi_dispatch import (  # noqa: E402
    continuous_baseload,
    cove_value,
    fixed_costs,
    solve_window,
)


PAST_LAGS = (1, 2, 3, 6, 12, 24, 48, 168)
HORIZONS = (24, 48, 72, 168)


@dataclass
class DirectForecastModel:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    coefficients: np.ndarray
    target_min: float
    target_max: float

    def predict(self, features: np.ndarray) -> float:
        standardized = (features - self.feature_mean) / self.feature_scale
        design = np.concatenate(([1.0], standardized))
        return float(np.clip(design @ self.coefficients, self.target_min, self.target_max))


def calendar_features(timestamps: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    dt = pd.DatetimeIndex(timestamps)
    hour = dt.hour.to_numpy(dtype=float)
    weekday = dt.dayofweek.to_numpy(dtype=float)
    day = dt.dayofyear.to_numpy(dtype=float)
    return np.column_stack(
        [
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
            np.sin(2 * np.pi * weekday / 7),
            np.cos(2 * np.pi * weekday / 7),
            np.sin(2 * np.pi * day / 365.25),
            np.cos(2 * np.pi * day / 365.25),
        ]
    )


def origin_features(values: np.ndarray, origins: np.ndarray) -> np.ndarray:
    lag_columns = [values[origins - lag] for lag in PAST_LAGS]
    rolling_24 = np.array([values[origin - 24 : origin] for origin in origins])
    rolling_168 = np.array([values[origin - 168 : origin] for origin in origins])
    return np.column_stack(
        [
            *lag_columns,
            rolling_24.mean(axis=1),
            rolling_24.std(axis=1),
            rolling_168.mean(axis=1),
            rolling_168.std(axis=1),
        ]
    )


def single_origin_features(values: np.ndarray, origin: int) -> np.ndarray:
    past = [values[origin - lag] for lag in PAST_LAGS]
    recent_24 = values[origin - 24 : origin]
    recent_168 = values[origin - 168 : origin]
    return np.asarray(
        [
            *past,
            recent_24.mean(),
            recent_24.std(),
            recent_168.mean(),
            recent_168.std(),
        ],
        dtype=float,
    )


def fit_direct_models(
    values: np.ndarray,
    datetimes: pd.Series,
    train_end: int,
    max_horizon: int,
    target_min: float,
    target_max: float,
    alpha: float,
    origin_stride: int,
) -> list[DirectForecastModel]:
    origins = np.arange(max(PAST_LAGS), train_end - max_horizon, origin_stride)
    base = origin_features(values, origins)
    models: list[DirectForecastModel] = []

    for lead in range(1, max_horizon + 1):
        target_indices = origins + lead - 1
        lead_fraction = np.full((len(origins), 1), lead / max_horizon)
        X = np.column_stack(
            [base, calendar_features(datetimes.iloc[target_indices]), lead_fraction]
        )
        y = values[target_indices]
        feature_mean = X.mean(axis=0)
        feature_scale = X.std(axis=0)
        feature_scale[feature_scale < 1e-8] = 1.0
        standardized = (X - feature_mean) / feature_scale
        design = np.column_stack([np.ones(len(X)), standardized])
        regularizer = alpha * np.eye(design.shape[1])
        regularizer[0, 0] = 0.0
        coefficients = np.linalg.solve(
            design.T @ design + regularizer, design.T @ y
        )
        models.append(
            DirectForecastModel(
                feature_mean=feature_mean,
                feature_scale=feature_scale,
                coefficients=coefficients,
                target_min=target_min,
                target_max=target_max,
            )
        )
    return models


def make_forecast_matrix(
    values: np.ndarray,
    datetimes: pd.Series,
    origins: np.ndarray,
    models: list[DirectForecastModel],
) -> np.ndarray:
    max_horizon = len(models)
    forecasts = np.empty((len(origins), max_horizon), dtype=float)
    for row_index, origin in enumerate(origins):
        base = single_origin_features(values, int(origin))
        target_times = datetimes.iloc[origin : origin + max_horizon]
        calendar = calendar_features(target_times)
        for lead_index, model in enumerate(models):
            features = np.concatenate(
                [base, calendar[lead_index], [(lead_index + 1) / max_horizon]]
            )
            forecasts[row_index, lead_index] = model.predict(features)
    return forecasts


def forecast_metrics(
    actual: np.ndarray,
    origins: np.ndarray,
    forecasts: np.ndarray,
    name: str,
) -> pd.DataFrame:
    rows = []
    buckets = ((1, 24), (25, 48), (49, 72), (73, 168))
    for start_lead, end_lead in buckets:
        lead_indices = np.arange(start_lead - 1, end_lead)
        predicted = forecasts[:, lead_indices].reshape(-1)
        observed = np.concatenate(
            [actual[origin + lead_indices] for origin in origins]
        )
        errors = predicted - observed
        rows.append(
            {
                "variable": name,
                "lead_hours": f"{start_lead}-{end_lead}",
                "rmse": float(np.sqrt(np.mean(errors**2))),
                "mae": float(np.mean(np.abs(errors))),
                "bias": float(np.mean(errors)),
                "correlation": float(np.corrcoef(predicted, observed)[0, 1]),
                "samples": len(errors),
            }
        )
    return pd.DataFrame(rows)


def execute_plan_against_actual(
    planned: dict,
    actual_generation: np.ndarray,
    initial_soc: float,
    config: dict,
    min_soc_frac: float,
    max_soc_frac: float,
) -> dict[str, np.ndarray]:
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(
        config["storage_rating"]
        * config["storage_duration"]
        * config["num_modules"]
    )
    rte = float(
        util.get_rte(
            config["storage_type"],
            config["storage_rating"],
            config["storage_duration"],
        )
    )
    grid_cap = float(config["rated_capacity"])
    min_soc = capacity * min_soc_frac
    max_soc = capacity * max_soc_frac
    n = len(actual_generation)

    direct = np.zeros(n)
    charge = np.zeros(n)
    discharge = np.zeros(n)
    delivered = np.zeros(n)
    curtailment = np.zeros(n)
    storage = np.zeros(n + 1)
    mode = np.zeros(n)
    storage[0] = float(np.clip(initial_soc, min_soc, max_soc))

    for t, generation in enumerate(actual_generation):
        planned_direct = float(planned["direct"][t])
        planned_charge = float(planned["charge"][t])
        planned_discharge = float(planned["discharge"][t])
        if planned_charge > planned_discharge:
            mode[t] = 1.0
            room = max(0.0, max_soc - storage[t])
            charge[t] = min(planned_charge, rating, max(generation, 0.0), room)
        else:
            available = max(0.0, (storage[t] - min_soc) * rte)
            discharge[t] = min(planned_discharge, rating, available)

        wind_after_charge = max(0.0, generation - charge[t])
        direct[t] = min(planned_direct, wind_after_charge, max(0.0, grid_cap - discharge[t]))
        delivered[t] = direct[t] + discharge[t]
        curtailment[t] = max(0.0, generation - direct[t] - charge[t])
        storage[t + 1] = storage[t] + charge[t] - discharge[t] / rte

    return {
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "delivered": delivered,
        "curtailment": curtailment,
        "storage": storage,
        "mode": mode,
    }


def check_realized_constraints(
    labels: pd.DataFrame,
    config: dict,
    min_soc_frac: float,
    max_soc_frac: float,
) -> dict[str, float]:
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(
        config["storage_rating"]
        * config["storage_duration"]
        * config["num_modules"]
    )
    rte = float(
        util.get_rte(
            config["storage_type"],
            config["storage_rating"],
            config["storage_duration"],
        )
    )
    min_soc = capacity * min_soc_frac
    max_soc = capacity * max_soc_frac
    gen = labels["actual_generation"].to_numpy()
    direct = labels["realized_direct"].to_numpy()
    charge = labels["realized_charge"].to_numpy()
    discharge = labels["realized_discharge"].to_numpy()
    delivered = labels["realized_delivered"].to_numpy()
    start = labels["soc_start"].to_numpy()
    end = labels["soc_end"].to_numpy()
    mode = labels["mode_binary_charge"].to_numpy()
    return {
        "max_wind_only_violation": float(
            np.maximum(direct + charge - gen, 0).max()
        ),
        "max_delivered_definition_violation": float(
            np.abs(delivered - direct - discharge).max()
        ),
        "max_grid_violation": float(
            np.maximum(delivered - float(config["rated_capacity"]), 0).max()
        ),
        "max_charge_limit_violation": float(
            np.maximum(charge - rating * mode, 0).max()
        ),
        "max_discharge_limit_violation": float(
            np.maximum(discharge - rating * (1 - mode), 0).max()
        ),
        "max_available_energy_violation": float(
            np.maximum(discharge / rte - (start - min_soc), 0).max()
        ),
        "max_soc_update_violation": float(
            np.abs(end - (start + charge - discharge / rte)).max()
        ),
        "max_soc_lower_violation": float(np.maximum(min_soc - start, 0).max()),
        "max_soc_upper_violation": float(np.maximum(start - max_soc, 0).max()),
    }


def run_horizon(
    df: pd.DataFrame,
    test_start: int,
    origins: np.ndarray,
    generation_forecasts: np.ndarray,
    price_forecasts: np.ndarray,
    horizon: int,
    config: dict,
    initial_soc: float,
    min_soc_frac: float,
    max_soc_frac: float,
    mip_gap: float,
    perfect_information: bool,
) -> tuple[pd.DataFrame, dict]:
    actual_generation = df["power_generated"].to_numpy(dtype=float)
    actual_price = df["price_normalized"].to_numpy(dtype=float)
    current_soc = initial_soc
    rows = []
    solver_runtime = 0.0
    started = time.perf_counter()

    for origin_row, origin in enumerate(origins):
        available_horizon = min(horizon, len(df) - origin)
        execute_len = min(24, len(df) - origin)
        if execute_len <= 0:
            break

        if perfect_information:
            planned_generation = actual_generation[origin : origin + available_horizon]
            planned_price = actual_price[origin : origin + available_horizon]
        else:
            planned_generation = generation_forecasts[
                origin_row, :available_horizon
            ]
            planned_price = price_forecasts[origin_row, :available_horizon]

        solution = solve_window(
            planned_generation,
            planned_price,
            config,
            current_soc,
            "equal-initial",
            min_soc_frac,
            max_soc_frac,
            mip_gap,
            None,
        )
        solver_runtime += float(solution["runtime"])
        realized = execute_plan_against_actual(
            solution,
            actual_generation[origin : origin + execute_len],
            current_soc,
            config,
            min_soc_frac,
            max_soc_frac,
        )

        for k in range(execute_len):
            hour = origin + k
            rows.append(
                {
                    "hour_index": hour,
                    "datetime": df["datetime"].iloc[hour],
                    "horizon_hours": horizon,
                    "perfect_information": perfect_information,
                    "actual_generation": actual_generation[hour],
                    "forecast_generation": planned_generation[k],
                    "actual_price": actual_price[hour],
                    "forecast_price": planned_price[k],
                    "planned_direct": float(solution["direct"][k]),
                    "planned_charge": float(solution["charge"][k]),
                    "planned_discharge": float(solution["discharge"][k]),
                    "realized_direct": realized["direct"][k],
                    "realized_charge": realized["charge"][k],
                    "realized_discharge": realized["discharge"][k],
                    "realized_delivered": realized["delivered"][k],
                    "realized_curtailment": realized["curtailment"][k],
                    "soc_start": realized["storage"][k],
                    "soc_end": realized["storage"][k + 1],
                    "mode_binary_charge": realized["mode"][k],
                }
            )
        current_soc = float(realized["storage"][-1])

        if (origin_row + 1) % 500 == 0:
            print(
                f"{'oracle' if perfect_information else 'forecast'} "
                f"{horizon} h: {origin_row + 1}/{len(origins)} windows, "
                f"SoC={current_soc:.1f}, elapsed={time.perf_counter() - started:.1f}s",
                flush=True,
            )

    labels = pd.DataFrame(rows)
    power = labels["actual_generation"].to_numpy()
    price = labels["actual_price"].to_numpy()
    delivered = labels["realized_delivered"].to_numpy()
    baseload = continuous_baseload(power, config, initial_soc=initial_soc)
    wind_cost, dispatch_cost = fixed_costs(config)
    revenue = float(util.revenue(delivered, price))
    baseload_revenue = float(util.revenue(baseload, price))
    cove = cove_value(delivered, price, config)
    baseload_cove = cove_value(baseload, price, config)
    constraints = check_realized_constraints(
        labels, config, min_soc_frac, max_soc_frac
    )
    summary = {
        "method": "oracle" if perfect_information else "causal_forecast",
        "horizon_hours": horizon,
        "hours": len(labels),
        "test_start": str(labels["datetime"].iloc[0]),
        "test_end": str(labels["datetime"].iloc[-1]),
        "revenue_metric": revenue,
        "baseload_revenue_metric": baseload_revenue,
        "cove": cove,
        "baseload_cove": baseload_cove,
        "improvement_vs_baseload_pct": (baseload_cove - cove)
        / baseload_cove
        * 100,
        "dispatch_cost": dispatch_cost,
        "profit_metric": revenue - dispatch_cost,
        "final_soc": float(labels["soc_end"].iloc[-1]),
        "solver_runtime_seconds": solver_runtime,
        **constraints,
    }
    return labels, summary


def style_axis(axis):
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    axis.set_axisbelow(True)


def save_figures(
    summary: pd.DataFrame,
    metrics: pd.DataFrame,
    labels_by_horizon: dict[int, pd.DataFrame],
    output_dir: Path,
):
    colors = ["#2563EB", "#0F766E", "#B45309", "#7C3AED"]
    forecast = summary[summary["method"] == "causal_forecast"].sort_values(
        "horizon_hours"
    )
    oracle = summary[summary["method"] == "oracle"].sort_values("horizon_hours")
    labels = [f"{int(value)} h" for value in forecast["horizon_hours"]]
    x = np.arange(len(labels))

    fig, axis = plt.subplots(figsize=(9, 5), dpi=220)
    width = 0.36
    axis.bar(
        x - width / 2,
        forecast["improvement_vs_baseload_pct"],
        width,
        label="Causal forecasts",
        color="#2563EB",
    )
    if not oracle.empty:
        axis.bar(
            x + width / 2,
            oracle["improvement_vs_baseload_pct"],
            width,
            label="Perfect future information",
            color="#CBD5E1",
        )
    axis.set_xticks(x, labels)
    axis.set_ylabel("COVE improvement vs baseload (%)")
    axis.set_title(
        "Realistic forecast dispatch versus perfect-information upper bound",
        fontweight="bold",
    )
    axis.legend(frameon=False)
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(
        output_dir / "figure_01_forecast_vs_oracle_improvement.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(9, 5), dpi=220)
    bars = axis.bar(labels, forecast["cove"], color=colors)
    for bar, value in zip(bars, forecast["cove"]):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value,
            f"{value:.4f}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    axis.set_ylabel("Realized COVE (lower is better)")
    axis.set_title(
        "Which planning horizon wins with forecast errors?", fontweight="bold"
    )
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(
        output_dir / "figure_02_realized_cove_by_horizon.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(9, 5), dpi=220)
    bars = axis.bar(
        labels, forecast["revenue_metric"] / 1_000_000, color=colors
    )
    for bar, value in zip(bars, forecast["revenue_metric"] / 1_000_000):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value,
            f"{value:.2f}M",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    axis.set_ylabel("Realized price-weighted energy value (millions)")
    axis.set_title("Realized value using causal forecasts", fontweight="bold")
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(
        output_dir / "figure_03_realized_value_by_horizon.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), dpi=220)
    for axis, variable, ylabel in (
        (axes[0], "generation_mw", "Generation RMSE (MW)"),
        (axes[1], "price_normalized", "Normalized price RMSE"),
    ):
        selected = metrics[metrics["variable"] == variable]
        axis.plot(
            selected["lead_hours"],
            selected["rmse"],
            marker="o",
            linewidth=2.5,
            color="#2563EB",
        )
        axis.set_ylabel(ylabel)
        axis.set_xlabel("Forecast lead")
        style_axis(axis)
    fig.suptitle(
        "Wind uncertainty grows; electricity-price spikes remain difficult",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(
        output_dir / "figure_04_forecast_error_by_lead.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

    start = pd.Timestamp("2020-01-06")
    end = start + pd.Timedelta(days=7)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), dpi=220, sharex=True)
    for color, horizon in zip(colors, HORIZONS):
        selected = labels_by_horizon[horizon]
        selected = selected[
            (pd.to_datetime(selected["datetime"]) >= start)
            & (pd.to_datetime(selected["datetime"]) < end)
        ]
        if selected.empty:
            continue
        axes[0].plot(
            pd.to_datetime(selected["datetime"]),
            selected["soc_start"],
            label=f"{horizon} h",
            color=color,
            linewidth=1.6,
        )
        net = selected["realized_discharge"] - selected["realized_charge"]
        axes[1].plot(
            pd.to_datetime(selected["datetime"]),
            net,
            label=f"{horizon} h",
            color=color,
            linewidth=1.2,
        )
    axes[0].set_ylabel("SoC (MWh)")
    axes[0].set_title(
        "Example week with forecasts: chronological battery state",
        fontweight="bold",
    )
    axes[1].set_ylabel("Net storage power (MW)")
    axes[1].axhline(0, color="#64748B", linewidth=0.8)
    axes[1].legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    for axis in axes:
        style_axis(axis)
    fig.autofmt_xdate(rotation=20)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(
        output_dir / "figure_05_forecast_example_week.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Causal forecast rolling-horizon dispatch backtest."
    )
    parser.add_argument(
        "--data",
        default=str(
            REPO_ROOT
            / "data"
            / "processed"
            / "dataset_1980-2023_withloads_fix.csv"
        ),
    )
    parser.add_argument(
        "--config",
        default=str(
            REPO_ROOT
            / "strategy_model"
            / "test"
            / "run_016"
            / "config_run_016.yaml"
        ),
    )
    parser.add_argument("--train-end", default="2014-01-01")
    parser.add_argument("--test-end", default=None)
    parser.add_argument("--alpha", type=float, default=10.0)
    parser.add_argument("--train-origin-stride", type=int, default=24)
    parser.add_argument("--mip-gap", type=float, default=0.0)
    parser.add_argument("--initial-soc", type=float, default=1440.0)
    parser.add_argument("--min-soc-frac", type=float, default=0.2)
    parser.add_argument("--max-soc-frac", type=float, default=1.0)
    parser.add_argument("--skip-oracle", action="store_true")
    parser.add_argument(
        "--out-dir",
        default=str(
            REPO_ROOT
            / "strategy_model"
            / "optimization"
            / "rolling_horizon_gurobi_results"
            / "forecast_backtest_2014_2023"
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.data, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    if args.test_end is not None:
        df = df[df["datetime"] < pd.Timestamp(args.test_end)].reset_index(
            drop=True
        )
    config = util.load_config(args.config)
    config.update(
        {
            "storage_type": "caes",
            "storage_rating": 100,
            "storage_duration": 24,
            "num_modules": 1,
            "rated_capacity": 249,
        }
    )

    capped_price = np.minimum(
        df["lmp"].to_numpy(dtype=float), float(config["price_threshold"])
    )
    train_end = int(
        np.searchsorted(
            df["datetime"].to_numpy(), np.datetime64(args.train_end)
        )
    )
    training_price_mean = float(capped_price[:train_end].mean())
    df["price_normalized"] = capped_price / training_price_mean
    generation = df["power_generated"].to_numpy(dtype=float)
    normalized_price = df["price_normalized"].to_numpy(dtype=float)
    max_horizon = max(HORIZONS)

    if train_end <= max(PAST_LAGS) + max_horizon:
        raise ValueError("Training period is too short.")
    origins = np.arange(train_end, len(df), 24)
    origins = origins[origins + max_horizon <= len(df)]

    print(
        f"Training forecasts on {df['datetime'].iloc[0]} through "
        f"{df['datetime'].iloc[train_end - 1]}",
        flush=True,
    )
    print(
        f"Backtesting {len(origins)} daily origins from "
        f"{df['datetime'].iloc[origins[0]]} through "
        f"{df['datetime'].iloc[origins[-1] + max_horizon - 1]}",
        flush=True,
    )

    generation_models = fit_direct_models(
        generation,
        df["datetime"],
        train_end,
        max_horizon,
        0.0,
        float(config["rated_capacity"]),
        args.alpha,
        args.train_origin_stride,
    )
    price_models = fit_direct_models(
        normalized_price,
        df["datetime"],
        train_end,
        max_horizon,
        -2.0,
        float(config["price_threshold"]) / training_price_mean,
        args.alpha,
        args.train_origin_stride,
    )
    generation_forecasts = make_forecast_matrix(
        generation, df["datetime"], origins, generation_models
    )
    price_forecasts = make_forecast_matrix(
        normalized_price, df["datetime"], origins, price_models
    )
    np.savez_compressed(
        output_dir / "forecast_matrices.npz",
        origins=origins,
        generation_forecast=generation_forecasts,
        price_forecast=price_forecasts,
    )

    metrics = pd.concat(
        [
            forecast_metrics(
                generation, origins, generation_forecasts, "generation_mw"
            ),
            forecast_metrics(
                normalized_price,
                origins,
                price_forecasts,
                "price_normalized",
            ),
        ],
        ignore_index=True,
    )
    metrics.to_csv(output_dir / "forecast_accuracy_by_lead.csv", index=False)

    summaries = []
    labels_by_horizon: dict[int, pd.DataFrame] = {}
    for horizon in HORIZONS:
        labels, summary = run_horizon(
            df,
            train_end,
            origins,
            generation_forecasts,
            price_forecasts,
            horizon,
            config,
            args.initial_soc,
            args.min_soc_frac,
            args.max_soc_frac,
            args.mip_gap,
            perfect_information=False,
        )
        labels.to_csv(
            output_dir / f"forecast_dispatch_{horizon}h.csv", index=False
        )
        labels_by_horizon[horizon] = labels
        summaries.append(summary)

    if not args.skip_oracle:
        for horizon in HORIZONS:
            labels, summary = run_horizon(
                df,
                train_end,
                origins,
                generation_forecasts,
                price_forecasts,
                horizon,
                config,
                args.initial_soc,
                args.min_soc_frac,
                args.max_soc_frac,
                args.mip_gap,
                perfect_information=True,
            )
            labels.to_csv(
                output_dir / f"oracle_dispatch_{horizon}h.csv", index=False
            )
            summaries.append(summary)

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "forecast_dispatch_summary.csv", index=False)
    save_figures(summary_df, metrics, labels_by_horizon, output_dir)

    maximum_violation = max(
        float(summary_df[column].max())
        for column in summary_df.columns
        if column.startswith("max_") and column.endswith("_violation")
    )
    report = {
        "training_period": [
            str(df["datetime"].iloc[0]),
            str(df["datetime"].iloc[train_end - 1]),
        ],
        "backtest_period": [
            str(df["datetime"].iloc[origins[0]]),
            str(df["datetime"].iloc[origins[-1] + max_horizon - 1]),
        ],
        "storage": {
            "type": "caes",
            "rating_mw": 100,
            "duration_hours": 24,
            "capacity_mwh": 2400,
            "rte": util.get_rte("caes", 100, 24),
            "min_soc_mwh": 480,
            "max_soc_mwh": 2400,
            "initial_soc_mwh": args.initial_soc,
            "grid_limit_mw": 249,
        },
        "maximum_constraint_violation": maximum_violation,
        "best_forecast_horizon": int(
            summary_df[summary_df["method"] == "causal_forecast"]
            .sort_values("cove")
            .iloc[0]["horizon_hours"]
        ),
    }
    (output_dir / "experiment_metadata.json").write_text(
        json.dumps(report, indent=2)
    )

    print("\nForecast accuracy by lead")
    print(metrics.to_string(index=False))
    print("\nDispatch summary")
    print(
        summary_df[
            [
                "method",
                "horizon_hours",
                "cove",
                "improvement_vs_baseload_pct",
                "revenue_metric",
                "final_soc",
                "solver_runtime_seconds",
            ]
        ].to_string(index=False)
    )
    print(f"\nMaximum realized constraint violation: {maximum_violation:.3e}")
    print(f"Results saved to {output_dir}")


if __name__ == "__main__":
    main()
