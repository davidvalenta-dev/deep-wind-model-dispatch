"""Rolling-horizon Gurobi dispatch with Nora's MILP constraints.

This experiment uses Gurobi as the mixed-integer teacher for COVE-DV.

Plain English:
- At each time step, Gurobi looks ahead a fixed number of hours.
- It chooses charge, discharge, hold, direct-to-grid, delivered power, and storage.
- Only the first part of that plan is executed.
- Then the battery state carries forward chronologically and the window rolls.

The default model includes Nora's operational constraints:
- storage capacity limits,
- charging/discharging power limits,
- one binary charge/discharge mode per hour,
- available-energy discharge limit,
- wind-only charging,
- delivered power definition,
- grid export limit,
- storage state update,
- end-of-horizon SoC_initial = SoC_final.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
if str(STRATEGY_SRC) not in sys.path:
    sys.path.insert(0, str(STRATEGY_SRC))

import util  # noqa: E402


def load_data(data_path: Path, config: dict, offset: int, hours: int | None) -> pd.DataFrame:
    df = pd.read_csv(data_path)
    end = None if hours is None else offset + hours
    df = df.iloc[offset:end].reset_index(drop=True)
    df["price_normalized"] = util.normalize_price(df["lmp"].copy(), config)
    return df


def cove_value(power: np.ndarray, price: np.ndarray, config: dict) -> float:
    return float(
        util.cove(
            power,
            price,
            config["storage_type"],
            config["storage_rating"],
            config["storage_duration"],
            config["rated_capacity"],
            config["num_modules"],
        )
    )


def continuous_baseload(power: np.ndarray, config: dict, initial_soc: float = 0.0) -> np.ndarray:
    """Simple baseload comparator with chronological storage continuity."""
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    target = float(np.mean(power))
    storage = float(np.clip(initial_soc, 0.0, capacity))
    released = np.zeros(len(power), dtype=float)

    for i, generation in enumerate(power):
        if generation >= target:
            charge = min(generation - target, rating, capacity - storage)
            direct = min(generation - charge, float(config["rated_capacity"]))
            released[i] = direct
            storage += charge
        else:
            direct = min(generation, float(config["rated_capacity"]))
            needed = max(0.0, target - direct)
            discharge = min(needed, rating, storage * rte, float(config["rated_capacity"]) - direct)
            released[i] = direct + discharge
            storage -= discharge / rte
    return released


def fixed_costs(config: dict) -> tuple[float, float]:
    capex_kw, opex_kw, _ = util.get_storage_specs(
        config["storage_type"], config["storage_rating"], config["storage_duration"]
    )
    rating_kw = config["storage_rating"] * 1000
    wind_rating_kw = config["rated_capacity"] * 1000
    wind_cost = (util.WF_CAPEX * wind_rating_kw * util.FCR) + (util.WF_OPEX * wind_rating_kw)
    storage_cost = config["num_modules"] * ((capex_kw * rating_kw * util.FCR) + (opex_kw * rating_kw))
    return float(wind_cost), float(wind_cost + storage_cost)


def solve_window(
    generation: np.ndarray,
    price: np.ndarray,
    config: dict,
    initial_soc: float,
    terminal_policy: str,
    min_soc_frac: float,
    max_soc_frac: float,
    mip_gap: float,
    time_limit: float | None,
) -> dict[str, np.ndarray | float | int | str]:
    import gurobipy as gp
    from gurobipy import GRB

    hours = len(generation)
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    grid_cap = float(config["rated_capacity"])
    min_soc = capacity * min_soc_frac
    max_soc = capacity * max_soc_frac
    start_soc = float(np.clip(initial_soc, min_soc, max_soc))

    model = gp.Model("rolling_horizon_dispatch")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = mip_gap
    if time_limit is not None:
        model.Params.TimeLimit = time_limit

    # Nora's decision variables.
    p_dir = model.addVars(hours, lb=0.0, ub=grid_cap, name="P_dir")
    p_ch = model.addVars(hours, lb=0.0, ub=rating, name="P_ch")
    p_dis = model.addVars(hours, lb=0.0, ub=rating, name="P_dis")
    p_delivered = model.addVars(hours, lb=0.0, ub=grid_cap, name="P_delivered")
    soc = model.addVars(hours + 1, lb=min_soc, ub=max_soc, name="SoC")
    u = model.addVars(hours, vtype=GRB.BINARY, name="u_charge_mode")

    model.addConstr(soc[0] == start_soc, name="SoC_initial")
    if terminal_policy == "equal-initial":
        model.addConstr(soc[hours] == start_soc, name="SoC_final_equals_initial")
    elif terminal_policy == "no-empty":
        model.addConstr(soc[hours] >= start_soc, name="SoC_final_at_least_initial")
    elif terminal_policy != "none":
        raise ValueError(f"Unknown terminal policy: {terminal_policy}")

    for t in range(hours):
        # Wind-only charging: direct wind plus charging cannot exceed generated wind.
        model.addConstr(p_dir[t] + p_ch[t] <= float(generation[t]), name=f"wind_only_charging_{t}")

        # Power delivered to the grid.
        model.addConstr(p_delivered[t] == p_dir[t] + p_dis[t], name=f"delivered_definition_{t}")

        # Binary operating mode: u=1 allows charging; u=0 allows discharging.
        model.addConstr(p_ch[t] <= rating * u[t], name=f"charge_mode_{t}")
        model.addConstr(p_dis[t] <= rating * (1 - u[t]), name=f"discharge_mode_{t}")

        # Available energy: delivered discharge cannot use more storage than exists.
        model.addConstr(p_dis[t] / rte <= soc[t] - min_soc, name=f"available_energy_{t}")

        # State-of-charge update.
        model.addConstr(soc[t + 1] == soc[t] + p_ch[t] - (p_dis[t] / rte), name=f"soc_update_{t}")

    model.setObjective(gp.quicksum(float(price[t]) * p_delivered[t] for t in range(hours)), GRB.MAXIMIZE)
    model.optimize()

    acceptable = {GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL}
    if model.Status not in acceptable or model.SolCount == 0:
        raise RuntimeError(f"Gurobi failed. status={model.Status}, sol_count={model.SolCount}")

    direct = np.array([p_dir[t].X for t in range(hours)], dtype=float)
    charge = np.array([p_ch[t].X for t in range(hours)], dtype=float)
    discharge = np.array([p_dis[t].X for t in range(hours)], dtype=float)
    delivered = np.array([p_delivered[t].X for t in range(hours)], dtype=float)
    storage = np.array([soc[t].X for t in range(hours + 1)], dtype=float)
    mode = np.array([u[t].X for t in range(hours)], dtype=float)
    action = np.clip((discharge - charge) / rating, -1.0, 1.0)

    return {
        "status": int(model.Status),
        "objective": float(model.ObjVal),
        "runtime": float(model.Runtime),
        "mip_gap": float(model.MIPGap) if model.SolCount else math.nan,
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "delivered": delivered,
        "storage": storage,
        "mode": mode,
        "action": action,
    }


def check_constraints(labels: pd.DataFrame, config: dict, min_soc_frac: float, max_soc_frac: float) -> dict[str, float]:
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    grid_cap = float(config["rated_capacity"])
    min_soc = capacity * min_soc_frac
    max_soc = capacity * max_soc_frac

    gen = labels["power_generated"].to_numpy(dtype=float)
    direct = labels["gurobi_direct"].to_numpy(dtype=float)
    charge = labels["gurobi_charge"].to_numpy(dtype=float)
    discharge = labels["gurobi_discharge"].to_numpy(dtype=float)
    delivered = labels["gurobi_release"].to_numpy(dtype=float)
    soc_start = labels["gurobi_storage_start"].to_numpy(dtype=float)
    soc_end = labels["gurobi_storage_end"].to_numpy(dtype=float)
    mode = labels["gurobi_mode_binary_charge"].to_numpy(dtype=float)

    return {
        "max_wind_only_violation": float(np.max(np.maximum(direct + charge - gen, 0.0))),
        "max_delivered_definition_violation": float(np.max(np.abs(delivered - direct - discharge))),
        "max_grid_violation": float(np.max(np.maximum(delivered - grid_cap, 0.0))),
        "max_charge_mode_violation": float(np.max(np.maximum(charge - rating * mode, 0.0))),
        "max_discharge_mode_violation": float(np.max(np.maximum(discharge - rating * (1.0 - mode), 0.0))),
        "max_available_energy_violation": float(np.max(np.maximum(discharge / rte - (soc_start - min_soc), 0.0))),
        "max_soc_update_violation": float(np.max(np.abs(soc_end - (soc_start + charge - discharge / rte)))),
        "max_soc_lower_violation": float(np.max(np.maximum(min_soc - soc_start, 0.0))),
        "max_soc_upper_violation": float(np.max(np.maximum(soc_start - max_soc, 0.0))),
    }


def write_progress(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_rolling(
    df: pd.DataFrame,
    config: dict,
    horizon_hours: int,
    step_hours: int,
    terminal_policy: str,
    initial_soc: float,
    min_soc_frac: float,
    max_soc_frac: float,
    mip_gap: float,
    time_limit: float | None,
    max_windows: int | None,
    progress_every: int,
    checkpoint_path: Path | None,
) -> tuple[pd.DataFrame, list[dict]]:
    generation = df["power_generated"].to_numpy(dtype=float)
    price = df["price_normalized"].to_numpy(dtype=float)
    rows: list[dict] = []
    window_rows: list[dict] = []
    current_soc = initial_soc
    total_windows = math.ceil(len(df) / step_hours)
    started = time.perf_counter()

    for window_index, start in enumerate(range(0, len(df), step_hours)):
        if max_windows is not None and window_index >= max_windows:
            break

        window_end = min(start + horizon_hours, len(df))
        execute_end = min(start + step_hours, len(df))
        if window_end <= start:
            break

        solution = solve_window(
            generation[start:window_end],
            price[start:window_end],
            config,
            current_soc,
            terminal_policy,
            min_soc_frac,
            max_soc_frac,
            mip_gap,
            time_limit,
        )
        execute_len = execute_end - start

        for k in range(execute_len):
            hour = start + k
            storage_start = float(solution["storage"][k])
            storage_end = float(solution["storage"][k + 1])
            charge = float(solution["charge"][k])
            discharge = float(solution["discharge"][k])
            direct = float(solution["direct"][k])
            release = float(solution["delivered"][k])
            row = {
                "hour_index": hour,
                "datetime": df["datetime"].iloc[hour] if "datetime" in df.columns else "",
                "power_generated": float(generation[hour]),
                "price": float(price[hour]),
                "gurobi_release": release,
                "gurobi_direct": direct,
                "gurobi_charge": charge,
                "gurobi_discharge": discharge,
                "gurobi_discharge_before_rte": float(discharge / util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"])),
                "gurobi_storage_start": storage_start,
                "gurobi_storage_end": storage_end,
                "gurobi_mode_binary_charge": float(solution["mode"][k]),
                "gurobi_action": float(solution["action"][k]),
                "gurobi_curtailment": max(0.0, float(generation[hour]) - direct - charge),
                "horizon_start_hour": start,
                "horizon_end_hour": window_end - 1,
                "executed_hours": execute_len,
            }
            rows.append(row)

        current_soc = float(solution["storage"][execute_len])
        window_rows.append(
            {
                "window_index": window_index,
                "horizon_start_hour": start,
                "horizon_end_hour": window_end - 1,
                "executed_until_hour": execute_end - 1,
                "initial_soc": float(solution["storage"][0]),
                "soc_after_execution": current_soc,
                "planned_terminal_soc": float(solution["storage"][-1]),
                "objective": float(solution["objective"]),
                "runtime_seconds": float(solution["runtime"]),
                "mip_gap": float(solution["mip_gap"]),
                "status": int(solution["status"]),
            }
        )

        if progress_every > 0 and (window_index + 1) % progress_every == 0:
            elapsed = time.perf_counter() - started
            print(
                f"window {window_index + 1}/{total_windows}: "
                f"hour {execute_end}/{len(df)}, current SoC={current_soc:.3f}, "
                f"elapsed={elapsed:.1f}s",
                flush=True,
            )
            if checkpoint_path is not None:
                write_progress(checkpoint_path, rows)

    labels = pd.DataFrame(rows)
    return labels, window_rows


def add_compatibility_columns(labels: pd.DataFrame, config: dict) -> pd.DataFrame:
    labels = labels.copy()
    labels["milp_release"] = labels["gurobi_release"]
    labels["milp_direct"] = labels["gurobi_direct"]
    labels["milp_charge"] = labels["gurobi_charge"]
    labels["milp_discharge"] = labels["gurobi_discharge"]
    labels["milp_discharge_before_rte"] = labels["gurobi_discharge_before_rte"]
    labels["milp_storage"] = labels["gurobi_storage_start"]
    labels["milp_mode_binary_charge"] = labels["gurobi_mode_binary_charge"]
    labels["milp_action"] = labels["gurobi_action"]
    labels["milp_curtailment"] = labels["gurobi_curtailment"]
    labels["optimal_release"] = labels["gurobi_release"]
    labels["optimal_direct"] = labels["gurobi_direct"]
    labels["optimal_charge"] = labels["gurobi_charge"]
    labels["optimal_discharge"] = labels["gurobi_discharge"]
    labels["optimal_discharge_before_rte"] = labels["gurobi_discharge_before_rte"]
    labels["optimal_storage"] = labels["gurobi_storage_start"]
    labels["optimal_curtailment"] = labels["gurobi_curtailment"]
    labels["baseload_release"] = continuous_baseload(labels["power_generated"].to_numpy(dtype=float), config)
    return labels


def summarize(labels: pd.DataFrame, window_rows: list[dict], config: dict, args: argparse.Namespace) -> dict[str, float | str]:
    power = labels["power_generated"].to_numpy(dtype=float)
    price = labels["price"].to_numpy(dtype=float)
    gurobi_release = labels["gurobi_release"].to_numpy(dtype=float)
    baseload_release = labels["baseload_release"].to_numpy(dtype=float)

    wind_cost, dispatch_cost = fixed_costs(config)
    generation_revenue = float(util.revenue(power, price))
    baseload_revenue = float(util.revenue(baseload_release, price))
    gurobi_revenue = float(util.revenue(gurobi_release, price))
    baseload_cove = cove_value(baseload_release, price, config)
    gurobi_cove = cove_value(gurobi_release, price, config)
    ntg_cove = float(wind_cost / generation_revenue)
    constraint_checks = check_constraints(labels, config, args.min_soc_frac, args.max_soc_frac)
    total_runtime = float(sum(row["runtime_seconds"] for row in window_rows))

    summary: dict[str, float | str] = {
        "method": "rolling_horizon_gurobi_mip",
        "hours": float(len(labels)),
        "horizon_hours": float(args.horizon_hours),
        "step_hours": float(args.step_hours),
        "terminal_policy": args.terminal_policy,
        "storage_type": config["storage_type"],
        "storage_rating": float(config["storage_rating"]),
        "storage_duration": float(config["storage_duration"]),
        "storage_capacity": float(config["storage_rating"] * config["storage_duration"] * config["num_modules"]),
        "rated_grid_capacity": float(config["rated_capacity"]),
        "num_windows": float(len(window_rows)),
        "gurobi_runtime_seconds_sum": total_runtime,
        "gurobi_runtime_seconds_mean": float(np.mean([row["runtime_seconds"] for row in window_rows])) if window_rows else 0.0,
        "generation_revenue": generation_revenue,
        "baseload_revenue": baseload_revenue,
        "gurobi_revenue": gurobi_revenue,
        "wind_cost_c_ntg": wind_cost,
        "dispatch_cost_c": dispatch_cost,
        "ntg_profit_sum_gi_pi_minus_c_ntg": generation_revenue - wind_cost,
        "baseload_profit_sum_di_pi_minus_c": baseload_revenue - dispatch_cost,
        "gurobi_profit_sum_di_pi_minus_c": gurobi_revenue - dispatch_cost,
        "ntg_cove": ntg_cove,
        "baseload_cove": baseload_cove,
        "gurobi_cove": gurobi_cove,
        "gurobi_improvement_vs_baseload_pct": float((baseload_cove - gurobi_cove) / baseload_cove * 100.0),
        "paper_cove_nn_improvement_pct": 32.3,
        "gurobi_minus_paper_cove_nn_pct_points": float((baseload_cove - gurobi_cove) / baseload_cove * 100.0 - 32.3),
        "final_soc": float(labels["gurobi_storage_end"].iloc[-1]) if len(labels) else 0.0,
        "max_soc": float(max(labels["gurobi_storage_start"].max(), labels["gurobi_storage_end"].max())) if len(labels) else 0.0,
    }
    summary.update(constraint_checks)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rolling-horizon Gurobi dispatch with Nora constraints.")
    parser.add_argument("--data", default=str(REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"))
    parser.add_argument("--config", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"))
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "strategy_model" / "optimization" / "rolling_horizon_gurobi_run_016"))
    parser.add_argument("--hours", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--horizon-hours", type=int, default=168)
    parser.add_argument("--step-hours", type=int, default=24)
    parser.add_argument("--terminal-policy", choices=["equal-initial", "no-empty", "none"], default="equal-initial")
    parser.add_argument("--initial-soc", type=float, default=0.0)
    parser.add_argument("--min-soc-frac", type=float, default=0.0)
    parser.add_argument("--max-soc-frac", type=float, default=1.0)
    parser.add_argument("--mip-gap", type=float, default=0.0)
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--max-windows", type=int, default=None)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--storage-type", default=None)
    parser.add_argument("--storage-rating", type=float, default=None)
    parser.add_argument("--storage-duration", type=float, default=None)
    args = parser.parse_args()

    config = util.load_config(args.config)
    if args.storage_type is not None:
        config["storage_type"] = args.storage_type
    if args.storage_rating is not None:
        config["storage_rating"] = int(args.storage_rating) if args.storage_rating.is_integer() else args.storage_rating
    if args.storage_duration is not None:
        config["storage_duration"] = int(args.storage_duration) if args.storage_duration.is_integer() else args.storage_duration
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(Path(args.data), config, args.offset, args.hours)
    variable_count = 6 * args.horizon_hours + 1
    rough_constraint_count = 6 * args.horizon_hours + 2
    print(f"Loaded {len(df)} hours from {args.data}")
    print(f"Horizon={args.horizon_hours}, step={args.step_hours}, terminal={args.terminal_policy}")
    print(f"Approx per-window size: {variable_count} variables, {rough_constraint_count} constraints")
    if variable_count > 2000 or rough_constraint_count > 2000:
        print("WARNING: this may exceed the restricted Gurobi license size limit.")

    checkpoint_path = out_dir / "rolling_horizon_gurobi_labels_checkpoint.csv"
    labels, window_rows = run_rolling(
        df=df,
        config=config,
        horizon_hours=args.horizon_hours,
        step_hours=args.step_hours,
        terminal_policy=args.terminal_policy,
        initial_soc=args.initial_soc,
        min_soc_frac=args.min_soc_frac,
        max_soc_frac=args.max_soc_frac,
        mip_gap=args.mip_gap,
        time_limit=args.time_limit,
        max_windows=args.max_windows,
        progress_every=args.progress_every,
        checkpoint_path=checkpoint_path,
    )
    labels = add_compatibility_columns(labels, config)
    summary = summarize(labels, window_rows, config, args)

    labels_out = out_dir / "rolling_horizon_gurobi_labels.csv"
    windows_out = out_dir / "rolling_horizon_gurobi_windows.csv"
    summary_out = out_dir / "rolling_horizon_gurobi_summary.csv"
    json_out = out_dir / "rolling_horizon_gurobi_summary.json"

    labels.to_csv(labels_out, index=False)
    pd.DataFrame(window_rows).to_csv(windows_out, index=False)
    pd.DataFrame([summary]).to_csv(summary_out, index=False)
    json_out.write_text(json.dumps(summary, indent=2))

    print("\nRolling-horizon Gurobi results")
    print(f"Hours evaluated: {int(summary['hours'])}")
    print(f"Baseload COVE: {summary['baseload_cove']:.6f}")
    print(f"Gurobi COVE: {summary['gurobi_cove']:.6f}")
    print(f"Improvement vs baseload: {summary['gurobi_improvement_vs_baseload_pct']:.2f}%")
    print(f"Difference vs paper COVE-NN 32.3%: {summary['gurobi_minus_paper_cove_nn_pct_points']:.2f} percentage points")
    max_violation = max(float(summary[k]) for k in summary if k.startswith("max_") and k.endswith("_violation"))
    print(f"Constraint max violation: {max_violation:.3e}")
    print(f"Labels saved to: {labels_out}")
    print(f"Summary saved to: {summary_out}")


if __name__ == "__main__":
    main()
