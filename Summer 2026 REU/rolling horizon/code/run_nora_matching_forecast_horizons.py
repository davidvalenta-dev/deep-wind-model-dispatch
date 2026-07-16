from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path

import gurobipy as gp
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from gurobipy import GRB


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "nora_matching_forecast_horizon_results"
DATA_PATH = REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"
NORA_PATH = Path(os.environ.get("NORA_WEEK_XLSX", "/Users/davidvalenta/Downloads/january6-12.xlsx"))

HORIZONS = [24, 48, 72, 168]
STEP_HOURS = 24
PAST_LAGS = (1, 2, 3, 6, 12, 24, 48, 168)

# Nora / CAES setup.
PS = 100.0
DURATION_HOURS = 10.0
RTE = 0.55
SQRT_RTE = math.sqrt(RTE)
CMAX = PS * DURATION_HOURS
DOD = 0.8
CMIN = CMAX * (1.0 - DOD)
SOC0 = (CMIN + CMAX) / 2.0
GRID_CAP = 249.0

# Annualized cost constants copied from strategy_model/src/util.py plus the
# CAES 100 MW, 10 h cost setting used in the previous COVE-DV decks.
FCR = 0.065
WF_CAPEX = 1968.0
WF_OPEX = 43.0
CAES_CAPEX = 2044.0
CAES_OPEX = 28.10


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
    recent_24 = values[origin - 24 : origin]
    recent_168 = values[origin - 168 : origin]
    return np.asarray(
        [
            *[values[origin - lag] for lag in PAST_LAGS],
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
    alpha: float = 10.0,
    origin_stride: int = 24,
) -> list[DirectForecastModel]:
    origins = np.arange(max(PAST_LAGS), train_end - max_horizon, origin_stride)
    base = origin_features(values, origins)
    models: list[DirectForecastModel] = []

    for lead in range(1, max_horizon + 1):
        target_indices = origins + lead - 1
        lead_fraction = np.full((len(origins), 1), lead / max_horizon)
        x = np.column_stack(
            [base, calendar_features(datetimes.iloc[target_indices]), lead_fraction]
        )
        y = values[target_indices]
        feature_mean = x.mean(axis=0)
        feature_scale = x.std(axis=0)
        feature_scale[feature_scale < 1e-8] = 1.0
        standardized = (x - feature_mean) / feature_scale
        design = np.column_stack([np.ones(len(x)), standardized])
        regularizer = alpha * np.eye(design.shape[1])
        regularizer[0, 0] = 0.0
        coefficients = np.linalg.solve(design.T @ design + regularizer, design.T @ y)
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


def make_generation_forecasts(
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


def make_weekly_price_forecasts(prices: np.ndarray, origins: np.ndarray, max_horizon: int) -> np.ndarray:
    forecasts = np.empty((len(origins), max_horizon), dtype=float)
    for row_index, origin in enumerate(origins):
        for lead_index in range(max_horizon):
            source = origin + lead_index - 168
            forecasts[row_index, lead_index] = prices[source]
    return forecasts


def forecast_metrics(
    actual: np.ndarray,
    origins: np.ndarray,
    forecasts: np.ndarray,
    variable: str,
) -> pd.DataFrame:
    rows = []
    for start_lead, end_lead in ((1, 24), (25, 48), (49, 72), (73, 168)):
        lead_indices = np.arange(start_lead - 1, end_lead)
        predicted = forecasts[:, lead_indices].reshape(-1)
        observed = np.concatenate([actual[origin + lead_indices] for origin in origins])
        errors = predicted - observed
        rows.append(
            {
                "variable": variable,
                "lead_hours": f"{start_lead}-{end_lead}",
                "rmse": float(np.sqrt(np.mean(errors**2))),
                "mae": float(np.mean(np.abs(errors))),
                "bias": float(np.mean(errors)),
                "correlation": float(np.corrcoef(predicted, observed)[0, 1]),
                "samples": int(len(errors)),
            }
        )
    return pd.DataFrame(rows)


def solve_window_nora(
    forecast_generation: np.ndarray,
    forecast_price: np.ndarray,
    start_soc: float,
    horizon: int,
) -> dict[str, np.ndarray | float]:
    """Optimize one forecast window with the Nora-matching Gurobi equations."""
    hours = len(forecast_generation)
    model = gp.Model(f"nora_forecast_horizon_{horizon}")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = 1e-9

    ch = model.addVars(hours, lb=0.0, ub=PS, name="ch")
    dh = model.addVars(hours, lb=0.0, ub=PS, name="dh")
    soc = model.addVars(hours + 1, lb=CMIN, ub=CMAX, name="SoC")
    ed = model.addVars(hours, lb=0.0, ub=GRID_CAP, name="ed")
    gw = model.addVars(hours, lb=0.0, name="gw")
    u = model.addVars(hours, vtype=GRB.BINARY, name="u")

    model.addConstr(soc[0] == float(np.clip(start_soc, CMIN, CMAX)), name="initial_soc")
    model.addConstr(soc[hours] == float(np.clip(start_soc, CMIN, CMAX)), name="terminal_soc_after_final_hour")

    for t in range(hours):
        model.addConstr(gw[t] <= float(forecast_generation[t]), name=f"direct_wind_limit_{t}")
        model.addConstr(ch[t] <= float(forecast_generation[t]) - gw[t], name=f"wind_only_charge_{t}")
        model.addConstr(ch[t] <= PS * u[t], name=f"charge_mode_{t}")
        model.addConstr(dh[t] <= PS * (1.0 - u[t]), name=f"discharge_mode_{t}")
        model.addConstr(dh[t] <= soc[t] * RTE, name=f"available_energy_nora_{t}")
        model.addConstr(ed[t] == gw[t] + dh[t], name=f"delivered_power_{t}")
        model.addConstr(soc[t + 1] == soc[t] + ch[t] - dh[t] / SQRT_RTE, name=f"soc_update_{t}")

    model.setObjective(
        gp.quicksum(float(forecast_price[t]) * ed[t] for t in range(hours)),
        GRB.MAXIMIZE,
    )
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi failed for horizon {horizon}. Status={model.Status}")

    return {
        "charge": np.array([ch[t].X for t in range(hours)], dtype=float),
        "discharge": np.array([dh[t].X for t in range(hours)], dtype=float),
        "soc": np.array([soc[t].X for t in range(hours + 1)], dtype=float),
        "delivered": np.array([ed[t].X for t in range(hours)], dtype=float),
        "direct": np.array([gw[t].X for t in range(hours)], dtype=float),
        "mode": np.array([u[t].X for t in range(hours)], dtype=float),
        "objective": float(model.ObjVal),
        "runtime": float(model.Runtime),
    }


def execute_frozen_day(
    planned: dict[str, np.ndarray | float],
    actual_generation: np.ndarray,
    start_soc: float,
    execute_len: int,
) -> dict[str, np.ndarray]:
    direct = np.zeros(execute_len, dtype=float)
    charge = np.zeros(execute_len, dtype=float)
    discharge = np.zeros(execute_len, dtype=float)
    delivered = np.zeros(execute_len, dtype=float)
    curtailment = np.zeros(execute_len, dtype=float)
    storage = np.zeros(execute_len + 1, dtype=float)
    mode = np.zeros(execute_len, dtype=float)
    storage[0] = float(np.clip(start_soc, CMIN, CMAX))

    planned_charge = planned["charge"]
    planned_discharge = planned["discharge"]
    planned_direct = planned["direct"]
    planned_mode = planned["mode"]

    for t in range(execute_len):
        generation = max(0.0, float(actual_generation[t]))
        if float(planned_mode[t]) >= 0.5:
            mode[t] = 1.0
            room = max(0.0, CMAX - storage[t])
            charge[t] = min(float(planned_charge[t]), PS, generation, room)
            remaining_wind = max(0.0, generation - charge[t])
            direct[t] = min(float(planned_direct[t]), remaining_wind, GRID_CAP)
        else:
            mode[t] = 0.0
            available_by_nora = max(0.0, storage[t] * RTE)
            available_by_soc_floor = max(0.0, (storage[t] - CMIN) * SQRT_RTE)
            discharge[t] = min(
                float(planned_discharge[t]),
                PS,
                available_by_nora,
                available_by_soc_floor,
            )
            direct[t] = min(float(planned_direct[t]), generation, max(0.0, GRID_CAP - discharge[t]))

        delivered[t] = direct[t] + discharge[t]
        curtailment[t] = max(0.0, generation - direct[t] - charge[t])
        storage[t + 1] = storage[t] + charge[t] - discharge[t] / SQRT_RTE
        storage[t + 1] = float(np.clip(storage[t + 1], CMIN, CMAX))

    return {
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "delivered": delivered,
        "curtailment": curtailment,
        "storage": storage,
        "mode": mode,
    }


def run_forecast_horizon(
    df: pd.DataFrame,
    origins: np.ndarray,
    generation_forecasts: np.ndarray,
    price_forecasts: np.ndarray,
    horizon: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual_generation = df["power_generated"].to_numpy(float)
    actual_price = df["lmp"].to_numpy(float)
    rows: list[dict] = []
    windows: list[dict] = []
    current_soc = SOC0
    started = time.perf_counter()

    for origin_row, origin in enumerate(origins):
        available_horizon = min(horizon, len(df) - origin)
        execute_len = min(STEP_HOURS, len(df) - origin)
        if execute_len <= 0:
            break

        planned_generation = generation_forecasts[origin_row, :available_horizon]
        planned_price = price_forecasts[origin_row, :available_horizon]
        planned = solve_window_nora(planned_generation, planned_price, current_soc, horizon)
        realized = execute_frozen_day(
            planned,
            actual_generation[origin : origin + execute_len],
            current_soc,
            execute_len,
        )

        for k in range(execute_len):
            i = origin + k
            rows.append(
                {
                    "hour_index": int(i),
                    "datetime": df["datetime"].iloc[i],
                    "horizon_hours": int(horizon),
                    "actual_generation_mw": float(actual_generation[i]),
                    "forecast_generation_mw": float(planned_generation[k]),
                    "actual_price": float(actual_price[i]),
                    "forecast_price": float(planned_price[k]),
                    "planned_direct_mw": float(planned["direct"][k]),
                    "planned_charge_mw": float(planned["charge"][k]),
                    "planned_discharge_mw": float(planned["discharge"][k]),
                    "realized_direct_mw": float(realized["direct"][k]),
                    "realized_charge_mw": float(realized["charge"][k]),
                    "realized_discharge_mw": float(realized["discharge"][k]),
                    "realized_delivered_mw": float(realized["delivered"][k]),
                    "realized_curtailment_mw": float(realized["curtailment"][k]),
                    "soc_start_mwh": float(realized["storage"][k]),
                    "soc_end_mwh": float(realized["storage"][k + 1]),
                    "mode_charge_binary": float(realized["mode"][k]),
                }
            )

        current_soc = float(realized["storage"][-1])
        windows.append(
            {
                "window_index": int(origin_row),
                "horizon_hours": int(horizon),
                "origin_hour": int(origin),
                "datetime": df["datetime"].iloc[origin],
                "initial_soc": float(realized["storage"][0]),
                "soc_after_frozen_day": current_soc,
                "forecast_objective": float(planned["objective"]),
                "runtime_seconds": float(planned["runtime"]),
            }
        )

        if (origin_row + 1) % 500 == 0:
            print(
                f"forecast {horizon}h: {origin_row + 1}/{len(origins)} daily windows, "
                f"SoC={current_soc:.1f}, elapsed={time.perf_counter() - started:.1f}s",
                flush=True,
            )

    return pd.DataFrame(rows), pd.DataFrame(windows)


def revenue(power: np.ndarray, price: np.ndarray) -> float:
    return float(np.sum(power * price))


def annualized_dispatch_cost() -> float:
    wind_cost = ((WF_CAPEX * GRID_CAP * 1000.0) * FCR) + (WF_OPEX * GRID_CAP * 1000.0)
    storage_cost = ((CAES_CAPEX * PS * 1000.0) * FCR) + (CAES_OPEX * PS * 1000.0)
    return wind_cost + storage_cost


def continuous_baseload(generation: np.ndarray) -> np.ndarray:
    target = float(np.mean(generation))
    storage = SOC0
    delivered = np.zeros(len(generation), dtype=float)
    for i, gen in enumerate(generation):
        gen = max(0.0, float(gen))
        if gen >= target:
            charge = min(gen - target, PS, CMAX - storage)
            direct = min(gen - charge, GRID_CAP)
            delivered[i] = direct
            storage = min(CMAX, storage + charge)
        else:
            direct = min(gen, GRID_CAP)
            needed = max(0.0, target - direct)
            discharge = min(needed, PS, storage * RTE, (storage - CMIN) * SQRT_RTE, GRID_CAP - direct)
            delivered[i] = direct + discharge
            storage = max(CMIN, storage - discharge / SQRT_RTE)
    return delivered


def check_realized_constraints(labels: pd.DataFrame) -> dict[str, float]:
    gen = labels["actual_generation_mw"].to_numpy(float)
    direct = labels["realized_direct_mw"].to_numpy(float)
    charge = labels["realized_charge_mw"].to_numpy(float)
    discharge = labels["realized_discharge_mw"].to_numpy(float)
    delivered = labels["realized_delivered_mw"].to_numpy(float)
    start = labels["soc_start_mwh"].to_numpy(float)
    end = labels["soc_end_mwh"].to_numpy(float)
    mode = labels["mode_charge_binary"].to_numpy(float)
    return {
        "max_wind_balance_violation": float(np.maximum(direct + charge - gen, 0.0).max()),
        "max_delivered_definition_violation": float(np.abs(delivered - direct - discharge).max()),
        "max_grid_violation": float(np.maximum(delivered - GRID_CAP, 0.0).max()),
        "max_charge_mode_violation": float(np.maximum(charge - PS * mode, 0.0).max()),
        "max_discharge_mode_violation": float(np.maximum(discharge - PS * (1.0 - mode), 0.0).max()),
        "max_available_energy_violation": float(np.maximum(discharge - start * RTE, 0.0).max()),
        "max_soc_update_violation": float(np.abs(end - (start + charge - discharge / SQRT_RTE)).max()),
        "max_soc_low_violation": float(np.maximum(CMIN - start, 0.0).max()),
        "max_soc_high_violation": float(np.maximum(start - CMAX, 0.0).max()),
    }


def summarize(labels_by_horizon: dict[int, pd.DataFrame]) -> pd.DataFrame:
    first = next(iter(labels_by_horizon.values()))
    actual_generation = first["actual_generation_mw"].to_numpy(float)
    actual_price = first["actual_price"].to_numpy(float)
    wind_only = np.minimum(actual_generation, GRID_CAP)
    baseload = continuous_baseload(actual_generation)
    cost = annualized_dispatch_cost()
    wind_only_revenue = revenue(wind_only, actual_price)
    baseload_revenue = revenue(baseload, actual_price)
    rows = []
    for horizon, labels in labels_by_horizon.items():
        delivered = labels["realized_delivered_mw"].to_numpy(float)
        dispatch_revenue = revenue(delivered, labels["actual_price"].to_numpy(float))
        row = {
            "method": "forecast_freeze_24h",
            "horizon_hours": int(horizon),
            "hours": int(len(labels)),
            "test_start": str(labels["datetime"].iloc[0]),
            "test_end": str(labels["datetime"].iloc[-1]),
            "wind_only_revenue": wind_only_revenue,
            "baseload_revenue": baseload_revenue,
            "forecast_dispatch_revenue": dispatch_revenue,
            "wind_only_cove_index": cost / wind_only_revenue,
            "baseload_cove_index": cost / baseload_revenue,
            "forecast_dispatch_cove_index": cost / dispatch_revenue,
            "revenue_gain_vs_baseload_pct": (dispatch_revenue / baseload_revenue - 1.0) * 100.0,
            "cove_reduction_vs_baseload_pct": (1.0 - (cost / dispatch_revenue) / (cost / baseload_revenue)) * 100.0,
            "final_soc": float(labels["soc_end_mwh"].iloc[-1]),
            "min_soc": float(min(labels["soc_start_mwh"].min(), labels["soc_end_mwh"].min())),
            "max_soc": float(max(labels["soc_start_mwh"].max(), labels["soc_end_mwh"].max())),
            "sum_charge_mwh": float(labels["realized_charge_mw"].sum()),
            "sum_discharge_mwh": float(labels["realized_discharge_mw"].sum()),
            "sum_curtailment_mwh": float(labels["realized_curtailment_mw"].sum()),
        }
        row.update(check_realized_constraints(labels))
        rows.append(row)
    return pd.DataFrame(rows)


def validate_nora_week() -> dict[str, float]:
    df = pd.read_excel(NORA_PATH)
    result = solve_window_nora(
        df["Generation (MW)"].to_numpy(float),
        df["Price ($/MWh)"].to_numpy(float),
        SOC0,
        168,
    )
    return {
        "nora_matching_revenue": float(result["objective"]),
        "initial_soc": float(result["soc"][0]),
        "terminal_soc_start_last_hour": float(result["soc"][167]),
        "soc_after_last_hour": float(result["soc"][168]),
        "min_soc": float(result["soc"].min()),
        "max_soc": float(result["soc"].max()),
    }


def make_figures(
    summary: pd.DataFrame,
    metrics: pd.DataFrame,
    labels_by_horizon: dict[int, pd.DataFrame],
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    colors = ["#2563eb", "#0f766e", "#b45309", "#7c3aed"]

    ordered = summary.sort_values("horizon_hours")
    labels = [f"{int(h)}h" for h in ordered["horizon_hours"]]

    fig, ax = plt.subplots(figsize=(9, 5), dpi=220)
    bars = ax.bar(labels, ordered["cove_reduction_vs_baseload_pct"], color=colors)
    best_index = int(np.argmax(ordered["cove_reduction_vs_baseload_pct"].to_numpy()))
    bars[best_index].set_color("#16a34a")
    for bar, value in zip(bars, ordered["cove_reduction_vs_baseload_pct"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}%", ha="center", va="bottom", fontweight="bold")
    ax.set_ylabel("COVE reduction vs baseload (%)")
    ax.set_title("Realistic forecast dispatch: 24h freeze, chronological SoC")
    fig.tight_layout()
    fig.savefig(OUT / "figure_01_forecast_cove_reduction_by_horizon.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5), dpi=220)
    bars = ax.bar(labels, ordered["forecast_dispatch_revenue"] / 1e6, color=colors)
    bars[best_index].set_color("#16a34a")
    ax.axhline(ordered["baseload_revenue"].iloc[0] / 1e6, linestyle="--", color="#64748b", label="Baseload")
    for bar, value in zip(bars, ordered["forecast_dispatch_revenue"] / 1e6):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}M", ha="center", va="bottom", fontweight="bold")
    ax.set_ylabel("Realized revenue/value ($ millions)")
    ax.set_title("Scored with actual wind and actual price")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figure_02_forecast_revenue_by_horizon.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5), dpi=220)
    ax.plot(ordered["horizon_hours"], ordered["forecast_dispatch_cove_index"], marker="o", linewidth=2.5, color="#2563eb", label="Forecast dispatch")
    ax.axhline(ordered["baseload_cove_index"].iloc[0], linestyle="--", color="#64748b", label="Baseload")
    ax.set_xlabel("Planning horizon (hours)")
    ax.set_ylabel("COVE index (lower is better)")
    ax.set_title("Lower COVE means better price-weighted energy value")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figure_03_forecast_cove_index_by_horizon.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), dpi=220)
    for axis, variable, ylabel in (
        (axes[0], "generation_mw", "Wind forecast RMSE (MW)"),
        (axes[1], "price_raw", "Price forecast RMSE ($/MWh)"),
    ):
        selected = metrics[metrics["variable"] == variable]
        axis.plot(selected["lead_hours"], selected["rmse"], marker="o", linewidth=2.5, color="#2563eb")
        axis.set_ylabel(ylabel)
        axis.set_xlabel("Forecast lead")
    fig.suptitle("Forecast errors grow as the model looks farther ahead", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "figure_04_forecast_error_by_lead.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    best_horizon = int(ordered.sort_values("cove_reduction_vs_baseload_pct", ascending=False).iloc[0]["horizon_hours"])
    best = labels_by_horizon[best_horizon].copy()
    best["datetime"] = pd.to_datetime(best["datetime"])
    start = pd.Timestamp("2020-01-06 00:00:00")
    end = start + pd.Timedelta(hours=168)
    week = best[(best["datetime"] >= start) & (best["datetime"] < end)].copy()
    if len(week) < 24:
        week = best.iloc[:168].copy()

    fig, axes = plt.subplots(5, 1, figsize=(12, 10.5), sharex=True, dpi=220)
    axes[0].plot(week["datetime"], week["actual_generation_mw"], color="#0f172a", label="Actual")
    axes[0].plot(week["datetime"], week["forecast_generation_mw"], color="#38bdf8", alpha=0.9, label="Forecast")
    axes[0].set_ylabel("Wind MW")
    axes[0].legend(loc="upper right", ncol=2, frameon=False)
    axes[1].plot(week["datetime"], week["actual_price"], color="#581c87", label="Actual")
    axes[1].plot(week["datetime"], week["forecast_price"], color="#c084fc", alpha=0.9, label="Forecast")
    axes[1].set_ylabel("Price")
    axes[1].legend(loc="upper right", ncol=2, frameon=False)
    axes[2].plot(week["datetime"], week["realized_delivered_mw"], color="#16a34a", label="Delivered")
    axes[2].plot(week["datetime"], week["realized_direct_mw"], color="#64748b", alpha=0.8, label="Direct")
    axes[2].set_ylabel("MW")
    axes[2].legend(loc="upper right", ncol=2, frameon=False)
    net = week["realized_discharge_mw"] - week["realized_charge_mw"]
    axes[3].bar(week["datetime"], net, color=np.where(net >= 0, "#dc2626", "#2563eb"), width=0.03)
    axes[3].axhline(0, color="#111827", linewidth=0.8)
    axes[3].set_ylabel("Net storage MW")
    axes[4].plot(week["datetime"], week["soc_start_mwh"], color="#ea580c")
    axes[4].axhline(CMIN, color="#64748b", linestyle="--", linewidth=0.9)
    axes[4].axhline(CMAX, color="#64748b", linestyle="--", linewidth=0.9)
    axes[4].set_ylabel("SoC MWh")
    axes[4].set_xlabel("Time")
    fig.suptitle(f"Example week: forecast plan is frozen for 24h, best horizon = {best_horizon}h", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "figure_05_example_week_forecast_freeze.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=220)
    for color, horizon in zip(colors, HORIZONS):
        labels_df = labels_by_horizon[horizon].iloc[: 24 * 90]
        ax.plot(np.arange(len(labels_df)) / 24.0, labels_df["soc_start_mwh"], label=f"{horizon}h", color=color, linewidth=1.5)
    ax.set_xlabel("Days from test start")
    ax.set_ylabel("SoC (MWh)")
    ax.set_title("Chronological battery carryover, first 90 days")
    ax.legend(frameon=False, ncol=4)
    fig.tight_layout()
    fig.savefig(OUT / "figure_06_soc_carryover_first_90_days.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    yearly_rows = []
    for horizon, labels in labels_by_horizon.items():
        tmp = labels.copy()
        tmp["year"] = pd.to_datetime(tmp["datetime"]).dt.year
        for year, group in tmp.groupby("year"):
            actual_price = group["actual_price"].to_numpy(float)
            actual_generation = group["actual_generation_mw"].to_numpy(float)
            baseload = continuous_baseload(actual_generation)
            dispatch = group["realized_delivered_mw"].to_numpy(float)
            base_rev = revenue(baseload, actual_price)
            dispatch_rev = revenue(dispatch, actual_price)
            yearly_rows.append(
                {
                    "year": int(year),
                    "horizon_hours": int(horizon),
                    "revenue_gain_vs_baseload_pct": (dispatch_rev / base_rev - 1.0) * 100.0,
                    "cove_reduction_vs_baseload_pct": (1.0 - base_rev / dispatch_rev) * 100.0,
                }
            )
    yearly = pd.DataFrame(yearly_rows)
    yearly.to_csv(OUT / "forecast_yearly_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=220)
    for color, horizon in zip(colors, HORIZONS):
        selected = yearly[yearly["horizon_hours"] == horizon]
        ax.plot(selected["year"], selected["cove_reduction_vs_baseload_pct"], marker="o", label=f"{horizon}h", color=color)
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.set_xlabel("Year")
    ax.set_ylabel("COVE reduction vs baseload (%)")
    ax.set_title("Year-by-year realized performance")
    ax.legend(frameon=False, ncol=4)
    fig.tight_layout()
    fig.savefig(OUT / "figure_07_yearly_forecast_cove_reduction.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Validating Nora one-week convention...", flush=True)
    nora_check = validate_nora_week()
    print(nora_check, flush=True)

    df = pd.read_csv(DATA_PATH, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df[["datetime", "power_generated", "lmp", "user_load_zonal"]].dropna().reset_index(drop=True)
    train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64("2014-01-01")))
    max_horizon = max(HORIZONS)
    origins = np.arange(train_end, len(df), STEP_HOURS)
    origins = origins[origins + max_horizon <= len(df)]

    generation = df["power_generated"].to_numpy(float)
    price = df["lmp"].to_numpy(float)
    print(
        f"Training forecasts on {df['datetime'].iloc[0]} through {df['datetime'].iloc[train_end - 1]}",
        flush=True,
    )
    print(
        f"Backtesting {len(origins)} daily origins from {df['datetime'].iloc[origins[0]]} "
        f"through {df['datetime'].iloc[origins[-1] + max_horizon - 1]}",
        flush=True,
    )

    generation_models = fit_direct_models(
        generation,
        df["datetime"],
        train_end,
        max_horizon,
        0.0,
        max(float(generation[:train_end].max()), GRID_CAP),
        alpha=10.0,
        origin_stride=24,
    )
    generation_forecasts = make_generation_forecasts(generation, df["datetime"], origins, generation_models)
    price_forecasts = make_weekly_price_forecasts(price, origins, max_horizon)
    np.savez_compressed(
        OUT / "forecast_matrices.npz",
        origins=origins,
        generation_forecast=generation_forecasts,
        price_forecast=price_forecasts,
    )

    metrics = pd.concat(
        [
            forecast_metrics(generation, origins, generation_forecasts, "generation_mw"),
            forecast_metrics(price, origins, price_forecasts, "price_raw"),
        ],
        ignore_index=True,
    )
    metrics.to_csv(OUT / "forecast_accuracy_by_lead.csv", index=False)

    labels_by_horizon: dict[int, pd.DataFrame] = {}
    window_rows: list[pd.DataFrame] = []
    for horizon in HORIZONS:
        print(f"\nRunning forecast horizon {horizon}h", flush=True)
        labels, windows = run_forecast_horizon(
            df,
            origins,
            generation_forecasts,
            price_forecasts,
            horizon,
        )
        labels.to_csv(OUT / f"forecast_freeze_dispatch_{horizon}h.csv", index=False)
        windows.to_csv(OUT / f"forecast_freeze_windows_{horizon}h.csv", index=False)
        labels_by_horizon[horizon] = labels
        window_rows.append(windows)

    summary = summarize(labels_by_horizon)
    summary.to_csv(OUT / "forecast_freeze_summary.csv", index=False)
    pd.concat(window_rows, ignore_index=True).to_csv(OUT / "forecast_freeze_all_windows.csv", index=False)

    metadata = {
        "data_path": str(DATA_PATH),
        "nora_validation": nora_check,
        "forecast_training_period": [str(df["datetime"].iloc[0]), str(df["datetime"].iloc[train_end - 1])],
        "forecast_backtest_period": [
            str(df["datetime"].iloc[origins[0]]),
            str(df["datetime"].iloc[origins[-1] + max_horizon - 1]),
        ],
        "wind_forecast": "direct ridge regression using past lags and calendar features",
        "price_forecast": "causal weekly persistence: same hour from one week earlier",
        "freeze_rule": "optimize full horizon from forecasts, execute only first 24 hours, carry realized SoC forward",
        "storage_power_mw": PS,
        "storage_duration_hours": DURATION_HOURS,
        "capacity_mwh": CMAX,
        "cmin_mwh": CMIN,
        "soc0_mwh": SOC0,
        "rte": RTE,
        "grid_cap_mw": GRID_CAP,
        "soc_convention": "N+1 SoC states with terminal equality after the final optimized hour",
        "soc_update": "SoC[t+1] = SoC[t] + ch[t] - dh[t]/sqrt(RTE)",
        "available_energy": "dh[t] <= SoC[t] * RTE plus realized replay also protects Cmin",
    }
    (OUT / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2))
    make_figures(summary, metrics, labels_by_horizon)

    print("\nForecast accuracy by lead")
    print(metrics.to_string(index=False))
    print("\nForecast freeze dispatch summary")
    print(
        summary[
            [
                "horizon_hours",
                "forecast_dispatch_revenue",
                "forecast_dispatch_cove_index",
                "cove_reduction_vs_baseload_pct",
                "final_soc",
            ]
        ].to_string(index=False)
    )
    max_violation = max(
        float(summary[column].max())
        for column in summary.columns
        if column.startswith("max_") and column.endswith("_violation")
    )
    best = summary.sort_values("cove_reduction_vs_baseload_pct", ascending=False).iloc[0]
    print(f"\nBest forecast horizon: {int(best['horizon_hours'])}h")
    print(f"Maximum realized constraint violation: {max_violation:.3e}")
    print(f"Saved outputs to {OUT}")


if __name__ == "__main__":
    main()
