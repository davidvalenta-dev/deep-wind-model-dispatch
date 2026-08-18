"""Backtest rolling-horizon Gurobi dispatch with causal forecasts.

The forecasting models are trained on an early chronological period and frozen.
During the later backtest, each forecast uses only values observed before that
forecast was issued. Gurobi plans from forecast wind generation and price, but
only the configured execution block is scored against actual outcomes before
the controller replans. The frozen Summer 2026 ladder executes one hour and
replans every hour.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

os.environ["LC_ALL"] = "C"

REPO_ROOT = Path(__file__).resolve().parents[3]
SUMMER_STEP_DIR = Path(__file__).resolve().parents[1]
LOCAL_CODE_DIR = Path(__file__).resolve().parent
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
OPTIMIZATION_DIR = REPO_ROOT / "strategy_model" / "optimization"
for module_path in (OPTIMIZATION_DIR, STRATEGY_SRC, LOCAL_CODE_DIR):
    module_path_text = str(module_path)
    while module_path_text in sys.path:
        sys.path.remove(module_path_text)
    sys.path.insert(0, module_path_text)

import util  # noqa: E402
from rolling_horizon_gurobi_dispatch import (  # noqa: E402
    continuous_baseload,
    cove_value,
    fixed_costs,
    solve_window,
)


PAST_LAGS = (1, 2, 3, 6, 12, 24, 48, 168)
DEFAULT_HORIZONS = (24, 48, 168)


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
    known_future_values: np.ndarray | None = None,
) -> list[DirectForecastModel]:
    origins = np.arange(max(PAST_LAGS), train_end - max_horizon, origin_stride)
    base = origin_features(values, origins)
    models: list[DirectForecastModel] = []

    for lead in range(1, max_horizon + 1):
        target_indices = origins + lead - 1
        lead_fraction = np.full((len(origins), 1), lead / max_horizon)
        feature_blocks = [base, calendar_features(datetimes.iloc[target_indices]), lead_fraction]
        valid = np.ones(len(origins), dtype=bool)
        if known_future_values is not None:
            known = known_future_values[target_indices]
            valid &= ~np.isnan(known)
            feature_blocks.append(known.reshape(-1, 1))
        X = np.column_stack(
            feature_blocks
        )
        y = values[target_indices]
        X = X[valid]
        y = y[valid]
        if len(y) == 0:
            raise ValueError("No valid training samples for the requested known-future feature.")
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
    known_future_values: np.ndarray | None = None,
) -> np.ndarray:
    max_horizon = len(models)
    forecasts = np.empty((len(origins), max_horizon), dtype=float)
    for row_index, origin in enumerate(origins):
        base = single_origin_features(values, int(origin))
        target_indices = np.minimum(
            np.arange(origin, origin + max_horizon), len(values) - 1
        )
        target_times = datetimes.iloc[target_indices]
        calendar = calendar_features(target_times)
        for lead_index, model in enumerate(models):
            features = np.concatenate(
                [base, calendar[lead_index], [(lead_index + 1) / max_horizon]]
            )
            if known_future_values is not None:
                features = np.concatenate(
                    [features, [known_future_values[target_indices[lead_index]]]]
                )
            forecasts[row_index, lead_index] = model.predict(features)
    return forecasts


def make_known_future_matrix(
    values: np.ndarray,
    origins: np.ndarray,
    max_horizon: int,
) -> np.ndarray:
    forecasts = np.empty((len(origins), max_horizon), dtype=float)
    for row_index, origin in enumerate(origins):
        target_indices = np.minimum(
            np.arange(origin, origin + max_horizon), len(values) - 1
        )
        forecasts[row_index, :] = values[target_indices]
    return forecasts


def forecast_metrics(
    actual: np.ndarray,
    origins: np.ndarray,
    forecasts: np.ndarray,
    name: str,
) -> pd.DataFrame:
    rows = []
    buckets = ((1, 24), (25, 48), (49, 72), (73, 168))
    max_lead = forecasts.shape[1]
    for start_lead, end_lead in buckets:
        if start_lead > max_lead:
            continue
        end_lead = min(end_lead, max_lead)
        lead_indices = np.arange(start_lead - 1, end_lead)
        predicted_blocks = []
        observed_blocks = []
        for row_index, origin in enumerate(origins):
            valid_leads = lead_indices[origin + lead_indices < len(actual)]
            if len(valid_leads) == 0:
                continue
            predicted_blocks.append(forecasts[row_index, valid_leads])
            observed_blocks.append(actual[origin + valid_leads])
        if not predicted_blocks:
            continue
        predicted = np.concatenate(predicted_blocks)
        observed = np.concatenate(observed_blocks)
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
    timestamps = pd.to_datetime(labels["datetime"])
    chronological_error_count = 0
    if len(timestamps) > 1:
        hour_steps = timestamps.diff().dropna().dt.total_seconds().to_numpy() / 3600.0
        chronological_error_count = int(np.sum(np.abs(hour_steps - 1.0) > 1e-9))
    hourly_revenue = labels["hourly_revenue_USD"].to_numpy()
    raw_price = labels["actual_RTM_USD_per_MWh"].to_numpy()
    return {
        "chronological_hour_step_error_count": chronological_error_count,
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
        "curtailment_negative_count": int(np.sum(labels["realized_curtailment"].to_numpy() < -1e-9)),
        "hourly_revenue_sum_error_usd": float(
            abs(hourly_revenue.sum() - np.sum(delivered * raw_price))
        ),
    }


def year_end_soc_targets(
    timestamps: pd.Series,
    origin: int,
    available_horizon: int,
    annual_target_soc_mwh: float | None,
) -> dict[int, float]:
    """Return SoC-index targets for Dec. 31 23:00 hours inside a window."""
    if annual_target_soc_mwh is None:
        return {}
    targets: dict[int, float] = {}
    window_times = pd.to_datetime(timestamps.iloc[origin : origin + available_horizon])
    for offset, stamp in enumerate(window_times):
        if stamp.month == 12 and stamp.day == 31 and stamp.hour == 23:
            targets[offset + 1] = float(annual_target_soc_mwh)
    return targets


def annual_soc_qa(labels: pd.DataFrame, annual_target_soc_mwh: float | None) -> dict[str, float | int]:
    if annual_target_soc_mwh is None or labels.empty:
        return {
            "annual_soc_target_mwh": math.nan,
            "annual_soc_target_violation_count": 0,
            "annual_soc_target_max_abs_error": 0.0,
        }
    timestamps = pd.to_datetime(labels["datetime"])
    mask = (timestamps.dt.month == 12) & (timestamps.dt.day == 31) & (timestamps.dt.hour == 23)
    if not mask.any():
        return {
            "annual_soc_target_mwh": float(annual_target_soc_mwh),
            "annual_soc_target_violation_count": 0,
            "annual_soc_target_max_abs_error": 0.0,
        }
    errors = np.abs(labels.loc[mask, "soc_end"].to_numpy(dtype=float) - float(annual_target_soc_mwh))
    return {
        "annual_soc_target_mwh": float(annual_target_soc_mwh),
        "annual_soc_target_violation_count": int(np.sum(errors > 1e-5)),
        "annual_soc_target_max_abs_error": float(errors.max()),
    }


def wind_only_delivery(power: np.ndarray, config: dict) -> np.ndarray:
    """No-storage baseline: deliver actual wind directly up to grid capacity."""
    return np.minimum(np.maximum(power, 0.0), float(config["rated_capacity"]))


def constant_output_100mw_delivery(
    power: np.ndarray,
    config: dict,
    initial_soc: float,
    min_soc_frac: float,
    max_soc_frac: float,
    target_mw: float = 100.0,
) -> np.ndarray:
    """Chris's 100-MW rule-based wind-storage benchmark."""
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(
        config["storage_rating"] * config["storage_duration"] * config["num_modules"]
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
    soc = float(np.clip(initial_soc, min_soc, max_soc))
    delivered = np.zeros(len(power), dtype=float)

    for idx, generation_value in enumerate(power):
        generation = max(0.0, float(generation_value))
        if generation >= target_mw:
            direct = min(target_mw, grid_cap)
            room = max(0.0, max_soc - soc)
            charge = min(generation - direct, rating, room)
            delivered[idx] = direct
            soc += charge
        else:
            direct = min(generation, grid_cap)
            needed = max(0.0, target_mw - direct)
            discharge = min(
                needed,
                rating,
                max(0.0, (soc - min_soc) * rte),
                max(0.0, grid_cap - direct),
            )
            delivered[idx] = direct + discharge
            soc -= discharge / rte
    return delivered


def cost_over_revenue(cost: float, revenue: float) -> float:
    if revenue <= 0:
        return math.inf
    return float(cost / revenue)


def apply_direct_reserve(
    solution: dict,
    config: dict,
    direct_reserve_mw: float,
) -> dict:
    """Reserve direct-export headroom for causal forecast errors.

    The corrected realized-execution rule keeps the planned direct-wind
    allocation fixed. When the wind forecast is low, this can curtail actual
    wind even if the grid has room. The reserve keeps the optimized storage
    action but raises the planned direct-wind allocation by a chosen MW buffer.
    Realized execution still enforces wind availability and the grid cap.
    """
    if direct_reserve_mw <= 0:
        return solution

    reserved = dict(solution)
    grid_cap = float(config["rated_capacity"])
    direct = np.asarray(solution["direct"], dtype=float).copy()
    discharge = np.asarray(solution["discharge"], dtype=float)
    reserved["direct"] = np.minimum(
        np.maximum(0.0, grid_cap - discharge),
        direct + float(direct_reserve_mw),
    )
    return reserved


def run_horizon(
    df: pd.DataFrame,
    test_start: int,
    origins: np.ndarray,
    generation_forecasts: np.ndarray,
    price_forecasts: np.ndarray,
    horizon: int,
    config: dict,
    primary_baseline_config: dict,
    initial_soc: float,
    primary_baseline_initial_soc: float,
    min_soc_frac: float,
    max_soc_frac: float,
    mip_gap: float,
    perfect_information: bool,
    direct_reserve_mw: float,
    execution_step_hours: int,
    replanning_interval_hours: int,
    terminal_policy: str,
    annual_target_soc_mwh: float | None,
) -> tuple[pd.DataFrame, dict]:
    actual_generation = df["power_generated"].to_numpy(dtype=float)
    actual_price = df["price_normalized"].to_numpy(dtype=float)
    raw_price = df["raw_RTM_USD_per_MWh"].to_numpy(dtype=float)
    current_soc = initial_soc
    rows = []
    solver_runtime = 0.0
    started = time.perf_counter()

    for origin_row, origin in enumerate(origins):
        available_horizon = min(horizon, len(df) - origin)
        execute_len = min(execution_step_hours, available_horizon, len(df) - origin)
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

        soc_targets = (
            year_end_soc_targets(
                df["datetime"],
                int(origin),
                available_horizon,
                annual_target_soc_mwh,
            )
            if perfect_information
            else {}
        )
        solution = solve_window(
            planned_generation,
            planned_price,
            config,
            current_soc,
            terminal_policy,
            min_soc_frac,
            max_soc_frac,
            mip_gap,
            None,
            soc_targets=soc_targets,
        )
        solver_runtime += float(solution["runtime"])
        execution_plan = apply_direct_reserve(
            solution,
            config,
            0.0 if perfect_information else direct_reserve_mw,
        )
        realized = execute_plan_against_actual(
            execution_plan,
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
                    "timestamp_UTC": pd.Timestamp(df["datetime"].iloc[hour]).strftime("%Y-%m-%d %H:%M:%S"),
                    "horizon_hours": horizon,
                    "planning_horizon_hours": horizon,
                    "execution_step_hours": execution_step_hours,
                    "replanning_interval_hours": replanning_interval_hours,
                    "perfect_information": perfect_information,
                    "actual_generation": actual_generation[hour],
                    "actual_wind_MW": actual_generation[hour],
                    "forecast_generation": planned_generation[k],
                    "actual_price": actual_price[hour],
                    "actual_RTM_USD_per_MWh": raw_price[hour],
                    "forecast_price": planned_price[k],
                    "target_output_MW": np.nan,
                    "optimized_direct": float(solution["direct"][k]),
                    "planned_direct": float(execution_plan["direct"][k]),
                    "planned_charge": float(solution["charge"][k]),
                    "planned_discharge": float(solution["discharge"][k]),
                    "realized_direct": realized["direct"][k],
                    "direct_wind_MW": realized["direct"][k],
                    "realized_charge": realized["charge"][k],
                    "charge_MW": realized["charge"][k],
                    "realized_discharge": realized["discharge"][k],
                    "discharge_MW": realized["discharge"][k],
                    "realized_delivered": realized["delivered"][k],
                    "delivered_power_MW": realized["delivered"][k],
                    "realized_curtailment": realized["curtailment"][k],
                    "curtailment_MW": realized["curtailment"][k],
                    "output_shortfall_MW": np.nan,
                    "soc_start": realized["storage"][k],
                    "SOC_start_MWh": realized["storage"][k],
                    "soc_end": realized["storage"][k + 1],
                    "SOC_end_MWh": realized["storage"][k + 1],
                    "mode_binary_charge": realized["mode"][k],
                    "hourly_revenue_USD": realized["delivered"][k] * raw_price[hour],
                    "hourly_revenue_metric": realized["delivered"][k] * actual_price[hour],
                    "year_end_soc_target_active_in_plan": bool(soc_targets),
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
    raw_price_for_labels = labels["actual_RTM_USD_per_MWh"].to_numpy(dtype=float)
    delivered = labels["realized_delivered"].to_numpy()
    wind_only = wind_only_delivery(power, config)
    constant_100mw = constant_output_100mw_delivery(
        power,
        config,
        initial_soc=initial_soc,
        min_soc_frac=min_soc_frac,
        max_soc_frac=max_soc_frac,
        target_mw=100.0,
    )
    legacy_non_strategic = continuous_baseload(
        power,
        primary_baseline_config,
        initial_soc=primary_baseline_initial_soc,
    )
    wind_cost, dispatch_cost = fixed_costs(config)
    revenue = float(np.sum(delivered * price))
    wind_only_revenue = float(np.sum(wind_only * price))
    constant_100mw_revenue = float(np.sum(constant_100mw * price))
    legacy_revenue = float(np.sum(legacy_non_strategic * price))
    raw_revenue = float(np.sum(delivered * raw_price_for_labels))
    wind_only_raw_revenue = float(np.sum(wind_only * raw_price_for_labels))
    constant_100mw_raw_revenue = float(np.sum(constant_100mw * raw_price_for_labels))
    legacy_raw_revenue = float(np.sum(legacy_non_strategic * raw_price_for_labels))
    cove = cost_over_revenue(dispatch_cost, revenue)
    wind_only_cove = cost_over_revenue(wind_cost, wind_only_revenue)
    constant_100mw_cove = cost_over_revenue(dispatch_cost, constant_100mw_revenue)
    legacy_cove = cove_value(legacy_non_strategic, price, primary_baseline_config)
    raw_cove = cost_over_revenue(dispatch_cost, raw_revenue)
    wind_only_raw_cove = cost_over_revenue(wind_cost, wind_only_raw_revenue)
    constant_100mw_raw_cove = cost_over_revenue(dispatch_cost, constant_100mw_raw_revenue)
    constraints = check_realized_constraints(
        labels, config, min_soc_frac, max_soc_frac
    )
    annual_checks = annual_soc_qa(
        labels,
        annual_target_soc_mwh if perfect_information else None,
    )
    summary = {
        "method": "oracle"
        if perfect_information
        else (
            "causal_forecast_direct_reserve"
            if direct_reserve_mw > 0
            else "causal_forecast"
        ),
        "horizon_hours": horizon,
        "direct_reserve_mw": 0.0
        if perfect_information
        else float(direct_reserve_mw),
        "hours": len(labels),
        "test_start": str(labels["datetime"].iloc[0]),
        "test_end": str(labels["datetime"].iloc[-1]),
        "revenue_metric": revenue,
        "baseload_revenue_metric": wind_only_revenue,
        "wind_only_revenue_metric": wind_only_revenue,
        "constant_output_100mw_revenue_metric": constant_100mw_revenue,
        "legacy_non_strategic_revenue_metric": legacy_revenue,
        "raw_realized_revenue_usd": raw_revenue,
        "baseload_raw_realized_revenue_usd": wind_only_raw_revenue,
        "wind_only_raw_realized_revenue_usd": wind_only_raw_revenue,
        "constant_output_100mw_raw_realized_revenue_usd": constant_100mw_raw_revenue,
        "legacy_non_strategic_raw_realized_revenue_usd": legacy_raw_revenue,
        "cove": cove,
        "baseload_cove": wind_only_cove,
        "wind_only_cove": wind_only_cove,
        "constant_output_100mw_cove": constant_100mw_cove,
        "legacy_non_strategic_cove": legacy_cove,
        "raw_cove": raw_cove,
        "wind_only_raw_cove": wind_only_raw_cove,
        "constant_output_100mw_raw_cove": constant_100mw_raw_cove,
        "improvement_vs_baseload_pct": (wind_only_cove - cove) / wind_only_cove * 100,
        "cove_improvement_vs_wind_only_pct": (wind_only_cove - cove) / wind_only_cove * 100,
        "cove_improvement_vs_100mw_baseload_pct": (constant_100mw_cove - cove)
        / constant_100mw_cove
        * 100,
        "cove_improvement_vs_legacy_non_strategic_pct": (legacy_cove - cove)
        / legacy_cove
        * 100,
        "raw_revenue_gain_vs_wind_only_pct": (raw_revenue / wind_only_raw_revenue - 1.0) * 100,
        "raw_revenue_gain_vs_100mw_baseload_pct": (raw_revenue / constant_100mw_raw_revenue - 1.0) * 100,
        "dispatch_cost": dispatch_cost,
        "wind_only_cost": wind_cost,
        "profit_metric": revenue - dispatch_cost,
        "primary_baseline_storage_duration_h": float(
            primary_baseline_config["storage_duration"]
        ),
        "final_soc": float(labels["soc_end"].iloc[-1]),
        "execution_step_hours": int(execution_step_hours),
        "replanning_interval_hours": int(replanning_interval_hours),
        "terminal_policy": terminal_policy,
        "solver_runtime_seconds": solver_runtime,
        **constraints,
        **annual_checks,
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
    horizons: list[int],
):
    if not labels_by_horizon:
        return
    colors = ["#2563EB", "#0F766E", "#B45309", "#7C3AED"]
    plot_colors = colors * 10
    forecast = summary[
        summary["method"].str.startswith("causal_forecast")
    ].sort_values(
        "horizon_hours"
    )
    oracle = summary[summary["method"] == "oracle"].sort_values("horizon_hours")
    labels = [f"{int(value)} h" for value in forecast["horizon_hours"]]
    x = np.arange(len(labels))

    fig, axis = plt.subplots(figsize=(9, 5), dpi=220)
    width = 0.36
    axis.bar(
        x - width / 2,
        forecast["cove_improvement_vs_100mw_baseload_pct"],
        width,
        label="Causal forecasts",
        color="#2563EB",
    )
    if not oracle.empty:
        axis.bar(
            x + width / 2,
            oracle["cove_improvement_vs_100mw_baseload_pct"],
            width,
            label="Perfect information information",
            color="#CBD5E1",
        )
    axis.set_xticks(x, labels)
    axis.set_ylabel("COVE reduction vs 100 MW benchmark (%)")
    axis.set_title(
        "Realistic forecast dispatch versus perfect-information reference",
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
    bars = axis.bar(labels, forecast["cove"], color=plot_colors[: len(labels)])
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
        labels, forecast["revenue_metric"] / 1_000_000, color=plot_colors[: len(labels)]
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
    for color, horizon in zip(plot_colors, horizons):
        if horizon not in labels_by_horizon:
            continue
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
    parser.add_argument(
        "--price-signal",
        choices=("ridge_rtm",),
        default="ridge_rtm",
        help="Official Summer 2026 REU ladder price forecast: causal ridge RTM.",
    )
    parser.add_argument("--mip-gap", type=float, default=0.0)
    parser.add_argument("--storage-power-mw", type=float, default=100.0)
    parser.add_argument("--storage-duration-h", type=float, default=10.0)
    parser.add_argument(
        "--execution-step-hours",
        type=int,
        default=1,
        help="How many hours are actually executed before replanning. Chris spec: 1.",
    )
    parser.add_argument(
        "--replanning-interval-hours",
        type=int,
        default=1,
        help="How many hours the controller advances between solves. Chris spec: 1.",
    )
    parser.add_argument(
        "--annual-target-soc-mwh",
        type=float,
        default=None,
        help="Optional oracle SoC target after each Dec. 31 23:00 hour. Omit for fully chronological carryover.",
    )
    parser.add_argument(
        "--terminal-policy",
        choices=["equal-initial", "no-empty", "none"],
        default="equal-initial",
        help="SoC condition at the end of each planning window.",
    )
    parser.add_argument(
        "--primary-baseline-storage-duration-h",
        type=float,
        default=24.0,
        help=(
            "Storage duration used only for the legacy non-strategic "
            "storage-baseload column. The main comparison is wind-only "
            "no-storage; the 100 MW / 10 h benchmark is reported separately."
        ),
    )
    parser.add_argument("--grid-cap-mw", type=float, default=249.0)
    parser.add_argument(
        "--initial-soc",
        type=float,
        default=None,
        help="Initial SoC in MWh. If omitted, uses the midpoint of min/max SoC.",
    )
    parser.add_argument("--min-soc-frac", type=float, default=0.2)
    parser.add_argument("--max-soc-frac", type=float, default=1.0)
    parser.add_argument(
        "--direct-reserve-mw",
        type=float,
        default=0.0,
        help=(
            "Extra planned direct-wind export headroom for causal forecast "
            "execution. This keeps storage actions optimized but reduces "
            "curtailment from wind forecast underprediction."
        ),
    )
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=list(DEFAULT_HORIZONS),
        help="Planning horizons to test. Example: --horizons 24 48 72 168 248",
    )
    parser.add_argument(
        "--oracle-only",
        action="store_true",
        help="Skip causal forecast rows and write only perfect-information oracle hourly CSVs.",
    )
    parser.add_argument("--skip-oracle", action="store_true")
    parser.add_argument(
        "--out-dir",
        default=str(
            SUMMER_STEP_DIR
            / "results"
            / "full_rebuild_forecast_backtest_2014_2023"
        ),
    )
    args = parser.parse_args()
    if args.oracle_only and args.skip_oracle:
        raise ValueError("--oracle-only and --skip-oracle cannot both be used.")
    if args.execution_step_hours < 1 or args.replanning_interval_hours < 1:
        raise ValueError("Execution step and replanning interval must be at least one hour.")

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
            "storage_rating": args.storage_power_mw,
            "storage_duration": args.storage_duration_h,
            "num_modules": 1,
            "rated_capacity": args.grid_cap_mw,
        }
    )
    primary_baseline_config = dict(config)
    primary_baseline_config["storage_duration"] = args.primary_baseline_storage_duration_h
    storage_capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    initial_soc = (
        float(args.initial_soc)
        if args.initial_soc is not None
        else storage_capacity * (args.min_soc_frac + args.max_soc_frac) / 2.0
    )
    primary_baseline_capacity = float(
        primary_baseline_config["storage_rating"]
        * primary_baseline_config["storage_duration"]
        * primary_baseline_config["num_modules"]
    )
    primary_baseline_initial_soc = primary_baseline_capacity * (
        args.min_soc_frac + args.max_soc_frac
    ) / 2.0

    if "lmp" in df.columns:
        raw_rtm_price = df["lmp"].to_numpy(dtype=float)
    elif "rtm_lmp_pyron_usd_per_mwh" in df.columns:
        raw_rtm_price = df["rtm_lmp_pyron_usd_per_mwh"].to_numpy(dtype=float)
    else:
        raise ValueError("Input data must contain either 'lmp' or 'rtm_lmp_pyron_usd_per_mwh'.")
    df["raw_RTM_USD_per_MWh"] = raw_rtm_price

    capped_price = np.minimum(raw_rtm_price, float(config["price_threshold"]))
    train_end = int(
        np.searchsorted(
            df["datetime"].to_numpy(), np.datetime64(args.train_end)
        )
    )
    training_price_mean = float(capped_price[:train_end].mean())
    df["price_normalized"] = capped_price / training_price_mean
    generation = df["power_generated"].to_numpy(dtype=float)
    normalized_price = df["price_normalized"].to_numpy(dtype=float)
    horizons = sorted(dict.fromkeys(int(h) for h in args.horizons))
    max_horizon = max(horizons)

    if train_end <= max(PAST_LAGS) + max_horizon:
        raise ValueError("Training period is too short.")
    origins = np.arange(train_end, len(df), args.replanning_interval_hours)
    # Keep every tested horizon on the same evaluation hours. Without this,
    # the final partial week changes the horizon ranking.
    origins = origins[origins + max_horizon <= len(df)]
    if len(origins) == 0:
        raise ValueError("No test origins have a complete planning horizon.")

    print(
        f"Training forecasts on {df['datetime'].iloc[0]} through "
        f"{df['datetime'].iloc[train_end - 1]}",
        flush=True,
    )
    print(
        f"Backtesting {len(origins)} hourly rolling origins from "
        f"{df['datetime'].iloc[origins[0]]} through "
        f"{df['datetime'].iloc[origins[-1]]}",
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
    generation_forecasts = make_forecast_matrix(
        generation, df["datetime"], origins, generation_models
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
    price_forecasts = make_forecast_matrix(
        normalized_price,
        df["datetime"],
        origins,
        price_models,
    )
    np.savez_compressed(
        output_dir / "forecast_matrices.npz",
        origins=origins,
        generation_forecast=generation_forecasts,
        price_forecast=price_forecasts,
        price_signal=args.price_signal,
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
    if not args.oracle_only:
        for horizon in horizons:
            labels, summary = run_horizon(
                df,
                train_end,
                origins,
                generation_forecasts,
                price_forecasts,
                horizon,
                config,
                primary_baseline_config,
                initial_soc,
                primary_baseline_initial_soc,
                args.min_soc_frac,
                args.max_soc_frac,
                args.mip_gap,
                perfect_information=False,
                direct_reserve_mw=args.direct_reserve_mw,
                execution_step_hours=args.execution_step_hours,
                replanning_interval_hours=args.replanning_interval_hours,
                terminal_policy=args.terminal_policy,
                annual_target_soc_mwh=args.annual_target_soc_mwh,
            )
            labels.to_csv(
                output_dir / f"forecast_dispatch_{horizon}h.csv", index=False
            )
            labels_by_horizon[horizon] = labels
            summaries.append(summary)

    if not args.skip_oracle:
        for horizon in horizons:
            labels, summary = run_horizon(
                df,
                train_end,
                origins,
                generation_forecasts,
                price_forecasts,
                horizon,
                config,
                primary_baseline_config,
                initial_soc,
                primary_baseline_initial_soc,
                args.min_soc_frac,
                args.max_soc_frac,
                args.mip_gap,
                perfect_information=True,
                direct_reserve_mw=0.0,
                execution_step_hours=args.execution_step_hours,
                replanning_interval_hours=args.replanning_interval_hours,
                terminal_policy=args.terminal_policy,
                annual_target_soc_mwh=args.annual_target_soc_mwh,
            )
            labels.to_csv(
                output_dir / f"oracle_dispatch_{horizon}h.csv", index=False
            )
            summaries.append(summary)

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "forecast_dispatch_summary.csv", index=False)
    save_figures(summary_df, metrics, labels_by_horizon, output_dir, horizons)

    maximum_violation = max(
        float(summary_df[column].max())
        for column in summary_df.columns
        if column.startswith("max_") and column.endswith("_violation")
    )
    causal_rows = summary_df[summary_df["method"].str.startswith("causal_forecast")]
    report = {
        "training_period": [
            str(df["datetime"].iloc[0]),
            str(df["datetime"].iloc[train_end - 1]),
        ],
        "backtest_period": [
            str(df["datetime"].iloc[origins[0]]),
            str(df["datetime"].iloc[origins[-1]]),
        ],
        "storage": {
            "type": "caes",
            "rating_mw": float(config["storage_rating"]),
            "duration_hours": float(config["storage_duration"]),
            "capacity_mwh": storage_capacity,
            "rte": util.get_rte("caes", config["storage_rating"], config["storage_duration"]),
            "min_soc_mwh": storage_capacity * args.min_soc_frac,
            "max_soc_mwh": storage_capacity * args.max_soc_frac,
            "initial_soc_mwh": initial_soc,
            "grid_limit_mw": float(config["rated_capacity"]),
            "annual_target_soc_mwh_for_oracle": (
                None
                if args.annual_target_soc_mwh is None
                else float(args.annual_target_soc_mwh)
            ),
        },
        "execution_step_hours": int(args.execution_step_hours),
        "replanning_interval_hours": int(args.replanning_interval_hours),
        "ordinary_window_terminal_policy": args.terminal_policy,
        "price_signal_for_planning": args.price_signal,
        "realized_price_for_scoring": "summary keeps normalized revenue_metric for old COVE comparability; hourly CSV also reports raw realized RTM LMP and hourly revenue in USD",
        "maximum_constraint_violation": maximum_violation,
        "tested_horizons": horizons,
        "best_forecast_horizon": (
            int(causal_rows.sort_values("cove").iloc[0]["horizon_hours"])
            if not causal_rows.empty
            else None
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
                "cove_improvement_vs_wind_only_pct",
                "cove_improvement_vs_100mw_baseload_pct",
                "revenue_metric",
                "wind_only_revenue_metric",
                "constant_output_100mw_revenue_metric",
                "final_soc",
                "solver_runtime_seconds",
            ]
        ].to_string(index=False)
    )
    print(f"\nMaximum realized constraint violation: {maximum_violation:.3e}")
    print(f"Results saved to {output_dir}")


if __name__ == "__main__":
    main()
