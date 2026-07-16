"""Mixed-integer teacher for wind-storage dispatch.

This script creates the stronger teacher Chris asked for.

Plain-English model:
- P_gen(t) is wind generation at hour t.
- lambda(t) is electricity price at hour t.
- P_ch(t) is storage charging power.
- P_dis(t) is storage discharging power delivered to the grid.
- SoC(t) is the state of charge.
- P_dir(t) is direct wind power delivered to the grid.
- P_delivered(t) = P_dir(t) + P_dis(t).
- The teacher maximizes sum(P_delivered(t) * lambda(t)) - C.

Because C is fixed for one storage design, maximizing profit is equivalent to
maximizing dispatch revenue and minimizing cost-over-value (COVE).

The mixed-integer part is the charge/discharge mode:
- mode_i = 1 means charging is allowed.
- mode_i = 0 means discharging is allowed.
This prevents charging and discharging at the same time.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
if str(STRATEGY_SRC) not in sys.path:
    sys.path.insert(0, str(STRATEGY_SRC))

import util  # noqa: E402
from classical_strategies import baseload  # noqa: E402


def fixed_costs(config: dict) -> tuple[float, float]:
    """Return no-storage cost and wind+storage cost used in COVE/profit."""
    capex_kw, opex_kw, _ = util.get_storage_specs(
        config["storage_type"], config["storage_rating"], config["storage_duration"]
    )
    rating_kw = config["storage_rating"] * 1000
    wf_rating_kw = config["rated_capacity"] * 1000
    wind_cost = (util.WF_CAPEX * wf_rating_kw * util.FCR) + (util.WF_OPEX * wf_rating_kw)
    storage_cost = config["num_modules"] * ((capex_kw * rating_kw * util.FCR) + (opex_kw * rating_kw))
    return float(wind_cost), float(wind_cost + storage_cost)


def load_power_price(data_path: Path, config: dict, price_mode: str, hours: int | None, offset: int):
    df = pd.read_csv(data_path)
    generation = df["power_generated"].to_numpy(dtype=float)
    raw_price = df["lmp"].to_numpy(dtype=float)
    if price_mode == "normalized":
        price = util.normalize_price(pd.Series(raw_price.copy()), config).to_numpy(dtype=float)
    else:
        price = raw_price
    end = None if hours is None else offset + hours
    return generation[offset:end], price[offset:end]


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


def solve_milp_chunk(
    generation: np.ndarray,
    price: np.ndarray,
    config: dict,
    initial_soc: float,
    final_soc: float | None,
    mip_gap: float,
    time_limit: float | None,
) -> dict[str, np.ndarray | str | float]:
    t_count = len(generation)
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    grid_cap = float(config["rated_capacity"])

    # Variable layout: direct[T], charge[T], discharge[T], soc[T+1], mode[T]
    n = 5 * t_count + 1
    direct0 = 0
    charge0 = t_count
    discharge0 = 2 * t_count
    soc0 = 3 * t_count
    mode0 = 4 * t_count + 1

    def idx_direct(t: int) -> int:
        return direct0 + t

    def idx_charge(t: int) -> int:
        return charge0 + t

    def idx_discharge(t: int) -> int:
        return discharge0 + t

    def idx_soc(t: int) -> int:
        return soc0 + t

    def idx_mode(t: int) -> int:
        return mode0 + t

    # Maximize sum(price * (direct + discharge)). SciPy minimizes, so negate it.
    # Here discharge is P_dis(t): power delivered from storage to the grid.
    c = np.zeros(n)
    for t in range(t_count):
        c[idx_direct(t)] = -price[t]
        c[idx_discharge(t)] = -price[t]

    lb = np.zeros(n)
    ub = np.full(n, np.inf)
    ub[direct0 : direct0 + t_count] = grid_cap
    ub[charge0 : charge0 + t_count] = rating
    ub[discharge0 : discharge0 + t_count] = rating
    ub[soc0 : soc0 + t_count + 1] = capacity
    ub[mode0 : mode0 + t_count] = 1.0

    integrality = np.zeros(n)
    integrality[mode0 : mode0 + t_count] = 1

    # Inequalities:
    # 1. direct + charge <= generation
    # 2. direct + discharge <= grid cap
    # 3. charge <= rating*mode
    # 4. discharge <= rating*(1-mode)
    # 5. discharge/RTE <= SoC, so discharge cannot empty more than is available.
    a_ub = lil_matrix((5 * t_count, n))
    b_ub = np.zeros(5 * t_count)
    for t in range(t_count):
        row = 5 * t
        a_ub[row, idx_direct(t)] = 1.0
        a_ub[row, idx_charge(t)] = 1.0
        b_ub[row] = generation[t]

        row = 5 * t + 1
        a_ub[row, idx_direct(t)] = 1.0
        a_ub[row, idx_discharge(t)] = 1.0
        b_ub[row] = grid_cap

        row = 5 * t + 2
        a_ub[row, idx_charge(t)] = 1.0
        a_ub[row, idx_mode(t)] = -rating
        b_ub[row] = 0.0

        row = 5 * t + 3
        a_ub[row, idx_discharge(t)] = 1.0
        a_ub[row, idx_mode(t)] = rating
        b_ub[row] = rating

        row = 5 * t + 4
        a_ub[row, idx_discharge(t)] = 1.0 / rte
        a_ub[row, idx_soc(t)] = -1.0
        b_ub[row] = 0.0

    # Equalities: initial/final SOC and storage dynamics.
    eq_rows = t_count + 1 + int(final_soc is not None)
    a_eq = lil_matrix((eq_rows, n))
    b_eq = np.zeros(eq_rows)
    eq_row = 0
    a_eq[eq_row, idx_soc(0)] = 1.0
    b_eq[eq_row] = initial_soc
    eq_row += 1
    if final_soc is not None:
        a_eq[eq_row, idx_soc(t_count)] = 1.0
        b_eq[eq_row] = final_soc
        eq_row += 1
    for t in range(t_count):
        a_eq[eq_row, idx_soc(t + 1)] = 1.0
        a_eq[eq_row, idx_soc(t)] = -1.0
        a_eq[eq_row, idx_charge(t)] = -1.0
        a_eq[eq_row, idx_discharge(t)] = 1.0 / rte
        eq_row += 1

    constraints = [
        LinearConstraint(a_ub.tocsr(), -np.inf, b_ub),
        LinearConstraint(a_eq.tocsr(), b_eq, b_eq),
    ]
    options = {"disp": False, "mip_rel_gap": mip_gap}
    if time_limit is not None:
        options["time_limit"] = time_limit

    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=constraints,
        options=options,
    )
    if not result.success:
        raise RuntimeError(result.message)

    x = result.x
    direct = x[direct0 : direct0 + t_count]
    charge = x[charge0 : charge0 + t_count]
    discharge = x[discharge0 : discharge0 + t_count]
    soc = x[soc0 : soc0 + t_count]
    final_soc_value = x[idx_soc(t_count)]
    mode = x[mode0 : mode0 + t_count]
    released = direct + discharge
    action = np.clip((discharge - charge) / rating, -1.0, 1.0)
    return {
        "solver": "scipy-milp",
        "objective": float(result.fun),
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "soc": soc,
        "final_soc": float(final_soc_value),
        "mode": mode,
        "released": released,
        "action": action,
    }


def make_labels(generation: np.ndarray, price: np.ndarray, config: dict, solution: dict) -> pd.DataFrame:
    baseload_released, *_ = baseload(
        generation,
        config["storage_rating"] * config["num_modules"],
        config["storage_rating"] * config["storage_duration"] * config["num_modules"],
        util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]),
    )
    labels = pd.DataFrame(
        {
            "power_generated": generation,
            "price": price,
            "milp_release": solution["released"],
            "milp_direct": solution["direct"],
            "milp_charge": solution["charge"],
            "milp_discharge": solution["discharge"],
            "milp_discharge_before_rte": solution["discharge"] / util.get_rte(
                config["storage_type"], config["storage_rating"], config["storage_duration"]
            ),
            "milp_storage": solution["soc"],
            "milp_mode_binary_charge": solution["mode"],
            "milp_action": solution["action"],
            "baseload_release": baseload_released,
        }
    )
    labels["milp_curtailment"] = np.maximum(
        0.0,
        labels["power_generated"] - labels["milp_direct"] - labels["milp_charge"],
    )
    # Backward-compatible names so train_teacher_policy.py can use these labels directly.
    labels["optimal_release"] = labels["milp_release"]
    labels["optimal_direct"] = labels["milp_direct"]
    labels["optimal_charge"] = labels["milp_charge"]
    labels["optimal_discharge_before_rte"] = labels["milp_discharge_before_rte"]
    labels["optimal_discharge"] = labels["milp_discharge"]
    labels["optimal_storage"] = labels["milp_storage"]
    labels["optimal_curtailment"] = labels["milp_curtailment"]
    return labels


def solve_chunked(generation: np.ndarray, price: np.ndarray, config: dict, chunk_hours: int, mip_gap: float, time_limit: float | None):
    chunks = []
    for start in range(0, len(generation), chunk_hours):
        end = min(start + chunk_hours, len(generation))
        print(f"MILP optimizing hours {start}-{end - 1}", flush=True)
        solution = solve_milp_chunk(generation[start:end], price[start:end], config, 0.0, 0.0, mip_gap, time_limit)
        chunks.append(make_labels(generation[start:end], price[start:end], config, solution))
    return pd.concat(chunks, ignore_index=True)


def solve_chunked_chronological(
    generation: np.ndarray,
    price: np.ndarray,
    config: dict,
    chunk_hours: int,
    initial_soc: float,
    enforce_final_initial: bool,
    mip_gap: float,
    time_limit: float | None,
):
    chunks = []
    current_soc = initial_soc
    for start in range(0, len(generation), chunk_hours):
        end = min(start + chunk_hours, len(generation))
        is_last = end == len(generation)
        final_soc = initial_soc if enforce_final_initial and is_last else None
        print(
            f"MILP optimizing chronological hours {start}-{end - 1} "
            f"with initial SoC {current_soc:.3f}",
            flush=True,
        )
        solution = solve_milp_chunk(
            generation[start:end],
            price[start:end],
            config,
            current_soc,
            final_soc,
            mip_gap,
            time_limit,
        )
        chunks.append(make_labels(generation[start:end], price[start:end], config, solution))
        current_soc = float(solution["final_soc"])
    return pd.concat(chunks, ignore_index=True)


def summarize(labels: pd.DataFrame, config: dict) -> dict[str, float]:
    price = labels["price"].to_numpy(dtype=float)
    generation = labels["power_generated"].to_numpy(dtype=float)
    milp_release = labels["milp_release"].to_numpy(dtype=float)
    baseload_release = labels["baseload_release"].to_numpy(dtype=float)

    wind_cost, dispatch_cost = fixed_costs(config)
    generation_revenue = util.revenue(generation, price)
    baseload_revenue = util.revenue(baseload_release, price)
    milp_revenue = util.revenue(milp_release, price)

    ntg_profit = generation_revenue - wind_cost
    baseload_profit = baseload_revenue - dispatch_cost
    milp_profit = milp_revenue - dispatch_cost

    return {
        "hours": float(len(labels)),
        "generation_revenue": float(generation_revenue),
        "baseload_revenue": float(baseload_revenue),
        "milp_revenue": float(milp_revenue),
        "wind_cost_c_ntg": float(wind_cost),
        "dispatch_cost_c": float(dispatch_cost),
        "ntg_profit_sum_gi_pi_minus_c_ntg": float(ntg_profit),
        "baseload_profit_sum_di_pi_minus_c": float(baseload_profit),
        "milp_profit_sum_di_pi_minus_c": float(milp_profit),
        "ntg_cove_c_over_sum_gi_pi": float(wind_cost / generation_revenue),
        "baseload_cove": cove_value(baseload_release, price, config),
        "milp_cove": cove_value(milp_release, price, config),
        "milp_cove_improvement_vs_baseload_pct": float((cove_value(baseload_release, price, config) - cove_value(milp_release, price, config)) / cove_value(baseload_release, price, config) * 100),
        "mean_action": float(labels["milp_action"].mean()),
        "max_storage": float(labels["milp_storage"].max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create mixed-integer dispatch teacher labels.")
    parser.add_argument("--data", default=str(REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"))
    parser.add_argument("--config", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"))
    parser.add_argument("--hours", type=int, default=168)
    parser.add_argument("--all-data", action="store_true")
    parser.add_argument("--chunk-hours", type=int, default=168)
    parser.add_argument("--chronological", action="store_true")
    parser.add_argument("--initial-soc", type=float, default=0.0)
    parser.add_argument("--no-final-soc-constraint", action="store_true")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--price-mode", choices=["normalized", "raw"], default="normalized")
    parser.add_argument("--mip-gap", type=float, default=0.0)
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--out", default=str(REPO_ROOT / "strategy_model" / "optimization" / "milp_teacher_labels_run_016.csv"))
    parser.add_argument("--summary-out", default=str(REPO_ROOT / "strategy_model" / "optimization" / "milp_teacher_summary_run_016.csv"))
    args = parser.parse_args()

    config = util.load_config(args.config)
    hours = None if args.all_data else args.hours
    generation, price = load_power_price(Path(args.data), config, args.price_mode, hours, args.offset)

    enforce_final_initial = not args.no_final_soc_constraint

    if args.all_data and args.chronological:
        labels = solve_chunked_chronological(
            generation,
            price,
            config,
            args.chunk_hours,
            args.initial_soc,
            enforce_final_initial,
            args.mip_gap,
            args.time_limit,
        )
    elif args.all_data:
        labels = solve_chunked(generation, price, config, args.chunk_hours, args.mip_gap, args.time_limit)
    else:
        final_soc = args.initial_soc if enforce_final_initial else None
        solution = solve_milp_chunk(generation, price, config, args.initial_soc, final_soc, args.mip_gap, args.time_limit)
        labels = make_labels(generation, price, config, solution)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(out, index=False)

    summary = summarize(labels, config)
    summary_out = Path(args.summary_out)
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(summary_out, index=False)

    print("solver: scipy-milp")
    print(f"hours optimized: {int(summary['hours'])}")
    print(f"MILP COVE: {summary['milp_cove']:.6f}")
    print(f"Baseload COVE: {summary['baseload_cove']:.6f}")
    print(f"MILP improvement vs baseload: {summary['milp_cove_improvement_vs_baseload_pct']:.2f}%")
    print(f"sum(g_i*p_i)-C_NTG: {summary['ntg_profit_sum_gi_pi_minus_c_ntg']:.3f}")
    print(f"sum(d_i*p_i)-C: {summary['milp_profit_sum_di_pi_minus_c']:.3f}")
    print(f"labels saved to: {out}")
    print(f"summary saved to: {summary_out}")


if __name__ == "__main__":
    main()
