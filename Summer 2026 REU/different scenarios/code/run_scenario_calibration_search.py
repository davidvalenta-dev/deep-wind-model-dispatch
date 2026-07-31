#!/usr/bin/env python3
"""Calibrate scenario definitions, then test them out-of-sample.

This does NOT replace RUN_3_SCENARIO_COMPARISON.py. It searches alternative
3/5/7/10 scenario quantile/weight choices on a validation period and then
scores the best choices on a later test period.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
import run_uncertainty_aware_dispatch as scen  # noqa: E402
import run_nora_matching_forecast_horizons as base  # noqa: E402


def normalize(weights):
    w = np.asarray(weights, dtype=float)
    return w / w.sum()


def make_specs() -> dict[str, dict]:
    specs: dict[str, dict] = {}
    # Near-center candidates test whether a light amount of uncertainty can
    # improve the Step 2 single-forecast controller without becoming too
    # conservative.
    five_near_center_templates = {
        "tiny_center_96": (
            [0.50, 0.45, 0.55, 0.50, 0.50],
            [0.50, 0.55, 0.45, 0.45, 0.55],
            [0.96, 0.01, 0.01, 0.01, 0.01],
        ),
        "tiny_center_90": (
            [0.50, 0.40, 0.60, 0.50, 0.50],
            [0.50, 0.60, 0.40, 0.40, 0.60],
            [0.90, 0.025, 0.025, 0.025, 0.025],
        ),
        "mild_center_80": (
            [0.50, 0.35, 0.65, 0.50, 0.50],
            [0.50, 0.65, 0.35, 0.35, 0.65],
            [0.80, 0.05, 0.05, 0.05, 0.05],
        ),
        "price_up_tiny": (
            [0.50, 0.50, 0.50, 0.50, 0.50],
            [0.50, 0.55, 0.60, 0.45, 0.40],
            [0.90, 0.04, 0.03, 0.02, 0.01],
        ),
    }
    for name, (wq, pq, weights) in five_near_center_templates.items():
        specs[f"s5_{name}"] = {
            "scenario_count": 5,
            "weights": normalize(weights),
            "wind_quantiles": wq,
            "price_quantiles": pq,
            "risk_lambda": 0.0,
        }

    weight_sets_3 = {
        "w802": [0.80, 0.10, 0.10],
        "w602": [0.60, 0.20, 0.20],
        "w5025": [0.50, 0.25, 0.25],
        "weq": [1/3, 1/3, 1/3],
        "w901": [0.90, 0.05, 0.05],
    }
    q_pairs = {
        "mild": (0.40, 0.60),
        "mid": (0.25, 0.75),
        "wide": (0.10, 0.90),
        "extreme": (0.05, 0.95),
    }
    modes = ["price_only", "wind_only", "paired", "opportunity"]
    for qname, (lo, hi) in q_pairs.items():
        for wname, weights in weight_sets_3.items():
            for mode in modes:
                if mode == "price_only":
                    wind_q = [0.50, 0.50, 0.50]
                    price_q = [0.50, lo, hi]
                elif mode == "wind_only":
                    wind_q = [0.50, lo, hi]
                    price_q = [0.50, 0.50, 0.50]
                elif mode == "paired":
                    wind_q = [0.50, lo, hi]
                    price_q = [0.50, hi, lo]
                else:  # opportunity: high price futures emphasized without widening wind as much
                    wind_q = [0.50, 0.50, hi]
                    price_q = [0.50, hi, hi]
                specs[f"s3_{mode}_{qname}_{wname}"] = {
                    "scenario_count": 3,
                    "weights": normalize(weights),
                    "wind_quantiles": wind_q,
                    "price_quantiles": price_q,
                    "risk_lambda": 0.0,
                }

    # Build 5/7/10 scenario sets from the same calibrated families.
    five_templates = {
        "mild_balanced": ([0.50,0.40,0.60,0.50,0.50], [0.50,0.60,0.40,0.40,0.60], [0.50,0.125,0.125,0.125,0.125]),
        "mid_center": ([0.50,0.25,0.75,0.50,0.50], [0.50,0.75,0.25,0.25,0.75], [0.60,0.10,0.10,0.10,0.10]),
        "wide_center": ([0.50,0.10,0.90,0.50,0.50], [0.50,0.90,0.10,0.10,0.90], [0.60,0.10,0.10,0.10,0.10]),
        "price_up": ([0.50,0.50,0.50,0.50,0.50], [0.50,0.75,0.90,0.60,0.40], [0.55,0.15,0.10,0.10,0.10]),
        "opportunity": ([0.50,0.50,0.75,0.50,0.90], [0.50,0.75,0.75,0.90,0.90], [0.55,0.15,0.10,0.10,0.10]),
    }
    for name,(wq,pq,weights) in five_templates.items():
        specs[f"s5_{name}"] = {"scenario_count":5,"weights":normalize(weights),"wind_quantiles":wq,"price_quantiles":pq,"risk_lambda":0.0}

    seven_templates = {
        "mid_center": ([0.50,0.25,0.75,0.25,0.75,0.50,0.50], [0.50,0.75,0.25,0.25,0.75,0.75,0.25], [0.46,0.09,0.09,0.09,0.09,0.09,0.09]),
        "wide_center": ([0.50,0.10,0.90,0.10,0.90,0.25,0.75], [0.50,0.90,0.10,0.10,0.90,0.75,0.25], [0.46,0.09,0.09,0.09,0.09,0.09,0.09]),
        "price_up": ([0.50]*7, [0.50,0.60,0.70,0.80,0.90,0.40,0.25], [0.46,0.10,0.10,0.10,0.10,0.07,0.07]),
        "opportunity": ([0.50,0.50,0.75,0.90,0.50,0.75,0.90], [0.50,0.75,0.75,0.75,0.90,0.90,0.90], [0.46,0.10,0.09,0.08,0.10,0.09,0.08]),
    }
    for name,(wq,pq,weights) in seven_templates.items():
        specs[f"s7_{name}"] = {"scenario_count":7,"weights":normalize(weights),"wind_quantiles":wq,"price_quantiles":pq,"risk_lambda":0.0}

    ten_templates = {
        "mid_center": ([0.50,0.25,0.75,0.25,0.75,0.40,0.60,0.40,0.60,0.50], [0.50,0.75,0.25,0.25,0.75,0.60,0.40,0.40,0.60,0.90], [0.34,0.08,0.08,0.08,0.08,0.07,0.07,0.07,0.07,0.06]),
        "wide_center": ([0.50,0.10,0.90,0.10,0.90,0.25,0.75,0.25,0.75,0.50], [0.50,0.90,0.10,0.10,0.90,0.75,0.25,0.25,0.75,0.95], [0.34,0.08,0.08,0.08,0.08,0.07,0.07,0.07,0.07,0.06]),
        "price_up": ([0.50]*10, [0.50,0.60,0.70,0.80,0.90,0.95,0.40,0.30,0.20,0.10], [0.34,0.09,0.09,0.09,0.08,0.07,0.07,0.06,0.06,0.05]),
        "opportunity": ([0.50,0.50,0.60,0.75,0.90,0.50,0.60,0.75,0.90,0.50], [0.50,0.70,0.70,0.80,0.80,0.90,0.90,0.95,0.95,0.60], [0.34,0.09,0.08,0.08,0.07,0.09,0.08,0.07,0.06,0.04]),
    }
    for name,(wq,pq,weights) in ten_templates.items():
        specs[f"s10_{name}"] = {"scenario_count":10,"weights":normalize(weights),"wind_quantiles":wq,"price_quantiles":pq,"risk_lambda":0.0}
    return specs


def configure_base(args):
    base.PS = float(args.storage_power_mw)
    base.DURATION_HOURS = float(args.storage_duration_h)
    base.RTE = float(args.rte)
    base.SQRT_RTE = float(np.sqrt(base.RTE))
    base.DOD = float(args.dod)
    base.CMAX = base.PS * base.DURATION_HOURS
    base.CMIN = base.CMAX * (1.0 - base.DOD)
    base.SOC0 = (base.CMIN + base.CMAX) / 2.0 if args.initial_soc_mwh is None else float(args.initial_soc_mwh)
    base.GRID_CAP = float(args.grid_cap_mw)
    scen.HORIZON = int(args.horizon_hours)


def build_context(args):
    df = pd.read_csv(base.DATA_PATH, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df[["datetime", "power_generated", "lmp", "user_load_zonal"]].dropna().reset_index(drop=True)
    train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64(args.train_end)))

    raw_lmp = df["lmp"].to_numpy(float)
    config = scen.util.load_config(scen.CONFIG_PATH)
    capped_price = np.minimum(raw_lmp, float(config["price_threshold"]))
    training_price_mean = float(capped_price[:train_end].mean())
    df["raw_lmp"] = raw_lmp
    df["lmp"] = capped_price / training_price_mean

    forecast_model_max_horizon = int(args.forecast_model_max_horizon_hours)
    evaluation_cutoff_horizon = int(args.evaluation_cutoff_horizon_hours)
    origins = np.arange(train_end, len(df), int(args.replanning_interval_hours))
    origins = origins[origins + evaluation_cutoff_horizon <= len(df)]
    wind_center, price_center, generation_models, price_models = scen.build_forecasts(
        df,
        train_end,
        origins,
        int(args.train_origin_stride),
        forecast_model_max_horizon,
    )
    needed_quantiles = sorted({q for spec in make_specs().values() for q in spec["wind_quantiles"] + spec["price_quantiles"]})
    quantile_lookup = scen.residual_quantiles(
        df,
        max(base.PAST_LAGS),
        train_end,
        generation_models,
        price_models,
        needed_quantiles,
        method="empirical",
        origin_stride=int(args.residual_origin_stride),
    )
    return df, origins, wind_center, price_center, quantile_lookup


def select_period(df, origins, start, end, max_origins=None):
    dt = df["datetime"].to_numpy()
    mask = np.ones(len(origins), dtype=bool)
    if start:
        mask &= dt[origins] >= np.datetime64(start)
    if end:
        mask &= dt[origins] < np.datetime64(end)
    selected = origins[mask]
    if max_origins is not None:
        selected = selected[: int(max_origins)]
    # return positions into the full origin arrays too
    origin_to_pos = {int(o): i for i, o in enumerate(origins)}
    pos = np.array([origin_to_pos[int(o)] for o in selected], dtype=int)
    return selected, pos


def run_one(df, origins, positions, wind_center, price_center, quantile_lookup, spec_name, spec, args, out_dir, prefix):
    scen.SCENARIO_SPECS = {spec_name: spec}
    selected_origins = origins
    selected_wind = wind_center[positions]
    selected_price = price_center[positions]
    if spec_name == "single_recourse":
        labels = scen.run_single_forecast_recourse(
            df, selected_origins, selected_wind, selected_price, None,
            args.nowcast_first_hour,
            args.gate_margin,
            float(df["power_generated"].iloc[:np.searchsorted(df["datetime"].to_numpy(), np.datetime64(args.train_end))].mean()),
            int(args.execution_step_hours),
            float(args.direct_reserve_mw),
            bool(args.gate_single_forecast),
        )
        suffix = "_nowcast" if args.nowcast_first_hour else ""
        suffix += "_gated" if args.gate_margin is not None else ""
        candidate = f"single_forecast_recourse{suffix}"
        row = scen.summarize(labels, candidate, "causal ridge", "causal ridge price")
    else:
        labels = scen.run_scenario_controller(
            df, selected_origins, selected_wind, selected_price, quantile_lookup, spec_name, None,
            args.nowcast_first_hour,
            args.gate_margin,
            float(df["power_generated"].iloc[:np.searchsorted(df["datetime"].to_numpy(), np.datetime64(args.train_end))].mean()),
            int(args.execution_step_hours),
            float(args.direct_reserve_mw),
        )
        row = scen.summarize(labels, spec_name, f"calibrated wind {spec['wind_quantiles']}", f"calibrated price {spec['price_quantiles']}")
    row["spec_name"] = spec_name
    row["scenario_count"] = 1 if spec_name == "single_recourse" else int(spec["scenario_count"])
    row["period_label"] = prefix
    return row, labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "results" / "calibration_search")
    p.add_argument("--horizon-hours", type=int, default=48)
    p.add_argument("--forecast-model-max-horizon-hours", type=int, default=168)
    p.add_argument("--evaluation-cutoff-horizon-hours", type=int, default=168)
    p.add_argument("--execution-step-hours", type=int, default=24)
    p.add_argument("--replanning-interval-hours", type=int, default=24)
    p.add_argument("--train-origin-stride", type=int, default=24)
    p.add_argument("--residual-origin-stride", type=int, default=24)
    p.add_argument("--train-end", default="2014-01-01")
    p.add_argument("--validation-start", default="2014-01-01")
    p.add_argument("--validation-end", default="2018-01-01")
    p.add_argument("--test-start", default="2018-01-01")
    p.add_argument("--test-end", default="2023-12-23 21:00:00")
    p.add_argument("--max-validation-origins", type=int, default=None)
    p.add_argument("--max-test-origins", type=int, default=None)
    p.add_argument("--storage-power-mw", type=float, default=100.0)
    p.add_argument("--storage-duration-h", type=float, default=10.0)
    p.add_argument("--rte", type=float, default=0.55)
    p.add_argument("--dod", type=float, default=0.8)
    p.add_argument("--grid-cap-mw", type=float, default=249.0)
    p.add_argument("--initial-soc-mwh", type=float, default=None)
    p.add_argument("--direct-reserve-mw", type=float, default=75.0)
    p.add_argument("--fallback-target-mw", type=float, default=100.0)
    p.add_argument("--gate-single-forecast", action="store_true", default=False)
    p.add_argument("--gate-margin", type=float, default=None)
    p.add_argument("--nowcast-first-hour", action="store_true", default=False)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    configure_base(args)
    print("Building forecast/scenario calibration context...", flush=True)
    df, all_origins, wind_center, price_center, quantile_lookup = build_context(args)
    val_origins, val_pos = select_period(df, all_origins, args.validation_start, args.validation_end, args.max_validation_origins)
    test_origins, test_pos = select_period(df, all_origins, args.test_start, args.test_end, args.max_test_origins)
    print(f"Validation origins: {len(val_origins)} from {df['datetime'].iloc[val_origins[0]]} to {df['datetime'].iloc[val_origins[-1]]}", flush=True)
    print(f"Test origins: {len(test_origins)} from {df['datetime'].iloc[test_origins[0]]} to {df['datetime'].iloc[test_origins[-1]]}", flush=True)

    specs = make_specs()
    validation_rows=[]
    single_row, _ = run_one(df, val_origins, val_pos, wind_center, price_center, quantile_lookup, "single_recourse", {}, args, args.out_dir, "validation")
    validation_rows.append(single_row)
    print(f"Validation single: revenue={single_row['dispatch_revenue']:.2f}, COVE={single_row['dispatch_cove_index']:.6f}", flush=True)
    for name, spec in specs.items():
        row, _ = run_one(df, val_origins, val_pos, wind_center, price_center, quantile_lookup, name, spec, args, args.out_dir, "validation")
        validation_rows.append(row)
        print(f"Validation {name}: count={spec['scenario_count']} revenue={row['dispatch_revenue']:.2f}, COVE={row['dispatch_cove_index']:.6f}", flush=True)
    val = pd.DataFrame(validation_rows)
    val.to_csv(args.out_dir / "validation_all_scenario_specs.csv", index=False)

    best_by_count=[]
    for count in [3,5,7,10]:
        subset=val[val["scenario_count"]==count].copy()
        if not subset.empty:
            # choose lowest COVE, then highest revenue
            subset=subset.sort_values(["dispatch_cove_index","dispatch_revenue"], ascending=[True,False])
            best_by_count.append(subset.iloc[0].to_dict())
    best_df=pd.DataFrame(best_by_count)
    best_df.to_csv(args.out_dir / "validation_best_by_scenario_count.csv", index=False)

    test_rows=[]
    single_test, single_labels = run_one(df, test_origins, test_pos, wind_center, price_center, quantile_lookup, "single_recourse", {}, args, args.out_dir, "test")
    test_rows.append(single_test)
    single_labels.to_csv(args.out_dir / "test_single_forecast_labels.csv", index=False)
    for _, best in best_df.iterrows():
        name=str(best["spec_name"])
        row, labels = run_one(df, test_origins, test_pos, wind_center, price_center, quantile_lookup, name, specs[name], args, args.out_dir, "test")
        test_rows.append(row)
        labels.to_csv(args.out_dir / f"test_{name}_labels.csv", index=False)
    test=pd.DataFrame(test_rows).sort_values("dispatch_revenue", ascending=False)
    test.to_csv(args.out_dir / "test_best_calibrated_scenarios.csv", index=False)

    metadata={
        "validation_start": args.validation_start,
        "validation_end": args.validation_end,
        "test_start": args.test_start,
        "test_end": args.test_end,
        "horizon_hours": args.horizon_hours,
        "execution_step_hours": args.execution_step_hours,
        "replanning_interval_hours": args.replanning_interval_hours,
        "storage": {"power_mw": base.PS, "duration_h": base.DURATION_HOURS, "cmin": base.CMIN, "cmax": base.CMAX, "soc0": base.SOC0, "rte": base.RTE, "grid_cap": base.GRID_CAP},
        "best_specs": {str(row["spec_name"]): {k:(v.tolist() if hasattr(v,'tolist') else v) for k,v in specs[str(row["spec_name"])].items()} for _,row in best_df.iterrows()},
        "train_origin_stride": args.train_origin_stride,
        "residual_origin_stride": args.residual_origin_stride,
    }
    (args.out_dir / "calibration_metadata.json").write_text(json.dumps(metadata, indent=2))

    print("\nVALIDATION BEST BY COUNT")
    print(best_df[["scenario_count","spec_name","dispatch_revenue","dispatch_cove_index","revenue_gain_vs_wind_only_pct","cove_reduction_vs_wind_only_pct"]].to_string(index=False))
    print("\nTEST RESULTS FOR CALIBRATED WINNERS")
    print(test[["scenario_count","spec_name","dispatch_revenue","dispatch_cove_index","revenue_gain_vs_wind_only_pct","cove_reduction_vs_wind_only_pct","final_soc"]].to_string(index=False))
    print(f"\nSaved calibration outputs to {args.out_dir}")

if __name__ == "__main__":
    main()
