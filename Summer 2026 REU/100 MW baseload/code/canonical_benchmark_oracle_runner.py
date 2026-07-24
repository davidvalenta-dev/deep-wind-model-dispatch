"""Run Chris Qin's required canonical benchmark and oracle cases.

This runner implements the tightly scoped cases from
David_REU_Advisor_Feedback_and_Required_Actions_v1.0.pdf:

1. 100-MW Constant-Output Baseload Benchmark.
2. H-hour Perfect-Information Oracle Rolling-Horizon MILP for 24, 48, and
   168 hour planning horizons.

The default configuration is the required 2020 Pyron/RTM benchmark:
- 100 MW / 10 h / 1000 MWh CAES
- SoC bounds 200 to 1000 MWh
- initial SoC 600 MWh
- year-end SoC 600 MWh for oracle cases
- RTE 0.55 applied on the discharge side
- 249 MW grid export cap
- wind-only charging and no grid charging
- raw realized RTM LMP in USD/MWh

Run from the repository root after copying this file into
strategy_model/optimization/:

    ./venv/bin/python strategy_model/optimization/canonical_benchmark_oracle_runner.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

os.environ["LC_ALL"] = "C"

import gurobipy as gp
import numpy as np
import pandas as pd
from gurobipy import GRB


@dataclass(frozen=True)
class StorageConfig:
    storage_power_mw: float = 100.0
    storage_duration_h: float = 10.0
    rte: float = 0.55
    min_soc_mwh: float = 200.0
    max_soc_mwh: float = 1000.0
    initial_soc_mwh: float = 600.0
    year_end_soc_mwh: float = 600.0
    grid_cap_mw: float = 249.0
    target_output_mw: float = 100.0
    wind_rating_mw: float = 249.0
    fcr: float = 0.065
    wind_capex_usd_per_kw: float = 1968.0
    wind_opex_usd_per_kw_year: float = 43.0
    caes_capex_usd_per_kw: float = 1125.33
    caes_opex_usd_per_kw_year: float = 15.43

    @property
    def capacity_mwh(self) -> float:
        return self.storage_power_mw * self.storage_duration_h

    @property
    def annualized_cost_usd(self) -> float:
        wind_kw = self.wind_rating_mw * 1000.0
        storage_kw = self.storage_power_mw * 1000.0
        wind_cost = (
            self.wind_capex_usd_per_kw * wind_kw * self.fcr
            + self.wind_opex_usd_per_kw_year * wind_kw
        )
        storage_cost = (
            self.caes_capex_usd_per_kw * storage_kw * self.fcr
            + self.caes_opex_usd_per_kw_year * storage_kw
        )
        return float(wind_cost + storage_cost)


def git_value(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except Exception:
        return "unavailable"


def parse_power_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    dates = df["Date"].astype(str)
    times = df["Time"].astype(int).astype(str).str.zfill(4)
    timestamps = pd.to_datetime(dates + times, format="%Y%m%d%H%M")
    return pd.DataFrame(
        {
            "source_power_timestamp": timestamps,
            "actual_wind_MW": df["Power"].astype(float),
        }
    )


def load_2020_pyron_rtm(repo: Path) -> tuple[pd.DataFrame, dict]:
    """Load the complete 2020 Pyron power and raw RTM LMP series.

    The raw ERCOT local timestamps include daylight-saving-time behavior. This
    uses the same chronological row-order alignment used in the B6 package and
    maps the values onto a continuous 8784-hour 2020 output index.
    """

    power_path = repo / "data" / "processed" / "pyron_power.csv"
    price_path = repo / "data" / "raw" / "prices" / "12cfb125-8fa9-4401-8b0f-9d928544b721.csv"
    older_combined_path = repo / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"

    power = parse_power_file(power_path)
    power_2020 = (
        power[power["source_power_timestamp"].dt.year == 2020]
        .sort_values("source_power_timestamp")
        .reset_index(drop=True)
    )

    raw_price = pd.read_csv(price_path)
    raw_price_2020 = raw_price[
        raw_price["interval_start_local"].astype(str).str.startswith("2020")
    ].copy()
    raw_price_2020 = raw_price_2020.sort_values("interval_start_utc").reset_index(drop=True)

    expected = pd.date_range("2020-01-01 00:00:00", "2020-12-31 23:00:00", freq="h")
    if len(power_2020) != 8784 or len(raw_price_2020) != 8784:
        raise RuntimeError(
            f"Expected 8784 rows for 2020, got power={len(power_2020)} "
            f"and raw_lmp={len(raw_price_2020)}"
        )

    df = pd.DataFrame(
        {
            "timestamp": expected,
            "actual_wind_MW": power_2020["actual_wind_MW"].astype(float).to_numpy(),
            "RTM_price_per_MWh": raw_price_2020["lmp"].astype(float).to_numpy(),
        }
    )

    older_missing = []
    older_rows = None
    if older_combined_path.exists():
        older = pd.read_csv(older_combined_path, usecols=["datetime"])
        older_ts = pd.to_datetime(older["datetime"], errors="coerce")
        older_2020 = older_ts[older_ts.dt.year == 2020]
        older_rows = int(len(older_2020))
        older_missing = [str(x) for x in expected.difference(pd.DatetimeIndex(older_2020))]

    audit = {
        "evaluation_period": "2020-01-01 00:00:00 to 2020-12-31 23:00:00",
        "rows": int(len(df)),
        "power_input_file": str(power_path),
        "raw_rtm_lmp_input_file": str(price_path),
        "older_combined_file_not_used": str(older_combined_path),
        "older_combined_2020_rows": older_rows,
        "older_combined_missing_hours": older_missing,
        "alignment": "complete 2020 Pyron power and raw RTM LMP aligned by chronological row order onto a continuous 8784-hour 2020 index",
        "price_units": "raw, uncapped, unnormalized USD/MWh",
        "wind_units": "MW",
        "first_timestamp": str(df["timestamp"].iloc[0]),
        "last_timestamp": str(df["timestamp"].iloc[-1]),
        "missing_output_hours": [str(x) for x in expected.difference(pd.DatetimeIndex(df["timestamp"]))],
        "duplicate_output_hours": int(df["timestamp"].duplicated().sum()),
        "wind_min_mw": float(df["actual_wind_MW"].min()),
        "wind_max_mw": float(df["actual_wind_MW"].max()),
        "price_min_usd_per_mwh": float(df["RTM_price_per_MWh"].min()),
        "price_max_usd_per_mwh": float(df["RTM_price_per_MWh"].max()),
    }
    return df, audit


def compute_cove(revenue_usd: float, config: StorageConfig) -> float:
    if revenue_usd <= 0:
        return math.inf
    return float(config.annualized_cost_usd / revenue_usd)


def run_constant_output_baseload(df: pd.DataFrame, config: StorageConfig) -> pd.DataFrame:
    rows = []
    soc = float(config.initial_soc_mwh)

    for _, row in df.iterrows():
        wind = max(float(row["actual_wind_MW"]), 0.0)
        price = float(row["RTM_price_per_MWh"])
        soc_start = soc
        direct = charge = discharge = curtail = shortfall = 0.0

        if wind >= config.target_output_mw:
            direct = config.target_output_mw
            room = max(0.0, config.max_soc_mwh - soc_start)
            charge = min(
                wind - config.target_output_mw,
                config.storage_power_mw,
                room,
            )
            curtail = max(0.0, wind - direct - charge)
            delivered = direct
        else:
            direct = wind
            available_discharge = max(0.0, (soc_start - config.min_soc_mwh) * config.rte)
            discharge = min(
                config.target_output_mw - wind,
                config.storage_power_mw,
                available_discharge,
                max(0.0, config.grid_cap_mw - direct),
            )
            delivered = direct + discharge
            shortfall = max(0.0, config.target_output_mw - delivered)

        soc = soc_start + charge - discharge / config.rte
        rows.append(
            {
                "timestamp": row["timestamp"],
                "actual_wind_MW": wind,
                "target_output_MW": config.target_output_mw,
                "direct_wind_MW": direct,
                "charge_MW": charge,
                "discharge_MW": discharge,
                "delivered_power_MW": delivered,
                "curtailment_MW": curtail,
                "output_shortfall_MW": shortfall,
                "SOC_start_MWh": soc_start,
                "SOC_end_MWh": soc,
                "RTM_price_per_MWh": price,
                "hourly_revenue": delivered * price,
                "case_uses_future_actual_data": False,
                "planning_horizon_hours": 0,
                "execution_step_hours": 1,
                "replanning_interval_hours": 1,
                "oracle_information_horizon_hours": 0,
            }
        )

    return pd.DataFrame(rows)


def solve_oracle_window(
    generation: np.ndarray,
    price: np.ndarray,
    initial_soc: float,
    config: StorageConfig,
    enforce_terminal_600: bool,
    mip_gap: float,
    time_limit: float | None,
) -> dict:
    hours = len(generation)
    model = gp.Model("perfect_information_oracle_rh")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = mip_gap
    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    p_dir = model.addVars(hours, lb=0.0, ub=config.grid_cap_mw, name="P_dir")
    p_ch = model.addVars(hours, lb=0.0, ub=config.storage_power_mw, name="P_ch")
    p_dis = model.addVars(hours, lb=0.0, ub=config.storage_power_mw, name="P_dis")
    p_del = model.addVars(hours, lb=0.0, ub=config.grid_cap_mw, name="P_delivered")
    soc = model.addVars(hours + 1, lb=config.min_soc_mwh, ub=config.max_soc_mwh, name="SoC")
    u = model.addVars(hours, vtype=GRB.BINARY, name="u_charge_mode")

    start_soc = float(np.clip(initial_soc, config.min_soc_mwh, config.max_soc_mwh))
    model.addConstr(soc[0] == start_soc, name="SOC_initial")
    if enforce_terminal_600:
        model.addConstr(soc[hours] == config.year_end_soc_mwh, name="year_end_SOC_600")

    for t in range(hours):
        gen_t = max(float(generation[t]), 0.0)
        model.addConstr(p_dir[t] + p_ch[t] <= gen_t, name=f"wind_only_charging_{t}")
        model.addConstr(p_del[t] == p_dir[t] + p_dis[t], name=f"delivered_definition_{t}")
        model.addConstr(p_ch[t] <= config.storage_power_mw * u[t], name=f"charge_mode_{t}")
        model.addConstr(p_dis[t] <= config.storage_power_mw * (1.0 - u[t]), name=f"discharge_mode_{t}")
        model.addConstr(
            p_dis[t] / config.rte <= soc[t] - config.min_soc_mwh,
            name=f"available_energy_{t}",
        )
        model.addConstr(
            soc[t + 1] == soc[t] + p_ch[t] - p_dis[t] / config.rte,
            name=f"soc_update_{t}",
        )

    model.setObjective(
        gp.quicksum(float(price[t]) * p_del[t] for t in range(hours)),
        GRB.MAXIMIZE,
    )
    started = time.perf_counter()
    model.optimize()
    runtime = time.perf_counter() - started
    if model.Status not in {GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL} or model.SolCount == 0:
        raise RuntimeError(f"Oracle Gurobi solve failed: status={model.Status}, hours={hours}")

    return {
        "direct": np.array([p_dir[t].X for t in range(hours)], dtype=float),
        "charge": np.array([p_ch[t].X for t in range(hours)], dtype=float),
        "discharge": np.array([p_dis[t].X for t in range(hours)], dtype=float),
        "delivered": np.array([p_del[t].X for t in range(hours)], dtype=float),
        "soc": np.array([soc[t].X for t in range(hours + 1)], dtype=float),
        "mode": np.array([u[t].X for t in range(hours)], dtype=float),
        "status": int(model.Status),
        "objective": float(model.ObjVal),
        "runtime": float(runtime),
        "mip_gap": float(model.MIPGap) if model.SolCount else math.nan,
    }


def run_oracle_rolling_horizon(
    df: pd.DataFrame,
    planning_horizon_hours: int,
    config: StorageConfig,
    mip_gap: float,
    time_limit: float | None,
) -> tuple[pd.DataFrame, dict]:
    generation = df["actual_wind_MW"].to_numpy(dtype=float)
    price = df["RTM_price_per_MWh"].to_numpy(dtype=float)
    timestamps = df["timestamp"].to_numpy()
    rows = []
    soc = float(config.initial_soc_mwh)
    runtime = 0.0
    max_mip_gap = 0.0

    for t in range(len(df)):
        end = min(len(df), t + planning_horizon_hours)
        horizon = end - t
        enforce_terminal = end == len(df)
        solution = solve_oracle_window(
            generation[t:end],
            price[t:end],
            soc,
            config,
            enforce_terminal_600=enforce_terminal,
            mip_gap=mip_gap,
            time_limit=time_limit,
        )
        runtime += solution["runtime"]
        if not math.isnan(solution["mip_gap"]):
            max_mip_gap = max(max_mip_gap, solution["mip_gap"])

        direct = float(solution["direct"][0])
        charge = float(solution["charge"][0])
        discharge = float(solution["discharge"][0])
        delivered = float(solution["delivered"][0])
        soc_start = soc
        soc_end = float(solution["soc"][1])
        curtail = max(0.0, generation[t] - direct - charge)
        rows.append(
            {
                "timestamp": timestamps[t],
                "actual_wind_MW": generation[t],
                "target_output_MW": np.nan,
                "direct_wind_MW": direct,
                "charge_MW": charge,
                "discharge_MW": discharge,
                "delivered_power_MW": delivered,
                "curtailment_MW": curtail,
                "output_shortfall_MW": np.nan,
                "SOC_start_MWh": soc_start,
                "SOC_end_MWh": soc_end,
                "RTM_price_per_MWh": price[t],
                "hourly_revenue": delivered * price[t],
                "case_uses_future_actual_data": True,
                "planning_horizon_hours": planning_horizon_hours,
                "execution_step_hours": 1,
                "replanning_interval_hours": 1,
                "oracle_information_horizon_hours": horizon,
                "year_end_terminal_constraint_active": bool(enforce_terminal),
                "solver_status": int(solution["status"]),
            }
        )
        soc = soc_end
        if (t + 1) % 500 == 0 or t + 1 == len(df):
            print(
                f"Oracle H={planning_horizon_hours}: solved {t + 1}/{len(df)} hours; SoC={soc:.3f}",
                flush=True,
            )

    labels = pd.DataFrame(rows)
    metadata = {
        "solver_runtime_seconds": runtime,
        "max_mip_gap": max_mip_gap,
    }
    return labels, metadata


def chronological_continuity_error(timestamps: pd.Series) -> int:
    dt = pd.to_datetime(timestamps)
    expected = pd.date_range(dt.iloc[0], dt.iloc[-1], freq="h")
    return int(len(expected.difference(pd.DatetimeIndex(dt))) + dt.duplicated().sum())


def qa_for_labels(labels: pd.DataFrame, config: StorageConfig, case_type: str) -> dict:
    wind = labels["actual_wind_MW"].to_numpy(float)
    direct = labels["direct_wind_MW"].to_numpy(float)
    charge = labels["charge_MW"].to_numpy(float)
    discharge = labels["discharge_MW"].to_numpy(float)
    delivered = labels["delivered_power_MW"].to_numpy(float)
    curtail = labels["curtailment_MW"].to_numpy(float)
    soc_start = labels["SOC_start_MWh"].to_numpy(float)
    soc_end = labels["SOC_end_MWh"].to_numpy(float)
    price = labels["RTM_price_per_MWh"].to_numpy(float)
    revenue = labels["hourly_revenue"].to_numpy(float)
    simultaneous = np.minimum(charge, discharge)

    qa = {
        "row_count": int(len(labels)),
        "chronological_continuity_error_count": chronological_continuity_error(labels["timestamp"]),
        "soc_recursion_max_abs_error": float(np.max(np.abs(soc_end - (soc_start + charge - discharge / config.rte)))),
        "soc_lower_violation_count": int(np.sum(soc_start < config.min_soc_mwh - 1e-6) + np.sum(soc_end < config.min_soc_mwh - 1e-6)),
        "soc_upper_violation_count": int(np.sum(soc_start > config.max_soc_mwh + 1e-6) + np.sum(soc_end > config.max_soc_mwh + 1e-6)),
        "charge_limit_violation_count": int(np.sum(charge > config.storage_power_mw + 1e-6)),
        "discharge_limit_violation_count": int(np.sum(discharge > config.storage_power_mw + 1e-6)),
        "simultaneous_charge_discharge_violation_count": int(np.sum(simultaneous > 1e-6)),
        "no_grid_charging_violation_count": int(np.sum(direct + charge > wind + 1e-6)),
        "wind_balance_max_abs_error": float(np.max(np.abs(wind - direct - charge - curtail))),
        "curtailment_negative_count": int(np.sum(curtail < -1e-6)),
        "delivered_balance_max_abs_error": float(np.max(np.abs(delivered - direct - discharge))),
        "grid_export_violation_count": int(np.sum(delivered > config.grid_cap_mw + 1e-6)),
        "hourly_revenue_sum_error_usd": float(abs(np.sum(revenue) - np.sum(delivered * price))),
        "initial_soc_mwh": float(soc_start[0]),
        "final_soc_mwh": float(soc_end[-1]),
    }

    if case_type == "constant_output_baseload":
        shortfall = labels["output_shortfall_MW"].to_numpy(float)
        target = config.target_output_mw
        qa.update(
            {
                "delivered_above_100mw_violation_count": int(np.sum(delivered > target + 1e-6)),
                "output_shortfall_negative_count": int(np.sum(shortfall < -1e-6)),
                "charging_when_wind_below_target_count": int(np.sum((wind < target - 1e-6) & (charge > 1e-6))),
                "discharging_when_wind_above_target_count": int(np.sum((wind >= target - 1e-6) & (discharge > 1e-6))),
                "final_soc_forced": False,
            }
        )
    elif case_type == "oracle_rh":
        qa.update(
            {
                "execution_step_equals_one_hour": bool((labels["execution_step_hours"] == 1).all()),
                "replanning_interval_equals_one_hour": bool((labels["replanning_interval_hours"] == 1).all()),
                "uses_future_actual_data_flag": bool(labels["case_uses_future_actual_data"].all()),
                "year_end_soc_abs_error_mwh": float(abs(soc_end[-1] - config.year_end_soc_mwh)),
                "year_end_soc_violation_count": int(abs(soc_end[-1] - config.year_end_soc_mwh) > 1e-5),
            }
        )

    violation_keys = [k for k in qa if k.endswith("_violation_count") or k.endswith("_error_count") or k.endswith("_negative_count")]
    qa["total_violation_count"] = int(sum(int(qa[k]) for k in violation_keys))
    if qa["soc_recursion_max_abs_error"] > 1e-5:
        qa["total_violation_count"] += 1
    if qa["wind_balance_max_abs_error"] > 1e-5:
        qa["total_violation_count"] += 1
    if qa["delivered_balance_max_abs_error"] > 1e-5:
        qa["total_violation_count"] += 1
    if qa["hourly_revenue_sum_error_usd"] > 1e-4:
        qa["total_violation_count"] += 1
    return qa


def summarize_case(
    case_id: str,
    case_name: str,
    labels: pd.DataFrame,
    config: StorageConfig,
    qa: dict,
    extra: dict | None = None,
) -> dict:
    revenue = float(labels["hourly_revenue"].sum())
    delivered = float(labels["delivered_power_MW"].sum())
    summary = {
        "case_id": case_id,
        "case_name": case_name,
        "evaluation_period": "2020",
        "row_count": int(len(labels)),
        "revenue_usd": revenue,
        "COVE": compute_cove(revenue, config),
        "annualized_cost_usd": config.annualized_cost_usd,
        "delivered_energy_mwh": delivered,
        "total_curtailment_mwh": float(labels["curtailment_MW"].sum()),
        "total_output_shortfall_mwh": float(labels["output_shortfall_MW"].fillna(0.0).sum()),
        "total_charge_throughput_mwh": float(labels["charge_MW"].sum()),
        "total_discharge_throughput_mwh": float(labels["discharge_MW"].sum()),
        "initial_soc_mwh": float(labels["SOC_start_MWh"].iloc[0]),
        "final_soc_mwh": float(labels["SOC_end_MWh"].iloc[-1]),
        "min_soc_mwh": float(min(labels["SOC_start_MWh"].min(), labels["SOC_end_MWh"].min())),
        "max_soc_mwh": float(max(labels["SOC_start_MWh"].max(), labels["SOC_end_MWh"].max())),
        "hours_exactly_meeting_100mw": int(np.sum(np.isclose(labels["delivered_power_MW"], config.target_output_mw, atol=1e-6))),
        "percent_hours_exactly_meeting_100mw": float(100.0 * np.mean(np.isclose(labels["delivered_power_MW"], config.target_output_mw, atol=1e-6))),
        "constraint_or_balance_violations": int(qa["total_violation_count"]),
    }
    if extra:
        summary.update(extra)
    return summary


def write_hourly(labels: pd.DataFrame, path: Path) -> None:
    out = labels.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_csv(path, index=False)


def write_registry(
    output_dir: Path,
    summaries: list[dict],
    repo: Path,
    commit: str,
    config: StorageConfig,
) -> None:
    rows = []
    for summary in summaries:
        case_name = summary["case_name"]
        is_oracle = "Oracle" in case_name
        is_baseload = "Baseload" in case_name
        rows.append(
            {
                "case_id": summary["case_id"],
                "case_name": case_name,
                "status": "candidate",
                "code_commit": commit,
                "runner": "strategy_model/optimization/canonical_benchmark_oracle_runner.py",
                "config": (
                    f"{config.storage_power_mw:g} MW / {config.storage_duration_h:g} h CAES, "
                    f"RTE {config.rte:g} discharge-side, {config.grid_cap_mw:g} MW grid cap"
                ),
                "dataset": "complete 2020 Pyron power plus raw PYR_PYRON1 RTM LMP",
                "wind_source": "data/processed/pyron_power.csv",
                "price_source": "data/raw/prices/12cfb125-8fa9-4401-8b0f-9d928544b721.csv",
                "evaluation_period": "2020",
                "historical_window_hours": 0,
                "forecast_horizon_hours": 0,
                "planning_horizon_hours": summary.get("planning_horizon_hours", 0),
                "execution_step_hours": summary.get("execution_step_hours", 1),
                "replanning_interval_hours": summary.get("replanning_interval_hours", 1),
                "storage_power_MW": config.storage_power_mw,
                "storage_duration_h": config.storage_duration_h,
                "RTE": config.rte,
                "initial_SOC_MWh": config.initial_soc_mwh,
                "year_end_SOC_rule": "none; report final SoC" if is_baseload else "return to 600 MWh",
                "terminal_policy": "none" if is_baseload else "none for intermediate windows; 600 MWh at year end",
                "scenario_count": 0,
                "random_seed": "",
                "revenue": summary["revenue_usd"],
                "COVE": summary["COVE"],
                "output_file": summary["hourly_output_file"],
            }
        )
    pd.DataFrame(rows).to_csv(output_dir / "experiment_registry.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run canonical 2020 baseload and oracle RH MILP cases.")
    script_dir = Path(__file__).resolve().parent
    default_repo = script_dir.parents[2]
    parser.add_argument("--repo", type=Path, default=default_repo)
    parser.add_argument("--out", type=Path, default=script_dir.parent / "results" / "full_rebuild_canonical_2020")
    parser.add_argument("--horizons", type=int, nargs="+", default=[24, 48, 168])
    parser.add_argument("--storage-power-mw", type=float, default=100.0)
    parser.add_argument("--storage-duration-h", type=float, default=10.0)
    parser.add_argument("--rte", type=float, default=0.55)
    parser.add_argument("--target-output-mw", type=float, default=100.0)
    parser.add_argument("--grid-cap-mw", type=float, default=249.0)
    parser.add_argument("--min-soc-mwh", type=float, default=None)
    parser.add_argument("--max-soc-mwh", type=float, default=None)
    parser.add_argument("--initial-soc-mwh", type=float, default=None)
    parser.add_argument("--year-end-soc-mwh", type=float, default=None)
    parser.add_argument("--mip-gap", type=float, default=1e-6)
    parser.add_argument("--time-limit", type=float, default=None)
    args = parser.parse_args()

    repo = args.repo.resolve()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    capacity = args.storage_power_mw * args.storage_duration_h
    min_soc = args.min_soc_mwh if args.min_soc_mwh is not None else 0.2 * capacity
    max_soc = args.max_soc_mwh if args.max_soc_mwh is not None else capacity
    initial_soc = args.initial_soc_mwh if args.initial_soc_mwh is not None else (min_soc + max_soc) / 2.0
    year_end_soc = args.year_end_soc_mwh if args.year_end_soc_mwh is not None else initial_soc
    config = StorageConfig(
        storage_power_mw=args.storage_power_mw,
        storage_duration_h=args.storage_duration_h,
        rte=args.rte,
        min_soc_mwh=min_soc,
        max_soc_mwh=max_soc,
        initial_soc_mwh=initial_soc,
        year_end_soc_mwh=year_end_soc,
        grid_cap_mw=args.grid_cap_mw,
        target_output_mw=args.target_output_mw,
    )
    commit = git_value(repo, "rev-parse", "HEAD")
    status_short = git_value(repo, "status", "--short")
    remote = git_value(repo, "remote", "get-url", "origin")
    data, audit = load_2020_pyron_rtm(repo)

    metadata = {
        "repository": str(repo),
        "repository_remote": remote,
        "code_commit": commit,
        "git_status_short": status_short,
        "gurobi_version": ".".join(map(str, gp.gurobi.version())),
        "python": sys.version,
        "data_audit": audit,
        "storage_config": config.__dict__,
        "scope": "Chris required actions v1.0: 100-MW constant-output baseload plus H-hour perfect-information oracle RH MILP for 24/48/168 h",
    }
    (out / "canonical_run_metadata.json").write_text(json.dumps(metadata, indent=2))

    commands = [
        (
            f"{sys.executable} {Path(__file__).resolve()} --repo {repo} --out {out} "
            f"--horizons {' '.join(map(str, args.horizons))} "
            f"--storage-power-mw {args.storage_power_mw} "
            f"--storage-duration-h {args.storage_duration_h} "
            f"--rte {args.rte} --target-output-mw {args.target_output_mw} "
            f"--grid-cap-mw {args.grid_cap_mw} --mip-gap {args.mip_gap}"
        ),
    ]
    (out / "commands.txt").write_text("\n".join(commands) + "\n")

    summaries: list[dict] = []
    qa_rows: list[dict] = []

    print("Running 100-MW Constant-Output Baseload Benchmark", flush=True)
    baseload = run_constant_output_baseload(data, config)
    baseload_qa = qa_for_labels(baseload, config, "constant_output_baseload")
    baseload_file = "constant_output_baseload_100mw_2020_hourly.csv"
    write_hourly(baseload, out / baseload_file)
    baseload_summary = summarize_case(
        "constant_output_baseload_100mw_2020",
        "100-MW Constant-Output Baseload Benchmark",
        baseload,
        config,
        baseload_qa,
        {"hourly_output_file": baseload_file, "planning_horizon_hours": 0, "execution_step_hours": 1, "replanning_interval_hours": 1},
    )
    summaries.append(baseload_summary)
    qa_rows.append({"case_id": baseload_summary["case_id"], **baseload_qa})
    print(
        f"Baseload complete: revenue=${baseload_summary['revenue_usd']:,.2f}, "
        f"COVE={baseload_summary['COVE']:.6f}, violations={baseload_qa['total_violation_count']}",
        flush=True,
    )

    for horizon in args.horizons:
        print(f"Running {horizon}-hour Perfect-Information Oracle Rolling-Horizon MILP", flush=True)
        labels, oracle_meta = run_oracle_rolling_horizon(
            data,
            horizon,
            config,
            mip_gap=args.mip_gap,
            time_limit=args.time_limit,
        )
        qa = qa_for_labels(labels, config, "oracle_rh")
        hourly_file = f"oracle_rh_milp_{horizon}h_2020_hourly.csv"
        write_hourly(labels, out / hourly_file)
        summary = summarize_case(
            f"oracle_rh_milp_{horizon}h_2020",
            f"{horizon}-hour Perfect-Information Oracle Rolling-Horizon MILP",
            labels,
            config,
            qa,
            {
                "hourly_output_file": hourly_file,
                "planning_horizon_hours": horizon,
                "execution_step_hours": 1,
                "replanning_interval_hours": 1,
                "oracle_information_horizon_hours": horizon,
                **oracle_meta,
            },
        )
        summaries.append(summary)
        qa_rows.append({"case_id": summary["case_id"], **qa})
        print(
            f"Oracle {horizon}h complete: revenue=${summary['revenue_usd']:,.2f}, "
            f"COVE={summary['COVE']:.6f}, final SoC={summary['final_soc_mwh']:.3f}, "
            f"violations={qa['total_violation_count']}",
            flush=True,
        )

    pd.DataFrame(summaries).to_csv(out / "canonical_summary.csv", index=False)
    pd.DataFrame(qa_rows).to_csv(out / "canonical_QA_report.csv", index=False)
    write_registry(out, summaries, repo, commit, config)
    print(f"Wrote canonical outputs to {out}", flush=True)


if __name__ == "__main__":
    main()
