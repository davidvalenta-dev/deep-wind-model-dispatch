from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import gurobipy as gp
import numpy as np
import pandas as pd
from gurobipy import GRB


PAST_LAGS = (1, 2, 3, 6, 12, 24, 48, 168)
ARCHITECTURES = {
    "A": {"power_mw": 100.0, "duration_h": 6.0},
    "B": {"power_mw": 200.0, "duration_h": 3.0},
    "C": {"power_mw": 100.0, "duration_h": 10.0},
}


@dataclass
class ForecastModel:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    coefficients: np.ndarray
    target_min: float
    target_max: float

    def predict(self, features: np.ndarray) -> float:
        z = (features - self.feature_mean) / self.feature_scale
        x = np.concatenate(([1.0], z))
        return float(np.clip(x @ self.coefficients, self.target_min, self.target_max))


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def parse_power_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    dates = df["Date"].astype(str)
    times = df["Time"].astype(int).astype(str).str.zfill(4)
    dt = pd.to_datetime(dates + times, format="%Y%m%d%H%M")
    out = pd.DataFrame({"timestamp": dt, "actual_wind_MW": df["Power"].astype(float)})
    return out


def parse_raw_lmp_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    local = df["interval_start_local"].astype(str).str.slice(0, 19)
    dt = pd.to_datetime(local, format="%Y-%m-%dT%H:%M:%S")
    out = pd.DataFrame(
        {
            "timestamp": dt,
            "actual_raw_price_USD_per_MWh": df["lmp"].astype(float),
            "lmp_location": df["location"].astype(str),
        }
    )
    return out


def load_b6_data(repo: Path) -> tuple[pd.DataFrame, dict]:
    power_path = repo / "data" / "processed" / "pyron_power.csv"
    price_path = repo / "data" / "raw" / "prices" / "12cfb125-8fa9-4401-8b0f-9d928544b721.csv"
    older_combined_path = repo / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"

    power = parse_power_file(power_path)
    power_2020 = power[power["timestamp"].dt.year == 2020].sort_values("timestamp").reset_index(drop=True)

    raw_price = pd.read_csv(price_path)
    raw_price_2020 = raw_price[raw_price["interval_start_local"].astype(str).str.startswith("2020")].copy()
    raw_price_2020 = raw_price_2020.sort_values("interval_start_utc").reset_index(drop=True)

    if len(power_2020) != len(raw_price_2020):
        raise RuntimeError(
            f"Power/price row mismatch after 2020 filtering: power={len(power_2020)}, price={len(raw_price_2020)}"
        )

    # ERCOT local interval labels include daylight-saving-time behavior: one spring
    # hour is skipped and one fall hour repeats. Pyron power is stored as a simple
    # 8784-row hourly 2020 series. For this frozen B6 package, align the two raw
    # 2020 series by chronological row order and keep the simple Pyron power
    # timestamp as the output timestamp.
    expected = pd.date_range("2020-01-01 00:00:00", "2020-12-31 23:00:00", freq="h")
    source_power_missing = expected.difference(pd.DatetimeIndex(power_2020["timestamp"]))
    source_power_duplicates = int(power_2020["timestamp"].duplicated().sum())

    df = power_2020.copy()
    df["source_power_timestamp"] = df["timestamp"]
    df["timestamp"] = expected
    df["actual_raw_price_USD_per_MWh"] = raw_price_2020["lmp"].astype(float)
    df["lmp_location"] = raw_price_2020["location"].astype(str)
    df["raw_lmp_interval_start_local"] = raw_price_2020["interval_start_local"].astype(str)
    df["raw_lmp_interval_start_utc"] = raw_price_2020["interval_start_utc"].astype(str)

    missing = expected.difference(pd.DatetimeIndex(df["timestamp"]))
    duplicates = int(df["timestamp"].duplicated().sum())
    if len(df) != 8784 or len(missing) or duplicates:
        raise RuntimeError(
            f"2020 data coverage failed: rows={len(df)}, missing={list(missing)}, duplicates={duplicates}"
        )

    older_combined_2020_rows = None
    older_combined_missing = []
    if older_combined_path.exists():
        older = pd.read_csv(older_combined_path, usecols=["datetime"])
        older_ts = pd.to_datetime(older["datetime"], errors="coerce")
        older_2020 = older_ts[older_ts.dt.year == 2020]
        older_combined_2020_rows = int(len(older_2020))
        older_combined_missing = [str(x) for x in expected.difference(pd.DatetimeIndex(older_2020))]

    audit = {
        "power_input_file": str(power_path),
        "raw_lmp_input_file": str(price_path),
        "older_combined_input_file_not_used": str(older_combined_path),
        "rows_2020": int(len(df)),
        "complete_2020_power_rows": int(len(power_2020)),
        "complete_2020_raw_lmp_rows": int(len(raw_price_2020)),
        "older_combined_2020_rows": older_combined_2020_rows,
        "older_combined_missing_hours": older_combined_missing,
        "first_timestamp": str(df["timestamp"].iloc[0]),
        "last_timestamp": str(df["timestamp"].iloc[-1]),
        "missing_hours": [str(x) for x in missing],
        "duplicate_timestamps": duplicates,
        "lmp_location": sorted(df["lmp_location"].unique().tolist()),
        "source_power_missing_local_labels": [str(x) for x in source_power_missing],
        "source_power_duplicate_local_labels": source_power_duplicates,
        "alignment_note": "Power and raw LMP are aligned by chronological 2020 row order onto a continuous 8784-hour 2020 output index because raw local interval labels include DST skip/repeat behavior.",
        "actual_wind_MW_min": float(df["actual_wind_MW"].min()),
        "actual_wind_MW_max": float(df["actual_wind_MW"].max()),
        "raw_lmp_min": float(df["actual_raw_price_USD_per_MWh"].min()),
        "raw_lmp_max": float(df["actual_raw_price_USD_per_MWh"].max()),
    }
    return df.drop(columns=["lmp_location", "source_power_timestamp", "raw_lmp_interval_start_local", "raw_lmp_interval_start_utc"]), audit


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
    timestamps: pd.Series,
    train_end: int,
    max_horizon: int,
    alpha: float,
) -> list[ForecastModel]:
    origins = np.arange(max(PAST_LAGS), train_end - max_horizon)
    base = origin_features(values, origins)
    models: list[ForecastModel] = []
    target_min = float(values[:train_end].min())
    target_max = float(values[:train_end].max())

    for lead in range(1, max_horizon + 1):
        target_indices = origins + lead - 1
        lead_fraction = np.full((len(origins), 1), lead / max_horizon)
        x_raw = np.column_stack(
            [base, calendar_features(timestamps.iloc[target_indices]), lead_fraction]
        )
        y = values[target_indices]
        mean = x_raw.mean(axis=0)
        scale = x_raw.std(axis=0)
        scale[scale < 1e-8] = 1.0
        x_std = (x_raw - mean) / scale
        design = np.column_stack([np.ones(len(x_std)), x_std])
        regularizer = alpha * np.eye(design.shape[1])
        regularizer[0, 0] = 0.0
        coef = np.linalg.solve(design.T @ design + regularizer, design.T @ y)
        models.append(ForecastModel(mean, scale, coef, target_min, target_max))
    return models


def make_forecasts(
    values: np.ndarray,
    timestamps: pd.Series,
    origins: np.ndarray,
    models: list[ForecastModel],
) -> np.ndarray:
    max_horizon = len(models)
    out = np.empty((len(origins), max_horizon), dtype=float)
    for row, origin in enumerate(origins):
        base = single_origin_features(values, int(origin))
        start_time = pd.Timestamp(timestamps.iloc[origin])
        cals = calendar_features(pd.date_range(start_time, periods=max_horizon, freq="h"))
        for lead_index, model in enumerate(models):
            features = np.concatenate([base, cals[lead_index], [(lead_index + 1) / max_horizon]])
            out[row, lead_index] = model.predict(features)
    return out


def prepare_forecast_frame(repo: Path, b6_2020: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, dict]:
    history_path = repo / "data" / "processed" / "dataset_2018-21.csv"
    history = pd.read_csv(history_path, parse_dates=["datetime"])
    history = history.sort_values("datetime").reset_index(drop=True)
    history["power_cf"] = (
        history["power_cf"]
        .astype(float)
        .interpolate(limit_direction="both")
        .ffill()
        .bfill()
    )
    history["lmp"] = history["lmp"].astype(float).interpolate(limit_direction="both").ffill().bfill()
    history["actual_wind_MW"] = history["power_cf"].astype(float) * 249.0
    history["actual_raw_price_USD_per_MWh"] = history["lmp"].astype(float)
    history = history[["datetime", "actual_wind_MW", "actual_raw_price_USD_per_MWh"]]
    history = history.rename(columns={"datetime": "timestamp"})

    train_end = int((history["timestamp"] < "2020-01-01").sum())
    combined = pd.concat(
        [history[history["timestamp"] < "2020-01-01"], b6_2020],
        ignore_index=True,
    ).sort_values("timestamp").reset_index(drop=True)
    test_start = train_end
    origins = np.arange(test_start, len(combined), 24)

    wind_values = combined["actual_wind_MW"].to_numpy(dtype=float)
    price_values = combined["actual_raw_price_USD_per_MWh"].to_numpy(dtype=float)
    wind_models = fit_direct_models(wind_values, combined["timestamp"], train_end, horizon, alpha=10.0)
    price_models = fit_direct_models(price_values, combined["timestamp"], train_end, horizon, alpha=50.0)
    wind_fcst = make_forecasts(wind_values, combined["timestamp"], origins, wind_models)
    price_fcst = make_forecasts(price_values, combined["timestamp"], origins, price_models)

    meta = {
        "forecast_history_file": str(history_path),
        "forecast_train_start": str(combined["timestamp"].iloc[0]),
        "forecast_train_end_exclusive": "2020-01-01 00:00:00",
        "forecast_test_year": 2020,
        "forecast_model": "existing-style causal ridge lag/calendar direct forecast",
        "forecast_origin_count": int(len(origins)),
        "forecast_horizon_hours": int(horizon),
        "wind_forecast_alpha": 10.0,
        "price_forecast_alpha": 50.0,
    }
    return combined.iloc[test_start:].reset_index(drop=True), {
        "origins": (origins - test_start).tolist(),
        "wind_forecasts": wind_fcst.tolist(),
        "price_forecasts": price_fcst.tolist(),
        "metadata": meta,
    }


def solve_dispatch_window(
    generation: np.ndarray,
    price: np.ndarray,
    power_mw: float,
    capacity_mwh: float,
    grid_cap_mw: float,
    rte: float,
    min_soc_frac: float,
    max_soc_frac: float,
    initial_soc: float,
    terminal_equal_initial: bool,
    terminal_soc_value: float | None,
    mip_gap: float,
    time_limit: float | None,
) -> dict:
    hours = len(generation)
    min_soc = capacity_mwh * min_soc_frac
    max_soc = capacity_mwh * max_soc_frac
    start_soc = float(np.clip(initial_soc, min_soc, max_soc))

    model = gp.Model("b6_dispatch")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = mip_gap
    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    direct = model.addVars(hours, lb=0.0, name="direct")
    charge = model.addVars(hours, lb=0.0, ub=power_mw, name="charge")
    discharge = model.addVars(hours, lb=0.0, ub=power_mw, name="discharge")
    delivered = model.addVars(hours, lb=0.0, ub=grid_cap_mw, name="delivered")
    soc = model.addVars(hours + 1, lb=min_soc, ub=max_soc, name="soc")
    mode = model.addVars(hours, vtype=GRB.BINARY, name="mode_charge")

    model.addConstr(soc[0] == start_soc, name="initial_soc")
    if terminal_soc_value is not None:
        target = float(np.clip(terminal_soc_value, min_soc, max_soc))
        model.addConstr(soc[hours] == target, name="terminal_soc_target")
    elif terminal_equal_initial:
        model.addConstr(soc[hours] == start_soc, name="terminal_soc_equal_initial")

    for t in range(hours):
        gen_t = max(float(generation[t]), 0.0)
        model.addConstr(direct[t] <= gen_t, name=f"direct_wind_{t}")
        model.addConstr(charge[t] <= gen_t - direct[t], name=f"wind_only_charge_{t}")
        model.addConstr(charge[t] <= power_mw * mode[t], name=f"charge_mode_{t}")
        model.addConstr(discharge[t] <= power_mw * (1 - mode[t]), name=f"discharge_mode_{t}")
        model.addConstr(discharge[t] / rte <= soc[t] - min_soc, name=f"available_energy_{t}")
        model.addConstr(delivered[t] == direct[t] + discharge[t], name=f"delivered_balance_{t}")
        model.addConstr(soc[t + 1] == soc[t] + charge[t] - discharge[t] / rte, name=f"soc_update_{t}")

    model.setObjective(gp.quicksum(float(price[t]) * delivered[t] for t in range(hours)), GRB.MAXIMIZE)
    started = time.perf_counter()
    model.optimize()
    runtime = time.perf_counter() - started
    status = int(model.Status)
    status_name = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(status, str(status))
    if status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        raise RuntimeError(f"Gurobi failed with status {status_name}")
    if status == GRB.TIME_LIMIT and model.SolCount == 0:
        raise RuntimeError("Gurobi hit time limit without a feasible solution")

    return {
        "direct": np.array([direct[t].X for t in range(hours)], dtype=float),
        "charge": np.array([charge[t].X for t in range(hours)], dtype=float),
        "discharge": np.array([discharge[t].X for t in range(hours)], dtype=float),
        "delivered": np.array([delivered[t].X for t in range(hours)], dtype=float),
        "soc": np.array([soc[t].X for t in range(hours + 1)], dtype=float),
        "mode": np.array([mode[t].X for t in range(hours)], dtype=float),
        "objective": float(model.ObjVal),
        "runtime": float(runtime),
        "status": status_name,
        "mip_gap": float(model.MIPGap) if model.SolCount else None,
    }


def execute_plan(
    solution: dict,
    actual_generation: np.ndarray,
    initial_soc: float,
    power_mw: float,
    capacity_mwh: float,
    grid_cap_mw: float,
    rte: float,
    min_soc_frac: float,
    max_soc_frac: float,
) -> dict:
    n = len(actual_generation)
    min_soc = capacity_mwh * min_soc_frac
    max_soc = capacity_mwh * max_soc_frac
    direct = np.zeros(n)
    charge = np.zeros(n)
    discharge = np.zeros(n)
    delivered = np.zeros(n)
    curtailed = np.zeros(n)
    soc = np.zeros(n + 1)
    mode = np.zeros(n)
    soc[0] = float(np.clip(initial_soc, min_soc, max_soc))
    for t in range(n):
        gen = max(float(actual_generation[t]), 0.0)
        planned_direct = float(solution["direct"][t])
        planned_charge = float(solution["charge"][t])
        planned_discharge = float(solution["discharge"][t])
        if planned_charge > planned_discharge:
            mode[t] = 1.0
            room = max(0.0, max_soc - soc[t])
            charge[t] = min(planned_charge, power_mw, gen, room)
        else:
            available = max(0.0, (soc[t] - min_soc) * rte)
            discharge[t] = min(planned_discharge, power_mw, available)
        wind_after_charge = max(0.0, gen - charge[t])
        direct[t] = min(planned_direct, wind_after_charge, max(0.0, grid_cap_mw - discharge[t]))
        delivered[t] = direct[t] + discharge[t]
        curtailed[t] = max(0.0, gen - direct[t] - charge[t])
        soc[t + 1] = soc[t] + charge[t] - discharge[t] / rte
    return {
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "delivered": delivered,
        "curtailed": curtailed,
        "soc": soc,
        "mode": mode,
    }


def qa_checks(
    labels: pd.DataFrame,
    power_mw: float,
    capacity_mwh: float,
    grid_cap_mw: float,
    rte: float,
    min_soc_frac: float,
    max_soc_frac: float,
    annual_terminal_soc_mwh: float,
) -> dict:
    min_soc = capacity_mwh * min_soc_frac
    max_soc = capacity_mwh * max_soc_frac
    gen = labels["actual_wind_MW"].to_numpy(float)
    direct = labels["direct_wind_MW"].to_numpy(float)
    charge = labels["charge_MW"].to_numpy(float)
    discharge = labels["discharge_MW"].to_numpy(float)
    delivered = labels["delivered_power_MW"].to_numpy(float)
    start = labels["SOC_start_MWh"].to_numpy(float)
    end = labels["SOC_end_MWh"].to_numpy(float)
    simultaneous = np.minimum(charge, discharge)
    revenue_diff = abs(float(labels["hourly_raw_revenue_USD"].sum()) - float(np.sum(delivered * labels["actual_raw_price_USD_per_MWh"].to_numpy(float))))
    final_soc_error = abs(float(end[-1]) - float(annual_terminal_soc_mwh))
    return {
        "soc_below_min_violation_count": int(np.sum(start < min_soc - 1e-6) + np.sum(end < min_soc - 1e-6)),
        "soc_above_max_violation_count": int(np.sum(start > max_soc + 1e-6) + np.sum(end > max_soc + 1e-6)),
        "simultaneous_charge_discharge_violation_count": int(np.sum(simultaneous > 1e-6)),
        "wind_only_charging_violation_count": int(np.sum(direct + charge > gen + 1e-6)),
        "grid_export_violation_count": int(np.sum(delivered > grid_cap_mw + 1e-6)),
        "energy_availability_violation_count": int(np.sum(discharge / rte > (start - min_soc) + 1e-6)),
        "soc_update_max_abs_error": float(np.max(np.abs(end - (start + charge - discharge / rte)))),
        "delivered_balance_max_abs_error": float(np.max(np.abs(delivered - direct - discharge))),
        "hourly_revenue_sum_error_USD": float(revenue_diff),
        "annual_terminal_soc_target_mwh": float(annual_terminal_soc_mwh),
        "annual_terminal_soc_abs_error_mwh": float(final_soc_error),
        "annual_terminal_soc_violation_count": int(final_soc_error > 1e-5),
        "row_count": int(len(labels)),
        "first_timestamp": str(labels["timestamp"].iloc[0]),
        "last_timestamp": str(labels["timestamp"].iloc[-1]),
    }


def discharge_loss(discharge_mwh: float, rte: float) -> float:
    """Energy removed from storage but not delivered because RTE is below 1."""
    return discharge_mwh * (1.0 / rte - 1.0)


def run_oracle(df: pd.DataFrame, arch_id: str, cfg: dict) -> tuple[pd.DataFrame, dict]:
    solution = solve_dispatch_window(
        df["actual_wind_MW"].to_numpy(float),
        df["actual_raw_price_USD_per_MWh"].to_numpy(float),
        cfg["power_mw"],
        cfg["capacity_mwh"],
        cfg["grid_cap_mw"],
        cfg["rte"],
        cfg["min_soc_frac"],
        cfg["max_soc_frac"],
        cfg["initial_soc_mwh"],
        terminal_equal_initial=True,
        terminal_soc_value=cfg["annual_terminal_soc_mwh"],
        mip_gap=cfg["mip_gap"],
        time_limit=cfg["oracle_time_limit_seconds"],
    )
    labels = pd.DataFrame(
        {
            "timestamp": df["timestamp"],
            "actual_wind_MW": df["actual_wind_MW"],
            "actual_raw_price_USD_per_MWh": df["actual_raw_price_USD_per_MWh"],
            "forecast_wind_MW": df["actual_wind_MW"],
            "forecast_price_USD_per_MWh": df["actual_raw_price_USD_per_MWh"],
            "direct_wind_MW": solution["direct"],
            "charge_MW": solution["charge"],
            "discharge_MW": solution["discharge"],
            "delivered_power_MW": solution["delivered"],
            "SOC_start_MWh": solution["soc"][:-1],
            "SOC_end_MWh": solution["soc"][1:],
            "curtailed_wind_MW": np.maximum(0.0, df["actual_wind_MW"].to_numpy(float) - solution["direct"] - solution["charge"]),
            "hourly_raw_revenue_USD": solution["delivered"] * df["actual_raw_price_USD_per_MWh"].to_numpy(float),
            "solver_status_or_window_id": solution["status"],
        }
    )
    summary = summarize(labels, arch_id, "ORACLE", cfg, solution["runtime"], solution["status"], solution["mip_gap"])
    return labels, summary


def run_causal(df: pd.DataFrame, forecasts: dict, arch_id: str, cfg: dict) -> tuple[pd.DataFrame, dict]:
    origins = np.asarray(forecasts["origins"], dtype=int)
    wind_fcst = np.asarray(forecasts["wind_forecasts"], dtype=float)
    price_fcst = np.asarray(forecasts["price_forecasts"], dtype=float)
    rows = []
    current_soc = cfg["initial_soc_mwh"]
    runtime = 0.0
    statuses = []
    gaps = []
    actual_generation = df["actual_wind_MW"].to_numpy(float)
    actual_price = df["actual_raw_price_USD_per_MWh"].to_numpy(float)

    for window_id, origin in enumerate(origins):
        available_horizon = min(cfg["causal_horizon_hours"], len(df) - origin)
        execute_len = min(cfg["execution_step_hours"], len(df) - origin)
        if execute_len <= 0:
            break
        is_final_execution = origin + execute_len >= len(df)
        solution = solve_dispatch_window(
            wind_fcst[window_id, :available_horizon],
            price_fcst[window_id, :available_horizon],
            cfg["power_mw"],
            cfg["capacity_mwh"],
            cfg["grid_cap_mw"],
            cfg["rte"],
            cfg["min_soc_frac"],
            cfg["max_soc_frac"],
            current_soc,
            terminal_equal_initial=not is_final_execution,
            terminal_soc_value=cfg["annual_terminal_soc_mwh"] if is_final_execution else None,
            mip_gap=cfg["mip_gap"],
            time_limit=cfg["causal_window_time_limit_seconds"],
        )
        runtime += solution["runtime"]
        statuses.append(solution["status"])
        if solution["mip_gap"] is not None:
            gaps.append(solution["mip_gap"])
        realized = execute_plan(
            solution,
            actual_generation[origin : origin + execute_len],
            current_soc,
            cfg["power_mw"],
            cfg["capacity_mwh"],
            cfg["grid_cap_mw"],
            cfg["rte"],
            cfg["min_soc_frac"],
            cfg["max_soc_frac"],
        )
        for k in range(execute_len):
            hour = origin + k
            delivered = realized["delivered"][k]
            rows.append(
                {
                    "timestamp": df["timestamp"].iloc[hour],
                    "actual_wind_MW": actual_generation[hour],
                    "actual_raw_price_USD_per_MWh": actual_price[hour],
                    "forecast_wind_MW": wind_fcst[window_id, k],
                    "forecast_price_USD_per_MWh": price_fcst[window_id, k],
                    "direct_wind_MW": realized["direct"][k],
                    "charge_MW": realized["charge"][k],
                    "discharge_MW": realized["discharge"][k],
                    "delivered_power_MW": delivered,
                    "SOC_start_MWh": realized["soc"][k],
                    "SOC_end_MWh": realized["soc"][k + 1],
                    "curtailed_wind_MW": realized["curtailed"][k],
                    "hourly_raw_revenue_USD": delivered * actual_price[hour],
                    "solver_status_or_window_id": f"window_{window_id:03d}_{solution['status']}",
                }
            )
        current_soc = float(realized["soc"][execute_len])
        print(f"{arch_id}_CAUSAL window {window_id + 1}/{len(origins)} complete; SoC={current_soc:.3f}", flush=True)
    labels = pd.DataFrame(rows)
    status = "OPTIMAL" if set(statuses) == {"OPTIMAL"} else ",".join(sorted(set(statuses)))
    summary = summarize(labels, arch_id, "CAUSAL", cfg, runtime, status, max(gaps) if gaps else None)
    return labels, summary


def summarize(labels: pd.DataFrame, arch_id: str, workflow: str, cfg: dict, runtime: float, solver_status: str, mip_gap: float | None) -> dict:
    revenue = float(labels["hourly_raw_revenue_USD"].sum())
    delivered = float(labels["delivered_power_MW"].sum())
    charged = float(labels["charge_MW"].sum())
    discharged = float(labels["discharge_MW"].sum())
    curtailed = float(labels["curtailed_wind_MW"].sum())
    storage_loss = float(discharge_loss(discharge_mwh=discharged, rte=cfg["rte"]))
    checks = qa_checks(
        labels,
        cfg["power_mw"],
        cfg["capacity_mwh"],
        cfg["grid_cap_mw"],
        cfg["rte"],
        cfg["min_soc_frac"],
        cfg["max_soc_frac"],
        cfg["annual_terminal_soc_mwh"],
    )
    violation_total = int(
        checks["soc_below_min_violation_count"]
        + checks["soc_above_max_violation_count"]
        + checks["simultaneous_charge_discharge_violation_count"]
        + checks["wind_only_charging_violation_count"]
        + checks["grid_export_violation_count"]
        + checks["energy_availability_violation_count"]
        + checks["annual_terminal_soc_violation_count"]
    )
    return {
        "run_id": f"{arch_id}_{workflow}",
        "architecture_id": arch_id,
        "workflow": "Oracle" if workflow == "ORACLE" else "Causal",
        "power_mw": cfg["power_mw"],
        "duration_h": cfg["duration_h"],
        "energy_mwh": cfg["capacity_mwh"],
        "planning_horizon_h": 8784 if workflow == "ORACLE" else cfg["causal_horizon_hours"],
        "execution_step_h": 8784 if workflow == "ORACLE" else cfg["execution_step_hours"],
        "initial_soc_mwh": cfg["initial_soc_mwh"],
        "minimum_soc_mwh": cfg["capacity_mwh"] * cfg["min_soc_frac"],
        "final_soc_mwh": float(labels["SOC_end_MWh"].iloc[-1]),
        "raw_realized_revenue_usd": revenue,
        "delivered_energy_mwh": delivered,
        "charged_energy_mwh": charged,
        "discharged_energy_mwh": discharged,
        "curtailed_wind_mwh": curtailed,
        "storage_loss_mwh": storage_loss,
        "constraint_violations": violation_total,
        "solver_status": solver_status,
        "runtime_s": runtime,
        "max_mip_gap": mip_gap,
        **{f"qa_{k}": v for k, v in checks.items()},
    }


def write_hourly(labels: pd.DataFrame, output_path: Path) -> None:
    cols = [
        "timestamp",
        "actual_wind_MW",
        "actual_raw_price_USD_per_MWh",
        "forecast_wind_MW",
        "forecast_price_USD_per_MWh",
        "direct_wind_MW",
        "charge_MW",
        "discharge_MW",
        "delivered_power_MW",
        "SOC_start_MWh",
        "SOC_end_MWh",
        "curtailed_wind_MW",
        "hourly_raw_revenue_USD",
        "solver_status_or_window_id",
    ]
    out = labels[cols].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    default_repo = Path(__file__).resolve().parents[2]
    parser.add_argument("--repo", type=Path, default=default_repo)
    parser.add_argument(
        "--out",
        type=Path,
        default=default_repo / "strategy_model" / "optimization" / "b6_final_results",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    logs_dir = args.out / "logs"
    logs_dir.mkdir(exist_ok=True)

    repo = args.repo
    commit = git_value(repo, "rev-parse", "HEAD")
    remote_url = git_value(repo, "remote", "get-url", "origin")
    status_short = git_value(repo, "status", "--short")
    data_2020, data_audit = load_b6_data(repo)
    forecast_df, forecast_payload = prepare_forecast_frame(repo, data_2020, horizon=48)
    if not forecast_df[["timestamp", "actual_wind_MW", "actual_raw_price_USD_per_MWh"]].equals(
        data_2020[["timestamp", "actual_wind_MW", "actual_raw_price_USD_per_MWh"]]
    ):
        raise RuntimeError("Forecast test frame does not match B6 2020 data frame.")

    common = {
        "storage_type": "CAES",
        "rte": 0.55,
        "depth_of_discharge": 0.80,
        "min_soc_frac": 0.20,
        "max_soc_frac": 1.00,
        "initial_soc_frac": 0.20,
        "grid_cap_mw": 249.0,
        "causal_horizon_hours": 48,
        "execution_step_hours": 24,
        "mip_gap": 1e-6,
        "oracle_time_limit_seconds": 1800.0,
        "causal_window_time_limit_seconds": 120.0,
        "terminal_policy": "common annual rule: minimum SOC, initial SOC, and realized final 2020 SOC all equal 20% of architecture energy capacity; causal executed SOC carries chronologically",
        "direct_wind_execution_policy": "causal realized execution retains optimizer planned direct-wind allocation: direct = min(planned direct, actual wind remaining after executed charging, grid capacity remaining after executed discharge); all remaining actual wind is curtailment",
        "charging_policy": "wind-only; no grid charging",
        "primary_metric": "raw realized revenue USD = sum(delivered_power_MW * actual_raw_price_USD_per_MWh)",
    }

    config_records = []
    for arch_id, arch in ARCHITECTURES.items():
        cfg = dict(common)
        cfg.update(arch)
        cfg["capacity_mwh"] = cfg["power_mw"] * cfg["duration_h"]
        cfg["initial_soc_mwh"] = cfg["capacity_mwh"] * cfg["initial_soc_frac"]
        cfg["minimum_soc_mwh"] = cfg["capacity_mwh"] * cfg["min_soc_frac"]
        cfg["annual_terminal_soc_mwh"] = cfg["capacity_mwh"] * cfg["min_soc_frac"]
        config_records.append({"architecture": arch_id, **cfg})

    metadata = {
        "repository_url": remote_url,
        "commit_hash": commit,
        "git_status_short": status_short,
        "python_version": sys.version,
        "platform": platform.platform(),
        "gurobi_version": ".".join(map(str, gp.gurobi.version())),
        "data_audit": data_audit,
        "forecast_metadata": forecast_payload["metadata"],
        "common_configuration": common,
        "architecture_configuration": config_records,
    }
    (args.out / "David_B6_frozen_config.json").write_text(json.dumps(metadata, indent=2))

    commands = [
        f"git -C {repo} rev-parse HEAD",
        f"{sys.executable} {Path(__file__).resolve()} --repo {repo} --out {args.out}",
    ]
    (args.out / "David_B6_commands.txt").write_text("\n".join(commands) + "\n")

    run_summaries = []
    qa_rows = []
    for arch_id, arch in ARCHITECTURES.items():
        cfg = dict(common)
        cfg.update(arch)
        cfg["capacity_mwh"] = cfg["power_mw"] * cfg["duration_h"]
        cfg["initial_soc_mwh"] = cfg["capacity_mwh"] * cfg["initial_soc_frac"]
        cfg["annual_terminal_soc_mwh"] = cfg["capacity_mwh"] * cfg["min_soc_frac"]

        for workflow in ("ORACLE", "CAUSAL"):
            run_id = f"{arch_id}_{workflow}"
            print(f"Starting {run_id}", flush=True)
            started = time.perf_counter()
            if workflow == "ORACLE":
                labels, summary = run_oracle(data_2020, arch_id, cfg)
            else:
                labels, summary = run_causal(data_2020, forecast_payload, arch_id, cfg)
            elapsed = time.perf_counter() - started
            summary["wall_clock_s"] = elapsed
            filename = f"David_B6_{run_id}_2020_Hourly.csv"
            summary["hourly_output_filename"] = filename
            write_hourly(labels, args.out / filename)
            run_summaries.append(summary)
            qa_rows.append({"run_id": run_id, **{k: v for k, v in summary.items() if k.startswith("qa_")}})
            (logs_dir / f"David_B6_{run_id}.json").write_text(json.dumps(summary, indent=2))
            print(
                f"Completed {run_id}: revenue=${summary['raw_realized_revenue_usd']:,.2f}, "
                f"violations={summary['constraint_violations']}, rows={summary['qa_row_count']}",
                flush=True,
            )

    pd.DataFrame(run_summaries).to_csv(args.out / "David_B6_run_summary.csv", index=False)
    pd.DataFrame(qa_rows).to_csv(args.out / "David_B6_QA_summary.csv", index=False)
    print(f"Wrote B6 package outputs to {args.out}", flush=True)


if __name__ == "__main__":
    main()
