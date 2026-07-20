from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

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
import run_nora_matching_forecast_horizons as base  # noqa: E402
from run_best_forecast_dispatch_search import (  # noqa: E402
    PRICE_CLIP,
    candidate_summary,
    cove_reduction_from_revenues,
)


HORIZON = 48
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
) -> tuple[np.ndarray, np.ndarray, list[base.DirectForecastModel]]:
    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)

    models = base.fit_direct_models(
        generation,
        df["datetime"],
        train_end,
        HORIZON,
        0.0,
        max(float(generation[:train_end].max()), base.GRID_CAP),
        alpha=10.0,
        origin_stride=1,
    )
    wind_center = base.make_generation_forecasts(generation, df["datetime"], origins, models)
    price_center = matrix_from_indices(price, origins, lambda origin, lead: origin + lead - 24)
    price_center = np.clip(price_center, PRICE_CLIP[0], PRICE_CLIP[1])
    return wind_center, price_center, models


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
    models: list[base.DirectForecastModel],
    quantiles: list[float],
    method: str = "empirical",
) -> dict[str, dict[float, np.ndarray]]:
    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)
    residual_start = max(residual_start, max(base.PAST_LAGS))
    residual_origins = np.arange(residual_start, residual_end - HORIZON)
    residual_wind_forecast = base.make_generation_forecasts(generation, df["datetime"], residual_origins, models)
    residual_price_forecast = matrix_from_indices(price, residual_origins, lambda origin, lead: origin + lead - 24)

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
    return np.asarray(wind_scenarios), np.asarray(price_scenarios), weights


def solve_scenario_window(
    generation_scenarios: np.ndarray,
    price_scenarios: np.ndarray,
    weights: np.ndarray,
    start_soc: float,
    risk_lambda: float,
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
            model.addConstr(dh[s, t] <= soc[s, t] * base.RTE)
            model.addConstr(ed[s, t] == gw[s, t] + dh[s, t])
            model.addConstr(soc[s, t + 1] == soc[s, t] + ch[s, t] - dh[s, t] / base.SQRT_RTE)

    # First-hour storage action must be the same across futures; future actions
    # are recourse variables because the controller replans after one hour.
    for s in range(1, scenario_count):
        model.addConstr(ch[s, 0] == ch[0, 0])
        model.addConstr(dh[s, 0] == dh[0, 0])
        model.addConstr(gw[s, 0] == gw[0, 0])
        model.addConstr(mode[s, 0] == mode[0, 0])

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
        "charge": float(ch[0, 0].X),
        "discharge": float(dh[0, 0].X),
        "direct": float(gw[0, 0].X),
        "mode": float(mode[0, 0].X),
        "objective": float(model.ObjVal),
        "runtime": float(model.Runtime),
        "status": int(model.Status),
    }


def execute_first_hour_storage_action(
    action: dict[str, float],
    actual_generation: float,
    start_soc: float,
) -> dict[str, float]:
    generation = max(0.0, float(actual_generation))
    storage = float(np.clip(start_soc, base.CMIN, base.CMAX))
    mode = 1.0 if action["mode"] >= 0.5 else 0.0
    planned_direct = float(action.get("direct", base.GRID_CAP))
    charge = 0.0
    discharge = 0.0

    if mode >= 0.5:
        room = max(0.0, base.CMAX - storage)
        charge = min(float(action["charge"]), base.PS, generation, room)
        direct = min(planned_direct, max(0.0, generation - charge), base.GRID_CAP)
    else:
        available_by_nora = max(0.0, storage * base.RTE)
        available_by_soc_floor = max(0.0, (storage - base.CMIN) * base.SQRT_RTE)
        discharge = min(float(action["discharge"]), base.PS, available_by_nora, available_by_soc_floor)
        direct = min(planned_direct, generation, max(0.0, base.GRID_CAP - discharge))

    delivered = direct + discharge
    soc_end = float(np.clip(storage + charge - discharge / base.SQRT_RTE, base.CMIN, base.CMAX))
    curtailment = max(0.0, generation - direct - charge)
    return {
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "delivered": delivered,
        "curtailment": curtailment,
        "soc_start": storage,
        "soc_end": soc_end,
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
                direct = min(generation - charge, base.GRID_CAP)
                delivered = direct
                storage = min(base.CMAX, storage + charge)
            else:
                direct = min(generation, base.GRID_CAP)
                needed = max(0.0, target_mw - direct)
                discharge = min(
                    needed,
                    base.PS,
                    storage * base.RTE,
                    (storage - base.CMIN) * base.SQRT_RTE,
                    max(0.0, base.GRID_CAP - direct),
                )
                delivered = direct + discharge
                storage = max(base.CMIN, storage - discharge / base.SQRT_RTE)
            value += float(price) * delivered
        total += float(weights[s]) * value
    return total


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
        storage * base.RTE,
        (storage - base.CMIN) * base.SQRT_RTE,
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
) -> pd.DataFrame:
    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)
    current_soc = base.SOC0
    rows = []
    selected_origins = origins if max_origins is None else origins[:max_origins]
    started = time.perf_counter()

    for row_index, origin in enumerate(selected_origins):
        planned_wind = wind_center[row_index, :HORIZON].copy()
        planned_price = price_center[row_index, :HORIZON].copy()
        if nowcast_first_hour:
            planned_wind[0] = generation[origin]
            planned_price[0] = price[origin]
        planned = base.solve_window_nora(
            planned_wind,
            planned_price,
            current_soc,
            HORIZON,
        )
        action = {
            "charge": float(planned["charge"][0]),
            "discharge": float(planned["discharge"][0]),
            "direct": float(planned["direct"][0]),
            "mode": float(planned["mode"][0]),
            "objective": float(planned["objective"]),
            "runtime": float(planned["runtime"]),
            "status": 2,
        }
        used_gate = 0.0
        if gate_margin is not None:
            baseline_value = baseline_value_for_scenarios(
                planned_wind.reshape(1, -1),
                planned_price.reshape(1, -1),
                np.array([1.0]),
                current_soc,
                baseline_target_mw,
            )
            if float(planned["objective"]) < baseline_value * (1.0 + gate_margin):
                action = baseline_first_hour_action(generation[origin], current_soc, baseline_target_mw)
                action["objective"] = baseline_value
                used_gate = 1.0
        realized = execute_first_hour_storage_action(action, generation[origin], current_soc)
        row = make_label_row(df, origin, HORIZON, planned_wind[0], planned_price[0], action, realized)
        row["used_baseload_gate"] = used_gate
        rows.append(row)
        current_soc = realized["soc_end"]
        if (row_index + 1) % 10000 == 0:
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
) -> pd.DataFrame:
    generation = df["power_generated"].to_numpy(float)
    current_soc = base.SOC0
    rows = []
    spec = SCENARIO_SPECS[spec_name]
    selected_origins = origins if max_origins is None else origins[:max_origins]
    started = time.perf_counter()

    for row_index, origin in enumerate(selected_origins):
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
        )
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
                action = baseline_first_hour_action(generation[origin], current_soc, baseline_target_mw)
                action["objective"] = baseline_value
                used_gate = 1.0
        realized = execute_first_hour_storage_action(action, generation[origin], current_soc)
        row = make_label_row(df, origin, HORIZON, planned_wind_center[0], planned_price_center[0], action, realized)
        row["used_baseload_gate"] = used_gate
        rows.append(row)
        current_soc = realized["soc_end"]
        if (row_index + 1) % 5000 == 0:
            print(f"{spec_name} {row_index + 1}/{len(selected_origins)}, SoC={current_soc:.1f}, elapsed={time.perf_counter()-started:.1f}s", flush=True)
    return pd.DataFrame(rows)


def make_label_row(
    df: pd.DataFrame,
    origin: int,
    horizon: int,
    forecast_generation: float,
    forecast_price: float,
    action: dict[str, float],
    realized: dict[str, float],
) -> dict[str, float | int | str]:
    return {
        "hour_index": int(origin),
        "datetime": df["datetime"].iloc[origin],
        "horizon_hours": int(horizon),
        "actual_generation_mw": float(df["power_generated"].iloc[origin]),
        "forecast_generation_mw": float(forecast_generation),
        "actual_price": float(df["lmp"].iloc[origin]),
        "forecast_price": float(forecast_price),
        "planned_direct_mw": float(action.get("direct", np.nan)),
        "planned_charge_mw": float(action["charge"]),
        "planned_discharge_mw": float(action["discharge"]),
        "realized_direct_mw": float(realized["direct"]),
        "realized_charge_mw": float(realized["charge"]),
        "realized_discharge_mw": float(realized["discharge"]),
        "realized_delivered_mw": float(realized["delivered"]),
        "realized_curtailment_mw": float(realized["curtailment"]),
        "soc_start_mwh": float(realized["soc_start"]),
        "soc_end_mwh": float(realized["soc_end"]),
        "mode_charge_binary": float(realized["mode"]),
        "solver_objective": float(action["objective"]),
        "solver_runtime_seconds": float(action["runtime"]),
        "solver_status": int(action["status"]),
    }


def summarize(labels: pd.DataFrame, candidate: str, wind_forecast: str, price_forecast: str) -> dict:
    row = candidate_summary(labels, candidate, wind_forecast, price_forecast, HORIZON, False)
    row["mean_solver_runtime_seconds"] = float(labels["solver_runtime_seconds"].mean())
    row["total_solver_runtime_seconds"] = float(labels["solver_runtime_seconds"].sum())
    row["time_limit_fraction"] = float((labels["solver_status"] == 9).mean())
    if "used_baseload_gate" in labels.columns:
        row["gate_fraction"] = float(labels["used_baseload_gate"].mean())
    else:
        row["gate_fraction"] = 0.0
    return row


def make_figures(summary: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    ordered = summary.sort_values("dispatch_revenue")
    colors = ["#64748b" if "baseload" in m.lower() else "#2563eb" for m in ordered["candidate"]]
    colors = ["#16a34a" if r == ordered["dispatch_revenue"].max() else c for r, c in zip(ordered["dispatch_revenue"], colors)]

    fig, ax = plt.subplots(figsize=(11, 5.8), dpi=220)
    ax.barh(ordered["candidate"], ordered["dispatch_revenue"] / 1e6, color=colors)
    ax.axvline(float(ordered["baseload_revenue"].iloc[0]) / 1e6, color="#111827", linestyle="--", label="Baseload")
    ax.set_xlabel("Realized revenue, actual 2014-2023 score ($ millions)")
    ax.set_title("Uncertainty-aware scenario dispatch vs single forecast")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figure_01_scenario_revenue_comparison.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.8), dpi=220)
    ax.barh(ordered["candidate"], ordered["cove_reduction_vs_baseload_pct"], color=colors)
    ax.axvline(0, color="#111827", linewidth=1)
    ax.set_xlabel("COVE reduction vs baseload (%)")
    ax.set_title("COVE improvement from uncertainty-aware dispatch")
    fig.tight_layout()
    fig.savefig(OUT / "figure_02_scenario_cove_comparison.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-origins", type=int, default=None, help="Limit hourly origins for quick tests.")
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
    parser.add_argument("--gate-margin", type=float, default=0.0, help="Fallback to baseload-style action unless optimized forecast value beats forecast baseload by this fraction.")
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

    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(base.DATA_PATH, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df[["datetime", "power_generated", "lmp", "user_load_zonal"]].dropna().reset_index(drop=True)

    train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64("2014-01-01")))
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

    origins = np.arange(train_end, len(df))
    origins = origins[origins + HORIZON <= len(df)]
    if args.max_origins is not None:
        print(f"Quick run limited to {args.max_origins} hourly origins.", flush=True)

    print(f"Building {HORIZON}h hourly wind and price forecasts...", flush=True)
    wind_center, price_center, models = build_forecasts(df, forecast_train_end, origins)
    baseline_target_mw = float(df["power_generated"].iloc[:train_end].mean())
    needed_quantiles = sorted({q for spec in SCENARIO_SPECS.values() for q in (spec["wind_quantiles"] + spec["price_quantiles"])})
    print(
        f"Estimating {args.calibration_mode} quantiles from "
        f"{df['datetime'].iloc[residual_start]} to {df['datetime'].iloc[residual_end - 1]}: {needed_quantiles}",
        flush=True,
    )
    quantile_lookup = residual_quantiles(df, residual_start, residual_end, models, needed_quantiles, method=quantile_method)

    summary_rows = []

    if "single_recourse" in args.variants:
        print("Running single-forecast hourly replan with real-time direct-wind recourse...", flush=True)
        labels = run_single_forecast_recourse(
            df,
            origins,
            wind_center,
            price_center,
            args.max_origins,
            args.nowcast_first_hour,
            args.gate_margin,
            baseline_target_mw,
        )
        suffix = "_nowcast" if args.nowcast_first_hour else ""
        suffix += "_gated" if args.gate_margin is not None else ""
        labels.to_csv(OUT / f"single_forecast_recourse{suffix}_labels.csv", index=False)
        summary_rows.append(
            summarize(
                labels,
                f"single_forecast_recourse{suffix}",
                "current measured wind + ridge future" if args.nowcast_first_hour else "ridge_direct_24h",
                "current measured price + daily future" if args.nowcast_first_hour else "daily_persistence",
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
        )
        suffix = "_nowcast" if args.nowcast_first_hour else ""
        suffix += "_gated" if args.gate_margin is not None else ""
        labels.to_csv(OUT / f"{variant}{suffix}_labels.csv", index=False)
        spec = SCENARIO_SPECS[variant]
        summary_rows.append(
            summarize(
                labels,
                f"{variant}{suffix}",
                f"{'current measured wind + ' if args.nowcast_first_hour else ''}ridge residual scenarios {spec['wind_quantiles']}",
                f"{'current measured price + ' if args.nowcast_first_hour else ''}daily residual scenarios {spec['price_quantiles']}",
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
        "non_anticipativity": "Only the first-hour direct wind, storage charge, storage discharge, and mode are shared across scenarios; future scenario actions are recourse because the controller replans hourly.",
        "execution_rule": "The chosen storage action is executed for one hour. Direct wind to grid is adjusted using actual realized wind and grid capacity.",
        "nowcast_first_hour": bool(args.nowcast_first_hour),
        "gate_margin": args.gate_margin,
        "baseline_target_mw_from_training": baseline_target_mw,
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
