from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ["LC_ALL"] = "C"

import gurobipy as gp
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from gurobipy import GRB

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR.parents[0] / "results" / "scenario_48h_full_ladder"

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(REPO_ROOT / "strategy_model" / "src"))
import util  # noqa: E402
import run_nora_matching_forecast_horizons as base  # noqa: E402
from run_best_forecast_dispatch_search import (  # noqa: E402
    PRICE_CLIP,
    candidate_summary,
    cove_reduction_from_revenues,
)


HORIZON = 48
CONFIG_PATH = REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"
SCENARIO_SPECS = {
    "three_scenario_expected": {
        "weights": np.array([0.50, 0.25, 0.25], dtype=float),
        "wind_quantiles": [0.50, 0.10, 0.90],
        "price_quantiles": [0.50, 0.90, 0.10],
        "risk_lambda": 0.0,
    },
    "three_scenario_risk25": {
        "weights": np.array([0.50, 0.25, 0.25], dtype=float),
        "wind_quantiles": [0.50, 0.10, 0.90],
        "price_quantiles": [0.50, 0.90, 0.10],
        "risk_lambda": 0.25,
    },
    "five_scenario_expected": {
        "weights": np.array([0.40, 0.15, 0.15, 0.15, 0.15], dtype=float),
        "wind_quantiles": [0.50, 0.10, 0.90, 0.10, 0.90],
        "price_quantiles": [0.50, 0.90, 0.10, 0.10, 0.90],
        "risk_lambda": 0.0,
    },
    "seven_scenario_expected": {
        "weights": np.array([0.28, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12], dtype=float),
        "wind_quantiles": [0.50, 0.10, 0.90, 0.10, 0.90, 0.25, 0.75],
        "price_quantiles": [0.50, 0.90, 0.10, 0.10, 0.90, 0.75, 0.25],
        "risk_lambda": 0.0,
    },
    "ten_scenario_expected": {
        "weights": np.array([0.22, 0.10, 0.10, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.06], dtype=float),
        "wind_quantiles": [0.50, 0.05, 0.95, 0.05, 0.95, 0.25, 0.75, 0.25, 0.75, 0.50],
        "price_quantiles": [0.50, 0.95, 0.05, 0.05, 0.95, 0.75, 0.25, 0.25, 0.75, 0.95],
        "risk_lambda": 0.0,
    },
}


def matrix_from_indices(values: np.ndarray, origins: np.ndarray, indexer) -> np.ndarray:
    forecasts = np.empty((len(origins), HORIZON), dtype=float)
    for row, origin in enumerate(origins):
        for lead in range(HORIZON):
            forecasts[row, lead] = values[indexer(int(origin), lead)]
    return forecasts


def build_forecasts(
    df: pd.DataFrame,
    train_end: int,
    origins: np.ndarray,
    train_origin_stride: int,
    forecast_model_max_horizon: int,
) -> tuple[np.ndarray, np.ndarray, list[base.DirectForecastModel], list[base.DirectForecastModel]]:
    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)

    generation_models = base.fit_direct_models(
        generation,
        df["datetime"],
        train_end,
        forecast_model_max_horizon,
        0.0,
        max(float(generation[:train_end].max()), base.GRID_CAP),
        alpha=10.0,
        origin_stride=train_origin_stride,
    )
    wind_center = base.make_generation_forecasts(generation, df["datetime"], origins, generation_models)[:, :HORIZON]
    price_models = base.fit_direct_models(
        price,
        df["datetime"],
        train_end,
        forecast_model_max_horizon,
        -2.0,
        float(np.nanmax(price[:train_end])),
        alpha=10.0,
        origin_stride=train_origin_stride,
    )
    price_center = base.make_generation_forecasts(price, df["datetime"], origins, price_models)[:, :HORIZON]
    price_center = np.clip(price_center, PRICE_CLIP[0], PRICE_CLIP[1])
    return wind_center, price_center, generation_models, price_models


def conformal_quantile(values: np.ndarray, q: float) -> np.ndarray:
    """Finite-sample split-conformal empirical quantile by forecast lead."""
    sorted_values = np.sort(values, axis=0)
    n = sorted_values.shape[0]
    rank = int(np.ceil((n + 1) * q))
    rank = min(max(rank, 1), n)
    return sorted_values[rank - 1]


def residual_quantiles(
    df: pd.DataFrame,
    residual_start: int,
    residual_end: int,
    generation_models: list[base.DirectForecastModel],
    price_models: list[base.DirectForecastModel],
    quantiles: list[float],
    method: str = "empirical",
    origin_stride: int = 1,
) -> dict[str, dict[float, np.ndarray]]:
    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)
    residual_start = max(residual_start, max(base.PAST_LAGS))
    forecast_model_max_horizon = len(generation_models)
    residual_origins = np.arange(residual_start, residual_end - forecast_model_max_horizon, int(origin_stride))
    residual_wind_forecast = base.make_generation_forecasts(generation, df["datetime"], residual_origins, generation_models)[:, :HORIZON]
    residual_price_forecast = base.make_generation_forecasts(price, df["datetime"], residual_origins, price_models)[:, :HORIZON]

    observed_wind = np.vstack([generation[origin : origin + HORIZON] for origin in residual_origins])
    observed_price = np.vstack([price[origin : origin + HORIZON] for origin in residual_origins])
    wind_errors = observed_wind - residual_wind_forecast
    price_errors = observed_price - residual_price_forecast
    quantile_fn = conformal_quantile if method == "split_conformal" else (lambda values, q: np.quantile(values, q, axis=0))

    return {
        "wind": {q: quantile_fn(wind_errors, q) for q in quantiles},
        "price": {q: quantile_fn(price_errors, q) for q in quantiles},
    }


def scenario_matrices(
    center_wind: np.ndarray,
    center_price: np.ndarray,
    quantile_lookup: dict[str, dict[float, np.ndarray]],
    spec: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    weights = np.asarray(spec["weights"], dtype=float)
    weights = weights / weights.sum()
    wind_scenarios = []
    price_scenarios = []
    for wind_q, price_q in zip(spec["wind_quantiles"], spec["price_quantiles"]):
        wind = center_wind + quantile_lookup["wind"][wind_q]
        price = center_price + quantile_lookup["price"][price_q]
        wind_scenarios.append(np.clip(wind, 0.0, max(base.GRID_CAP, float(center_wind.max()))))
        price_scenarios.append(np.clip(price, PRICE_CLIP[0], PRICE_CLIP[1]))
    price_scenarios = np.asarray(price_scenarios)
    for scenario_index, event in enumerate(spec.get("price_events", [])):
        if not event or "quantile" not in event:
            continue
        start = max(0, min(HORIZON, int(event.get("start", 0))))
        end = max(start, min(HORIZON, int(event.get("end", HORIZON))))
        if end <= start:
            continue
        lift = np.maximum(
            0.0,
            quantile_lookup["price"][float(event["quantile"])][start:end]
            - quantile_lookup["price"][0.50][start:end],
        )
        price_scenarios[scenario_index, start:end] += float(event.get("scale", 1.0)) * lift
    return np.asarray(wind_scenarios), np.clip(price_scenarios, PRICE_CLIP[0], PRICE_CLIP[1]), weights


def solve_scenario_window(
    generation_scenarios: np.ndarray,
    price_scenarios: np.ndarray,
    weights: np.ndarray,
    start_soc: float,
    risk_lambda: float,
    execution_len: int,
) -> dict[str, float]:
    scenario_count, hours = generation_scenarios.shape
    model = gp.Model("uncertainty_aware_dispatch")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = 1e-6
    model.Params.TimeLimit = 2.0

    ch = model.addVars(scenario_count, hours, lb=0.0, ub=base.PS, name="ch")
    dh = model.addVars(scenario_count, hours, lb=0.0, ub=base.PS, name="dh")
    soc = model.addVars(scenario_count, hours + 1, lb=base.CMIN, ub=base.CMAX, name="soc")
    ed = model.addVars(scenario_count, hours, lb=0.0, ub=base.GRID_CAP, name="ed")
    gw = model.addVars(scenario_count, hours, lb=0.0, name="gw")
    mode = model.addVars(scenario_count, hours, vtype=GRB.BINARY, name="mode")

    for s in range(scenario_count):
        model.addConstr(soc[s, 0] == float(np.clip(start_soc, base.CMIN, base.CMAX)))
        model.addConstr(soc[s, hours] == float(np.clip(start_soc, base.CMIN, base.CMAX)))

        for t in range(hours):
            model.addConstr(gw[s, t] <= float(generation_scenarios[s, t]))
            model.addConstr(ch[s, t] <= float(generation_scenarios[s, t]) - gw[s, t])
            model.addConstr(ch[s, t] <= base.PS * mode[s, t])
            model.addConstr(dh[s, t] <= base.PS * (1.0 - mode[s, t]))
            model.addConstr(dh[s, t] <= (soc[s, t] - base.CMIN) * base.RTE)
            model.addConstr(ed[s, t] == gw[s, t] + dh[s, t])
            model.addConstr(soc[s, t + 1] == soc[s, t] + ch[s, t] - dh[s, t] / base.RTE)

    # The executed block must be the same across futures; future actions are
    # recourse variables because the controller replans after the executed day.
    for s in range(1, scenario_count):
        for t in range(execution_len):
            model.addConstr(ch[s, t] == ch[0, t])
            model.addConstr(dh[s, t] == dh[0, t])
            model.addConstr(gw[s, t] == gw[0, t])
            model.addConstr(mode[s, t] == mode[0, t])

    scenario_values = [
        gp.quicksum(float(price_scenarios[s, t]) * ed[s, t] for t in range(hours))
        for s in range(scenario_count)
    ]
    expected_value = gp.quicksum(float(weights[s]) * scenario_values[s] for s in range(scenario_count))

    if risk_lambda > 0:
        worst_value = model.addVar(lb=-GRB.INFINITY, name="worst_scenario_value")
        for s in range(scenario_count):
            model.addConstr(worst_value <= scenario_values[s])
        model.setObjective((1.0 - risk_lambda) * expected_value + risk_lambda * worst_value, GRB.MAXIMIZE)
    else:
        model.setObjective(expected_value, GRB.MAXIMIZE)

    model.optimize()
    if model.Status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        raise RuntimeError(f"Scenario Gurobi failed. Status={model.Status}")

    return {
        "charge": np.array([ch[0, t].X for t in range(hours)], dtype=float),
        "discharge": np.array([dh[0, t].X for t in range(hours)], dtype=float),
        "direct": np.array([gw[0, t].X for t in range(hours)], dtype=float),
        "mode": np.array([mode[0, t].X for t in range(hours)], dtype=float),
        "objective": float(model.ObjVal),
        "runtime": float(model.Runtime),
        "status": int(model.Status),
    }


def apply_direct_reserve(action: dict, direct_reserve_mw: float) -> dict:
    if direct_reserve_mw <= 0:
        return action
    reserved = dict(action)
    direct = np.asarray(action["direct"], dtype=float).copy()
    discharge = np.asarray(action["discharge"], dtype=float)
    reserved["direct"] = np.minimum(
        np.maximum(0.0, base.GRID_CAP - discharge),
        direct + float(direct_reserve_mw),
    )
    return reserved


def execute_storage_block(
    action: dict,
    actual_generation: np.ndarray,
    start_soc: float,
) -> dict[str, np.ndarray]:
    n = len(actual_generation)
    direct = np.zeros(n, dtype=float)
    charge = np.zeros(n, dtype=float)
    discharge = np.zeros(n, dtype=float)
    delivered = np.zeros(n, dtype=float)
    curtailment = np.zeros(n, dtype=float)
    storage = np.zeros(n + 1, dtype=float)
    mode = np.zeros(n, dtype=float)
    storage[0] = float(np.clip(start_soc, base.CMIN, base.CMAX))
    planned_direct = np.asarray(action["direct"], dtype=float)
    planned_charge = np.asarray(action["charge"], dtype=float)
    planned_discharge = np.asarray(action["discharge"], dtype=float)
    planned_mode = np.asarray(action["mode"], dtype=float)

    for t, generation_value in enumerate(actual_generation):
        generation = max(0.0, float(generation_value))
        if float(planned_mode[t]) >= 0.5:
            mode[t] = 1.0
            room = max(0.0, base.CMAX - storage[t])
            charge[t] = min(float(planned_charge[t]), base.PS, generation, room)
            direct[t] = min(float(planned_direct[t]), max(0.0, generation - charge[t]), base.GRID_CAP)
        else:
            mode[t] = 0.0
            available_by_soc_floor = max(0.0, (storage[t] - base.CMIN) * base.RTE)
            discharge[t] = min(float(planned_discharge[t]), base.PS, available_by_soc_floor)
            direct[t] = min(float(planned_direct[t]), generation, max(0.0, base.GRID_CAP - discharge[t]))
        delivered[t] = direct[t] + discharge[t]
        curtailment[t] = max(0.0, generation - direct[t] - charge[t])
        storage[t + 1] = float(np.clip(storage[t] + charge[t] - discharge[t] / base.RTE, base.CMIN, base.CMAX))

    return {
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "delivered": delivered,
        "curtailment": curtailment,
        "storage": storage,
        "mode": mode,
    }


def baseline_value_for_scenarios(
    generation_scenarios: np.ndarray,
    price_scenarios: np.ndarray,
    weights: np.ndarray,
    start_soc: float,
    target_mw: float,
) -> float:
    total = 0.0
    for s in range(generation_scenarios.shape[0]):
        storage = float(np.clip(start_soc, base.CMIN, base.CMAX))
        value = 0.0
        for generation, price in zip(generation_scenarios[s], price_scenarios[s]):
            generation = max(0.0, float(generation))
            if generation >= target_mw:
                charge = min(generation - target_mw, base.PS, base.CMAX - storage)
                direct = min(target_mw, base.GRID_CAP)
                delivered = direct
                storage = min(base.CMAX, storage + charge)
            else:
                direct = min(generation, base.GRID_CAP)
                needed = max(0.0, target_mw - direct)
                discharge = min(
                    needed,
                    base.PS,
                    (storage - base.CMIN) * base.RTE,
                    max(0.0, base.GRID_CAP - direct),
                )
                delivered = direct + discharge
                storage = max(base.CMIN, storage - discharge / base.RTE)
            value += float(price) * delivered
        total += float(weights[s]) * value
    return total


def baseline_block_action(actual_generation: np.ndarray, start_soc: float, target_mw: float) -> dict:
    n = len(actual_generation)
    charge = np.zeros(n, dtype=float)
    discharge = np.zeros(n, dtype=float)
    direct = np.zeros(n, dtype=float)
    mode = np.zeros(n, dtype=float)
    storage = float(np.clip(start_soc, base.CMIN, base.CMAX))
    for t, generation_value in enumerate(actual_generation):
        generation = max(0.0, float(generation_value))
        if generation >= target_mw:
            mode[t] = 1.0
            charge[t] = min(generation - target_mw, base.PS, base.CMAX - storage)
            direct[t] = min(target_mw, base.GRID_CAP)
            storage = min(base.CMAX, storage + charge[t])
        else:
            direct[t] = min(generation, base.GRID_CAP)
            needed = max(0.0, target_mw - direct[t])
            discharge[t] = min(
                needed,
                base.PS,
                (storage - base.CMIN) * base.RTE,
                max(0.0, base.GRID_CAP - direct[t]),
            )
            storage = max(base.CMIN, storage - discharge[t] / base.RTE)
    return {
        "charge": charge,
        "discharge": discharge,
        "direct": direct,
        "mode": mode,
        "objective": 0.0,
        "runtime": 0.0,
        "status": 2,
    }


def baseline_first_hour_action(actual_generation: float, start_soc: float, target_mw: float) -> dict[str, float]:
    generation = max(0.0, float(actual_generation))
    storage = float(np.clip(start_soc, base.CMIN, base.CMAX))
    if generation >= target_mw:
        charge = min(generation - target_mw, base.PS, base.CMAX - storage)
        direct = min(generation - charge, base.GRID_CAP)
        return {
            "charge": charge,
            "discharge": 0.0,
            "direct": direct,
            "mode": 1.0,
            "objective": 0.0,
            "runtime": 0.0,
            "status": 2,
        }
    direct = min(generation, base.GRID_CAP)
    needed = max(0.0, target_mw - direct)
    discharge = min(
        needed,
        base.PS,
        (storage - base.CMIN) * base.RTE,
        max(0.0, base.GRID_CAP - direct),
    )
    return {
        "charge": 0.0,
        "discharge": discharge,
        "direct": direct,
        "mode": 0.0,
        "objective": 0.0,
        "runtime": 0.0,
        "status": 2,
    }


def run_single_forecast_recourse(
    df: pd.DataFrame,
    origins: np.ndarray,
    wind_center: np.ndarray,
    price_center: np.ndarray,
    max_origins: int | None,
    nowcast_first_hour: bool,
    gate_margin: float | None,
    baseline_target_mw: float,
    execution_step_hours: int,
    direct_reserve_mw: float,
    apply_gate: bool,
) -> pd.DataFrame:
    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)
    current_soc = base.SOC0
    rows = []
    selected_origins = origins if max_origins is None else origins[:max_origins]
    started = time.perf_counter()

    for row_index, origin in enumerate(selected_origins):
        execute_len = min(execution_step_hours, HORIZON, len(df) - int(origin))
        if execute_len <= 0:
            break
        planned_wind = wind_center[row_index, :HORIZON].copy()
        planned_price = price_center[row_index, :HORIZON].copy()
        if nowcast_first_hour:
            planned_wind[0] = generation[origin]
            planned_price[0] = price[origin]
        action = solve_scenario_window(
            planned_wind.reshape(1, -1),
            planned_price.reshape(1, -1),
            np.array([1.0]),
            current_soc,
            0.0,
            execute_len,
        )
        action = apply_direct_reserve(action, direct_reserve_mw)
        used_gate = 0.0
        if gate_margin is not None and apply_gate:
            baseline_value = baseline_value_for_scenarios(
                planned_wind.reshape(1, -1),
                planned_price.reshape(1, -1),
                np.array([1.0]),
                current_soc,
                baseline_target_mw,
            )
            if float(action["objective"]) < baseline_value * (1.0 + gate_margin):
                action = baseline_block_action(generation[origin : origin + execute_len], current_soc, baseline_target_mw)
                action["objective"] = baseline_value
                used_gate = 1.0
        realized = execute_storage_block(action, generation[origin : origin + execute_len], current_soc)
        rows.extend(make_label_rows(df, int(origin), HORIZON, planned_wind, planned_price, action, realized, execute_len, used_gate))
        current_soc = float(realized["storage"][-1])
        if (row_index + 1) % 500 == 0:
            print(f"single recourse {row_index + 1}/{len(selected_origins)}, SoC={current_soc:.1f}, elapsed={time.perf_counter()-started:.1f}s", flush=True)
    return pd.DataFrame(rows)


def run_scenario_controller(
    df: pd.DataFrame,
    origins: np.ndarray,
    wind_center: np.ndarray,
    price_center: np.ndarray,
    quantile_lookup: dict[str, dict[float, np.ndarray]],
    spec_name: str,
    max_origins: int | None,
    nowcast_first_hour: bool,
    gate_margin: float | None,
    baseline_target_mw: float,
    execution_step_hours: int,
    direct_reserve_mw: float,
) -> pd.DataFrame:
    generation = df["power_generated"].to_numpy(float)
    current_soc = base.SOC0
    rows = []
    spec = SCENARIO_SPECS[spec_name]
    selected_origins = origins if max_origins is None else origins[:max_origins]
    started = time.perf_counter()

    for row_index, origin in enumerate(selected_origins):
        execute_len = min(execution_step_hours, HORIZON, len(df) - int(origin))
        if execute_len <= 0:
            break
        planned_wind_center = wind_center[row_index, :HORIZON].copy()
        planned_price_center = price_center[row_index, :HORIZON].copy()
        if nowcast_first_hour:
            planned_wind_center[0] = generation[origin]
            planned_price_center[0] = df["lmp"].iloc[origin]
        wind_scenarios, price_scenarios, weights = scenario_matrices(
            planned_wind_center,
            planned_price_center,
            quantile_lookup,
            spec,
        )
        if nowcast_first_hour:
            wind_scenarios[:, 0] = generation[origin]
            price_scenarios[:, 0] = df["lmp"].iloc[origin]
        action = solve_scenario_window(
            wind_scenarios,
            price_scenarios,
            weights,
            current_soc,
            float(spec["risk_lambda"]),
            execute_len,
        )
        action = apply_direct_reserve(action, direct_reserve_mw)
        used_gate = 0.0
        if gate_margin is not None:
            baseline_value = baseline_value_for_scenarios(
                wind_scenarios,
                price_scenarios,
                weights,
                current_soc,
                baseline_target_mw,
            )
            if float(action["objective"]) < baseline_value * (1.0 + gate_margin):
                action = baseline_block_action(generation[origin : origin + execute_len], current_soc, baseline_target_mw)
                action["objective"] = baseline_value
                used_gate = 1.0
        realized = execute_storage_block(action, generation[origin : origin + execute_len], current_soc)
        rows.extend(make_label_rows(df, int(origin), HORIZON, planned_wind_center, planned_price_center, action, realized, execute_len, used_gate))
        current_soc = float(realized["storage"][-1])
        if (row_index + 1) % 500 == 0:
            print(f"{spec_name} {row_index + 1}/{len(selected_origins)}, SoC={current_soc:.1f}, elapsed={time.perf_counter()-started:.1f}s", flush=True)
    return pd.DataFrame(rows)


def make_label_rows(
    df: pd.DataFrame,
    origin: int,
    horizon: int,
    forecast_generation: np.ndarray,
    forecast_price: np.ndarray,
    action: dict,
    realized: dict[str, np.ndarray],
    execute_len: int,
    used_gate: float,
) -> list[dict[str, float | int | str]]:
    rows = []
    planned_direct = np.asarray(action["direct"], dtype=float)
    planned_charge = np.asarray(action["charge"], dtype=float)
    planned_discharge = np.asarray(action["discharge"], dtype=float)
    for k in range(execute_len):
        i = origin + k
        rows.append(
            {
                "hour_index": int(i),
                "datetime": df["datetime"].iloc[i],
                "horizon_hours": int(horizon),
                "execution_step_hours": int(execute_len),
                "actual_generation_mw": float(df["power_generated"].iloc[i]),
                "forecast_generation_mw": float(forecast_generation[k]),
                "actual_price": float(df["lmp"].iloc[i]),
                "forecast_price": float(forecast_price[k]),
                "planned_direct_mw": float(planned_direct[k]),
                "planned_charge_mw": float(planned_charge[k]),
                "planned_discharge_mw": float(planned_discharge[k]),
                "realized_direct_mw": float(realized["direct"][k]),
                "realized_charge_mw": float(realized["charge"][k]),
                "realized_discharge_mw": float(realized["discharge"][k]),
                "realized_delivered_mw": float(realized["delivered"][k]),
                "realized_curtailment_mw": float(realized["curtailment"][k]),
                "soc_start_mwh": float(realized["storage"][k]),
                "soc_end_mwh": float(realized["storage"][k + 1]),
                "mode_charge_binary": float(realized["mode"][k]),
                "solver_objective": float(action["objective"]),
                "solver_runtime_seconds": float(action["runtime"]),
                "solver_status": int(action["status"]),
                "used_baseload_gate": float(used_gate),
            }
        )
    return rows


def summarize(labels: pd.DataFrame, candidate: str, wind_forecast: str, price_forecast: str) -> dict:
    row = candidate_summary(labels, candidate, wind_forecast, price_forecast, HORIZON, False)
    actual_generation = labels["actual_generation_mw"].to_numpy(float)
    actual_price = labels["actual_price"].to_numpy(float)
    constant_100mw = constant_output_100mw_delivery(actual_generation)
    constant_revenue = base.revenue(constant_100mw, actual_price)
    dispatch_revenue = float(row["dispatch_revenue"])
    dispatch_cove = float(row["dispatch_cove_index"])
    dispatch_cost = base.annualized_dispatch_cost()
    constant_cove = dispatch_cost / constant_revenue
    row["100mw_baseload_revenue"] = constant_revenue
    row["100mw_baseload_cove"] = constant_cove
    row["revenue_gain_vs_100mw_baseload_pct"] = (dispatch_revenue / constant_revenue - 1.0) * 100.0
    row["cove_reduction_vs_100mw_baseload_pct"] = (constant_cove - dispatch_cove) / constant_cove * 100.0
    row["mean_solver_runtime_seconds"] = float(labels["solver_runtime_seconds"].mean())
    row["total_solver_runtime_seconds"] = float(labels["solver_runtime_seconds"].sum())
    row["time_limit_fraction"] = float((labels["solver_status"] == 9).mean())
    if "used_baseload_gate" in labels.columns:
        row["gate_fraction"] = float(labels["used_baseload_gate"].mean())
    else:
        row["gate_fraction"] = 0.0
    return row


def constant_output_100mw_delivery(generation: np.ndarray, target_mw: float = 100.0) -> np.ndarray:
    storage = base.SOC0
    delivered = np.zeros(len(generation), dtype=float)
    for idx, generation_value in enumerate(generation):
        wind = max(0.0, float(generation_value))
        if wind >= target_mw:
            direct = min(target_mw, base.GRID_CAP)
            charge = min(wind - direct, base.PS, base.CMAX - storage)
            delivered[idx] = direct
            storage = min(base.CMAX, storage + charge)
        else:
            direct = min(wind, base.GRID_CAP)
            needed = max(0.0, target_mw - direct)
            discharge = min(
                needed,
                base.PS,
                max(0.0, (storage - base.CMIN) * base.RTE),
                max(0.0, base.GRID_CAP - direct),
            )
            delivered[idx] = direct + discharge
            storage = max(base.CMIN, storage - discharge / base.RTE)
    return delivered


def make_figures(summary: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    ordered = summary.sort_values("dispatch_revenue")
    colors = ["#64748b" if "baseload" in m.lower() else "#2563eb" for m in ordered["candidate"]]
    colors = ["#16a34a" if r == ordered["dispatch_revenue"].max() else c for r, c in zip(ordered["dispatch_revenue"], colors)]

    fig, ax = plt.subplots(figsize=(11, 5.8), dpi=220)
    ax.barh(ordered["candidate"], ordered["dispatch_revenue"] / 1e6, color=colors)
    ax.axvline(float(ordered["baseload_revenue"].iloc[0]) / 1e6, color="#111827", linestyle="--", label="Internal storage-baseload")
    ax.set_xlabel("Realized revenue, actual 2014-2023 score ($ millions)")
    ax.set_title("Uncertainty-aware scenario dispatch vs single forecast")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figure_01_scenario_revenue_comparison.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.8), dpi=220)
    ax.barh(ordered["candidate"], ordered["cove_reduction_vs_baseload_pct"], color=colors)
    ax.axvline(0, color="#111827", linewidth=1)
    ax.set_xlabel("COVE reduction vs internal storage-baseload (%)")
    ax.set_title("Internal scenario-runner COVE comparison")
    fig.tight_layout()
    fig.savefig(OUT / "figure_02_scenario_cove_comparison.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    global OUT, HORIZON
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-hours", type=int, default=48, help="Forecast/dispatch lookahead for each scenario MILP.")
    parser.add_argument("--forecast-model-max-horizon-hours", type=int, default=168, help="Maximum forecast lead used when training ridge models, matching Step 2 horizon sweep.")
    parser.add_argument("--evaluation-cutoff-horizon-hours", type=int, default=168, help="Common end-of-test cutoff horizon, matching Step 2 horizon sweep.")
    parser.add_argument("--execution-step-hours", type=int, default=24, help="How many hours are executed from each optimized plan.")
    parser.add_argument("--replanning-interval-hours", type=int, default=24, help="How many hours the controller advances between solves.")
    parser.add_argument("--storage-power-mw", type=float, default=base.PS)
    parser.add_argument("--storage-duration-h", type=float, default=base.DURATION_HOURS)
    parser.add_argument("--rte", type=float, default=base.RTE)
    parser.add_argument("--dod", type=float, default=base.DOD)
    parser.add_argument("--grid-cap-mw", type=float, default=base.GRID_CAP)
    parser.add_argument(
        "--initial-soc-mwh",
        type=float,
        default=None,
        help="Initial SoC. If omitted, uses midpoint between Cmin and Cmax.",
    )
    parser.add_argument("--max-origins", type=int, default=None, help="Limit hourly origins for quick tests.")
    parser.add_argument("--direct-reserve-mw", type=float, default=75.0, help="Direct-wind reserve applied to planned direct export before realized execution.")
    parser.add_argument("--train-origin-stride", type=int, default=24, help="Training origin stride for the causal ridge model.")
    parser.add_argument("--residual-origin-stride", type=int, default=1, help="Stride for residual origins used to estimate scenario quantiles.")
    parser.add_argument("--fallback-target-mw", type=float, default=100.0, help="Rule-based target output used by the safety fallback gate.")
    parser.add_argument("--gate-single-forecast", action="store_true", help="Also apply the safety gate to the single-forecast controller.")
    parser.add_argument(
        "--variants",
        nargs="+",
        default=[
            "single_recourse",
            "three_scenario_expected",
            "five_scenario_expected",
            "seven_scenario_expected",
            "ten_scenario_expected",
        ],
    )
    parser.add_argument(
        "--nowcast-first-hour",
        dest="nowcast_first_hour",
        action="store_true",
        default=True,
        help="Use actual current wind/price for the hour being executed, forecasts/scenarios after that.",
    )
    parser.add_argument(
        "--no-nowcast-first-hour",
        dest="nowcast_first_hour",
        action="store_false",
        help="Disable the official current-hour nowcast setting.",
    )
    parser.add_argument("--gate-margin", type=float, default=None, help="Fallback to baseload-style action unless optimized forecast value beats forecast baseload by this fraction.")
    parser.add_argument("--out-dir", type=Path, default=OUT, help="Output directory for labels, figures, and summary files.")
    parser.add_argument(
        "--calibration-mode",
        choices=["in_sample_residual", "split_conformal"],
        default="in_sample_residual",
        help="Use all pre-test residuals or train/calibrate/test split conformal residual quantiles.",
    )
    parser.add_argument("--forecast-train-end", default="2013-01-01", help="End date for center forecast training in split_conformal mode.")
    parser.add_argument("--calibration-end", default="2014-01-01", help="End date for conformal calibration and start of test period.")
    args = parser.parse_args()
    OUT = args.out_dir
    HORIZON = int(args.horizon_hours)
    execution_step_hours = int(args.execution_step_hours)
    replanning_interval_hours = int(args.replanning_interval_hours)
    if execution_step_hours < 1 or replanning_interval_hours < 1:
        raise ValueError("Execution step and replanning interval must be at least one hour.")
    base.PS = float(args.storage_power_mw)
    base.DURATION_HOURS = float(args.storage_duration_h)
    base.RTE = float(args.rte)
    base.SQRT_RTE = math.sqrt(base.RTE)
    base.DOD = float(args.dod)
    base.CMAX = base.PS * base.DURATION_HOURS
    base.CMIN = base.CMAX * (1.0 - base.DOD)
    base.SOC0 = (
        float(args.initial_soc_mwh)
        if args.initial_soc_mwh is not None
        else (base.CMIN + base.CMAX) / 2.0
    )
    base.GRID_CAP = float(args.grid_cap_mw)

    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(base.DATA_PATH, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df[["datetime", "power_generated", "lmp", "user_load_zonal"]].dropna().reset_index(drop=True)

    train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64("2014-01-01")))
    raw_lmp = df["lmp"].to_numpy(float)
    config = util.load_config(CONFIG_PATH)
    capped_price = np.minimum(raw_lmp, float(config["price_threshold"]))
    training_price_mean = float(capped_price[:train_end].mean())
    df["raw_lmp"] = raw_lmp
    df["lmp"] = capped_price / training_price_mean
    forecast_train_end = train_end
    residual_start = max(base.PAST_LAGS)
    residual_end = train_end
    quantile_method = "empirical"

    if args.calibration_mode == "split_conformal":
        forecast_train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64(args.forecast_train_end)))
        residual_start = forecast_train_end
        residual_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64(args.calibration_end)))
        train_end = residual_end
        quantile_method = "split_conformal"
        if residual_end <= residual_start + HORIZON:
            raise ValueError("Calibration period is too short for the selected horizon.")

    forecast_model_max_horizon = int(args.forecast_model_max_horizon_hours)
    evaluation_cutoff_horizon = int(args.evaluation_cutoff_horizon_hours)
    if forecast_model_max_horizon < HORIZON:
        raise ValueError("forecast-model-max-horizon-hours must be at least horizon-hours.")
    if evaluation_cutoff_horizon < HORIZON:
        raise ValueError("evaluation-cutoff-horizon-hours must be at least horizon-hours.")
    origins = np.arange(train_end, len(df), replanning_interval_hours)
    origins = origins[origins + evaluation_cutoff_horizon <= len(df)]
    if args.max_origins is not None:
        print(f"Quick run limited to {args.max_origins} hourly origins.", flush=True)

    print(f"Building {HORIZON}h hourly wind and price forecasts...", flush=True)
    wind_center, price_center, generation_models, price_models = build_forecasts(
        df,
        forecast_train_end,
        origins,
        int(args.train_origin_stride),
        forecast_model_max_horizon,
    )
    baseline_target_mw = float(args.fallback_target_mw)
    needed_quantiles = sorted(
        {
            q
            for spec in SCENARIO_SPECS.values()
            for q in (
                spec["wind_quantiles"]
                + spec["price_quantiles"]
                + [event["quantile"] for event in spec.get("price_events", []) if "quantile" in event]
                + [0.50]
            )
        }
    )
    print(
        f"Estimating {args.calibration_mode} quantiles from "
        f"{df['datetime'].iloc[residual_start]} to {df['datetime'].iloc[residual_end - 1]}: {needed_quantiles}",
        flush=True,
    )
    quantile_lookup = residual_quantiles(
        df,
        residual_start,
        residual_end,
        generation_models,
        price_models,
        needed_quantiles,
        method=quantile_method,
        origin_stride=int(args.residual_origin_stride),
    )

    summary_rows = []

    if "single_recourse" in args.variants:
        print("Running single-forecast rolling-horizon controller with direct-wind reserve...", flush=True)
        labels = run_single_forecast_recourse(
            df,
            origins,
            wind_center,
            price_center,
            args.max_origins,
            args.nowcast_first_hour,
            args.gate_margin,
            baseline_target_mw,
            execution_step_hours,
            float(args.direct_reserve_mw),
            bool(args.gate_single_forecast),
        )
        suffix = "_nowcast" if args.nowcast_first_hour else ""
        suffix += "_gated" if args.gate_margin is not None and args.gate_single_forecast else ""
        labels.to_csv(OUT / f"single_forecast_recourse{suffix}_labels.csv", index=False)
        summary_rows.append(
            summarize(
                labels,
                f"single_forecast_recourse{suffix}",
                "current measured wind + ridge future" if args.nowcast_first_hour else "causal ridge",
                "current measured price + ridge future" if args.nowcast_first_hour else "causal ridge price",
            )
        )

    for variant in args.variants:
        if variant == "single_recourse":
            continue
        if variant not in SCENARIO_SPECS:
            raise ValueError(f"Unknown variant {variant}. Options: {sorted(SCENARIO_SPECS)}")
        print(f"Running scenario controller: {variant}", flush=True)
        labels = run_scenario_controller(
            df,
            origins,
            wind_center,
            price_center,
            quantile_lookup,
            variant,
            args.max_origins,
            args.nowcast_first_hour,
            args.gate_margin,
            baseline_target_mw,
            execution_step_hours,
            float(args.direct_reserve_mw),
        )
        suffix = "_nowcast" if args.nowcast_first_hour else ""
        suffix += "_gated" if args.gate_margin is not None else ""
        labels.to_csv(OUT / f"{variant}{suffix}_labels.csv", index=False)
        spec = SCENARIO_SPECS[variant]
        summary_rows.append(
            summarize(
                labels,
                f"{variant}{suffix}",
                f"{'current measured wind + ' if args.nowcast_first_hour else ''}causal ridge residual scenarios {spec['wind_quantiles']}",
                f"{'current measured price + ' if args.nowcast_first_hour else ''}causal ridge price residual scenarios {spec['price_quantiles']}",
            )
        )

    summary = pd.DataFrame(summary_rows).sort_values("dispatch_revenue", ascending=False)
    summary.to_csv(OUT / "uncertainty_aware_summary.csv", index=False)
    make_figures(summary)

    metadata = {
        "data_path": str(base.DATA_PATH),
        "training_period": f"{df['datetime'].iloc[0]} through {df['datetime'].iloc[train_end - 1]}",
        "center_forecast_training_period": f"{df['datetime'].iloc[0]} through {df['datetime'].iloc[forecast_train_end - 1]}",
        "calibration_mode": args.calibration_mode,
        "calibration_period": f"{df['datetime'].iloc[residual_start]} through {df['datetime'].iloc[residual_end - 1]}",
        "test_start": str(df["datetime"].iloc[origins[0]]),
        "test_end": str(df["datetime"].iloc[(origins if args.max_origins is None else origins[: args.max_origins])[-1]]),
        "horizon_hours": HORIZON,
        "forecast_model_max_horizon_hours": forecast_model_max_horizon,
        "evaluation_cutoff_horizon_hours": evaluation_cutoff_horizon,
        "non_anticipativity": f"The first {execution_step_hours} hours of direct wind, storage charge, storage discharge, and mode are shared across scenarios; later horizon actions are recourse because the controller replans after the executed block.",
        "execution_rule": f"The chosen storage plan is executed for {execution_step_hours} hours. Direct wind to grid is adjusted using actual realized wind and grid capacity.",
        "replanning_interval_hours": replanning_interval_hours,
        "direct_reserve_mw": float(args.direct_reserve_mw),
        "train_origin_stride": int(args.train_origin_stride),
        "residual_origin_stride": int(args.residual_origin_stride),
        "nowcast_first_hour": bool(args.nowcast_first_hour),
        "gate_margin": args.gate_margin,
        "baseline_target_mw_from_training": baseline_target_mw,
        "fallback_target_mw": baseline_target_mw,
        "gate_single_forecast": bool(args.gate_single_forecast),
        "scenario_specs": {
            name: {
                key: (value.tolist() if isinstance(value, np.ndarray) else value)
                for key, value in spec.items()
            }
            for name, spec in SCENARIO_SPECS.items()
        },
        "storage_constraints": {
            "power_mw": base.PS,
            "duration_hours": base.DURATION_HOURS,
            "cmax_mwh": base.CMAX,
            "cmin_mwh": base.CMIN,
            "soc0_mwh": base.SOC0,
            "rte": base.RTE,
            "grid_cap_mw": base.GRID_CAP,
        },
    }
    (OUT / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2))

    print("\nUNCERTAINTY-AWARE RESULTS")
    print(
        summary[
            [
                "candidate",
                "dispatch_revenue",
                "baseload_revenue",
                "revenue_gain_vs_baseload_pct",
                "cove_reduction_vs_baseload_pct",
                "min_soc",
                "max_soc",
                "final_soc",
                "mean_solver_runtime_seconds",
                "time_limit_fraction",
                "gate_fraction",
            ]
        ].to_string(index=False)
    )
    print(f"Saved outputs to {OUT}")


if __name__ == "__main__":
    main()
