"""Create an optimization benchmark/teacher for wind-storage dispatch.

This script solves a deterministic dispatch problem:

    given wind power, prices, and storage limits,
    choose how much power to sell now, store, or release later.

It uses gurobipy when Gurobi is installed. If Gurobi is not available, it falls
back to scipy.optimize.linprog so the benchmark can still be run locally.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
if str(STRATEGY_SRC) not in sys.path:
    sys.path.insert(0, str(STRATEGY_SRC))

import util  # noqa: E402
from classical_strategies import baseload  # noqa: E402


def load_power_price(csv_path: Path, config: dict, limit: int | None, offset: int) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)
    power = df["power_generated"].to_numpy(dtype=float)
    price = df["lmp"].copy()
    price = util.normalize_price(price, config).to_numpy(dtype=float)
    end = None if limit is None else offset + limit
    return power[offset:end], price[offset:end]


def cove_for(power: np.ndarray, price: np.ndarray, config: dict) -> float:
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


def solve_with_gurobi(
    generation: np.ndarray,
    price: np.ndarray,
    rating: float,
    capacity: float,
    rte: float,
    grid_cap: float,
    final_soc_equals_initial: bool = True,
) -> dict[str, np.ndarray | str]:
    import gurobipy as gp
    from gurobipy import GRB

    t_count = len(generation)
    model = gp.Model("wind_storage_dispatch_teacher")
    model.Params.OutputFlag = 0

    direct = model.addVars(t_count, lb=0.0, name="direct")
    charge = model.addVars(t_count, lb=0.0, ub=rating, name="charge")
    discharge = model.addVars(t_count, lb=0.0, ub=rating, name="discharge")
    soc = model.addVars(t_count + 1, lb=0.0, ub=capacity, name="soc")
    charging = model.addVars(t_count, vtype=GRB.BINARY, name="charging")

    model.addConstr(soc[0] == 0.0, name="initial_soc")
    if final_soc_equals_initial:
        model.addConstr(soc[t_count] == 0.0, name="final_soc")

    for t in range(t_count):
        model.addConstr(direct[t] + charge[t] <= float(generation[t]), name=f"wind_only_charge_{t}")
        model.addConstr(charge[t] <= rating * charging[t], name=f"charge_mode_{t}")
        model.addConstr(discharge[t] <= rating * (1 - charging[t]), name=f"discharge_mode_{t}")
        model.addConstr(direct[t] + rte * discharge[t] <= grid_cap, name=f"grid_cap_{t}")
        model.addConstr(soc[t + 1] == soc[t] + charge[t] - discharge[t], name=f"soc_{t}")

    model.setObjective(
        gp.quicksum(price[t] * (direct[t] + rte * discharge[t]) for t in range(t_count)),
        GRB.MAXIMIZE,
    )
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not find an optimal solution. Status={model.Status}")

    return {
        "solver": "gurobi",
        "direct": np.array([direct[t].X for t in range(t_count)]),
        "charge": np.array([charge[t].X for t in range(t_count)]),
        "discharge": np.array([discharge[t].X for t in range(t_count)]),
        "soc": np.array([soc[t].X for t in range(t_count)]),
        "released": np.array([direct[t].X + rte * discharge[t].X for t in range(t_count)]),
    }


def solve_with_scipy(
    generation: np.ndarray,
    price: np.ndarray,
    rating: float,
    capacity: float,
    rte: float,
    grid_cap: float,
    final_soc_equals_initial: bool = True,
) -> dict[str, np.ndarray | str]:
    """Linear-program fallback.

    This is an LP relaxation: it does not include Gurobi's binary charge/discharge
    mode variable. It is still useful as a deterministic teacher benchmark when
    Gurobi is not installed.
    """
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix

    t_count = len(generation)
    n = 4 * t_count + 1

    def idx_direct(t: int) -> int:
        return t

    def idx_charge(t: int) -> int:
        return t_count + t

    def idx_discharge(t: int) -> int:
        return 2 * t_count + t

    def idx_soc(t: int) -> int:
        return 3 * t_count + t

    c = np.zeros(n)
    for t in range(t_count):
        c[idx_direct(t)] = -price[t]
        c[idx_discharge(t)] = -(price[t] * rte)

    bounds = []
    for _ in range(t_count):
        bounds.append((0.0, None))
    for _ in range(t_count):
        bounds.append((0.0, rating))
    for _ in range(t_count):
        bounds.append((0.0, rating))
    for _ in range(t_count + 1):
        bounds.append((0.0, capacity))

    a_ub = lil_matrix((2 * t_count, n))
    b_ub = np.zeros(2 * t_count)
    for t in range(t_count):
        row = 2 * t
        a_ub[row, idx_direct(t)] = 1.0
        a_ub[row, idx_charge(t)] = 1.0
        b_ub[row] = generation[t]

        row = 2 * t + 1
        a_ub[row, idx_direct(t)] = 1.0
        a_ub[row, idx_discharge(t)] = rte
        b_ub[row] = grid_cap

    eq_rows = t_count + 1 + int(final_soc_equals_initial)
    a_eq = lil_matrix((eq_rows, n))
    b_eq = np.zeros(eq_rows)
    eq_row = 0
    a_eq[eq_row, idx_soc(0)] = 1.0
    eq_row += 1

    if final_soc_equals_initial:
        a_eq[eq_row, idx_soc(t_count)] = 1.0
        eq_row += 1

    for t in range(t_count):
        a_eq[eq_row, idx_soc(t + 1)] = 1.0
        a_eq[eq_row, idx_soc(t)] = -1.0
        a_eq[eq_row, idx_charge(t)] = -1.0
        a_eq[eq_row, idx_discharge(t)] = 1.0
        eq_row += 1

    result = linprog(
        c,
        A_ub=a_ub.tocsr(),
        b_ub=b_ub,
        A_eq=a_eq.tocsr(),
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(result.message)

    x = result.x
    direct = np.array([x[idx_direct(t)] for t in range(t_count)])
    charge = np.array([x[idx_charge(t)] for t in range(t_count)])
    discharge = np.array([x[idx_discharge(t)] for t in range(t_count)])
    soc = np.array([x[idx_soc(t)] for t in range(t_count)])
    released = direct + rte * discharge
    return {
        "solver": "scipy-linprog",
        "direct": direct,
        "charge": charge,
        "discharge": discharge,
        "soc": soc,
        "released": released,
    }


def make_labels(
    generation: np.ndarray,
    price: np.ndarray,
    config: dict,
    solution: dict[str, np.ndarray | str],
) -> pd.DataFrame:
    rte = util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"])
    baseload_released, *_ = baseload(
        generation,
        config["storage_rating"] * config["num_modules"],
        config["storage_rating"] * config["storage_duration"] * config["num_modules"],
        rte,
    )

    labels = pd.DataFrame(
        {
            "power_generated": generation,
            "price": price,
            "optimal_release": solution["released"],
            "optimal_direct": solution["direct"],
            "optimal_charge": solution["charge"],
            "optimal_discharge_before_rte": solution["discharge"],
            "optimal_storage": solution["soc"],
            "baseload_release": baseload_released,
        }
    )
    labels["optimal_curtailment"] = np.maximum(
        0.0,
        labels["power_generated"] - labels["optimal_direct"] - labels["optimal_charge"],
    )
    return labels


def solve_chunked(
    generation: np.ndarray,
    price: np.ndarray,
    config: dict,
    solver: str,
    chunk_hours: int,
) -> tuple[pd.DataFrame, str]:
    label_chunks = []
    used_solver = "unknown"
    for start in range(0, len(generation), chunk_hours):
        end = min(start + chunk_hours, len(generation))
        print(f"optimizing hours {start}-{end - 1}")
        solution = solve_dispatch(generation[start:end], price[start:end], config, solver, True)
        used_solver = str(solution["solver"])
        label_chunks.append(make_labels(generation[start:end], price[start:end], config, solution))
    return pd.concat(label_chunks, ignore_index=True), used_solver


def solve_dispatch(
    generation: np.ndarray,
    price: np.ndarray,
    config: dict,
    solver: str,
    final_soc_equals_initial: bool,
) -> dict[str, np.ndarray | str]:
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    grid_cap = float(config["rated_capacity"])

    if solver in {"auto", "gurobi"}:
        try:
            return solve_with_gurobi(generation, price, rating, capacity, rte, grid_cap, final_soc_equals_initial)
        except ModuleNotFoundError:
            if solver == "gurobi":
                raise
            print("gurobipy is not installed; using scipy linprog fallback.")

    return solve_with_scipy(generation, price, rating, capacity, rte, grid_cap, final_soc_equals_initial)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an optimized dispatch benchmark/teacher dataset.")
    parser.add_argument("--data", default=str(REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"))
    parser.add_argument("--config", default=str(STRATEGY_SRC / "configs" / "config.yaml"))
    parser.add_argument("--hours", type=int, default=168, help="Number of hours to optimize.")
    parser.add_argument("--all-data", action="store_true", help="Optimize all rows in the dataset.")
    parser.add_argument("--chunk-hours", type=int, default=8760, help="Hours per chunk when using --all-data.")
    parser.add_argument("--offset", type=int, default=0, help="Start row in the dataset.")
    parser.add_argument("--solver", choices=["auto", "gurobi", "scipy"], default="auto")
    parser.add_argument("--allow-final-soc", action="store_true", help="Do not force final storage to return to zero.")
    parser.add_argument("--out", default=str(REPO_ROOT / "strategy_model" / "optimization" / "dispatch_teacher_labels.csv"))
    args = parser.parse_args()

    config = util.load_config(args.config)
    generation, price = load_power_price(
        Path(args.data),
        config,
        None if args.all_data else args.hours,
        args.offset,
    )

    rte = util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"])
    baseload_released, *_ = baseload(
        generation,
        config["storage_rating"] * config["num_modules"],
        config["storage_rating"] * config["storage_duration"] * config["num_modules"],
        rte,
    )

    if args.all_data:
        labels, used_solver = solve_chunked(generation, price, config, args.solver, args.chunk_hours)
        released = labels["optimal_release"].to_numpy(dtype=float)
    else:
        solution = solve_dispatch(generation, price, config, args.solver, not args.allow_final_soc)
        used_solver = str(solution["solver"])
        released = solution["released"]
        assert isinstance(released, np.ndarray)
        labels = make_labels(generation, price, config, solution)

    optimized_cove = cove_for(released, price, config)
    baseload_cove = cove_for(baseload_released, price, config)
    optimized_revenue = util.revenue(released, price)
    baseload_revenue = util.revenue(baseload_released, price)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(out, index=False)

    print(f"solver: {used_solver}")
    print(f"hours optimized: {len(generation)}")
    print(
        "storage:",
        f"{config['storage_type']}, {config['storage_rating']} MW,",
        f"{config['storage_duration']} h, RTE={rte:.3f}",
    )
    print(f"optimized revenue: {optimized_revenue:.3f}")
    print(f"baseload revenue: {baseload_revenue:.3f}")
    print(f"optimized COVE: {optimized_cove:.6f}")
    print(f"baseload COVE: {baseload_cove:.6f}")
    print(f"COVE improvement vs baseload: {(baseload_cove - optimized_cove) / baseload_cove * 100:.2f}%")
    print(f"teacher labels saved to: {out}")


if __name__ == "__main__":
    main()
