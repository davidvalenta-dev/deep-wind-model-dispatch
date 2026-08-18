#!/usr/bin/env python3
"""Validate and freeze the controlled Step 0-4 experiment ladder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[2]
REU = REPO / "Summer 2026 REU"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def near(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return bool(np.isclose(float(left), float(right), rtol=0.0, atol=tolerance))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=REU / "results" / "final_controlled_ladder")
    args = parser.parse_args()

    step0 = pd.read_csv(
        REU
        / "100 MW baseload/results/frozen_controlled/constant_output_baseload_100mw_2014_2023_summary.csv"
    )
    step2 = pd.read_csv(
        REU
        / "rolling horizon/results/controlled_hourly_nowcast_from_knobs/controlled_single_forecast_horizon_summary.csv"
    )
    step3 = pd.read_csv(
        REU / "different scenarios/results/frozen_controlled/uncertainty_aware_summary.csv"
    )
    step4 = pd.read_csv(
        REU / "oracle upper bound/results/frozen_controlled/forecast_dispatch_summary.csv"
    )
    oracle = step4[step4["method"].eq("oracle")].copy()

    require(len(step0) == 1, "Step 0 must contain exactly one full-period benchmark row.")
    require(len(step2) == 4, "Step 2 must contain 24/48/72/168-hour rows.")
    require(set(step2["horizon_hours"].astype(int)) == {24, 48, 72, 168}, "Step 2 horizons drifted.")
    require(len(step3) == 5, "Step 3 must contain 1/3/5/7/10-forecast rows.")
    require(len(oracle) == 4, "Step 4 must contain four Oracle horizons.")

    benchmark_revenue = float(step0.iloc[0]["normalized_revenue_metric"])
    benchmark_cove = float(step0.iloc[0]["normalized_cove_index"])
    require(near(step0.iloc[0]["initial_soc_mwh"], 600.0), "Step 0 initial SoC is not 600 MWh.")
    require(near(step0.iloc[0]["final_soc_mwh"], 600.0), "Step 0 final SoC is not 600 MWh.")
    require(int(step0.iloc[0]["qa_total_violation_count"]) == 0, "Step 0 physical QA failed.")

    for name, frame, benchmark_column, cove_column in [
        ("Step 2", step2, "100mw_baseload_revenue", "100mw_baseload_cove"),
        ("Step 3", step3, "100mw_baseload_revenue", "100mw_baseload_cove"),
        ("Step 4", oracle, "constant_output_100mw_revenue_metric", "constant_output_100mw_cove"),
    ]:
        require(frame[benchmark_column].map(lambda value: near(value, benchmark_revenue)).all(), f"{name} benchmark revenue drifted.")
        require(frame[cove_column].map(lambda value: near(value, benchmark_cove)).all(), f"{name} benchmark COVE drifted.")
        require(frame["final_soc"].map(lambda value: near(value, 600.0)).all(), f"{name} final SoC is not 600 MWh.")
        require((pd.to_numeric(frame["annual_soc_target_violation_count"]) == 0).all(), f"{name} annual SoC QA failed.")
        require((pd.to_numeric(frame["final_soc_target_violation_count"]) == 0).all(), f"{name} final SoC QA failed.")

    require((pd.to_numeric(step2["qa_total_violation_count"]) == 0).all(), "Step 2 physical QA failed.")
    require((pd.to_numeric(step3["qa_total_violation_count"]) == 0).all(), "Step 3 physical QA failed.")
    physical_step4 = [
        "max_wind_only_violation",
        "max_delivered_definition_violation",
        "max_grid_violation",
        "max_charge_limit_violation",
        "max_discharge_limit_violation",
        "max_available_energy_violation",
        "max_soc_update_violation",
        "max_soc_lower_violation",
        "max_soc_upper_violation",
    ]
    require(
        max(float(pd.to_numeric(oracle[column]).abs().max()) for column in physical_step4) <= 1e-5,
        "Step 4 physical QA failed.",
    )

    require(
        step2["causal_ridge_forecast_sha256"].astype(str).str.len().eq(64).all(),
        "A Step 2 horizon is missing its forecast fingerprint.",
    )
    require(step3["causal_ridge_forecast_sha256"].nunique() == 1, "Step 3 forecast fingerprint drifted.")

    best2 = step2.loc[step2["cove_reduction_vs_100mw_baseload_pct"].idxmax()]
    single3 = step3[step3["candidate"].str.startswith("single_forecast_recourse")].iloc[0]
    require(
        best2["causal_ridge_forecast_sha256"] == single3["causal_ridge_forecast_sha256"],
        "The selected Step 2 horizon and Step 3 do not use the same frozen forecast.",
    )
    require(int(best2["horizon_hours"]) == int(single3["horizon_hours"]), "Step 3 does not use the Step 2 winning horizon.")
    for column in ["dispatch_revenue", "dispatch_cove_index", "final_soc"]:
        require(near(best2[column], single3[column]), f"Step 2/Step 3 single-forecast mismatch in {column}.")

    rows: list[dict[str, object]] = [
        {
            "step": 0,
            "case": "100 MW constant-output benchmark",
            "information": "realized current wind; price used only for scoring",
            "horizon_hours": 0,
            "scenario_count": 0,
            "revenue_metric": benchmark_revenue,
            "cove": benchmark_cove,
            "cove_reduction_vs_100mw_pct": 0.0,
            "final_soc_mwh": float(step0.iloc[0]["final_soc_mwh"]),
            "qa_violations": int(step0.iloc[0]["qa_total_violation_count"]),
        }
    ]
    for _, row in step2.iterrows():
        rows.append(
            {
                "step": 2,
                "case": "deterministic causal-ridge rolling horizon",
                "information": "one causal-ridge forecast",
                "horizon_hours": int(row["horizon_hours"]),
                "scenario_count": 1,
                "revenue_metric": float(row["dispatch_revenue"]),
                "cove": float(row["dispatch_cove_index"]),
                "cove_reduction_vs_100mw_pct": float(row["cove_reduction_vs_100mw_baseload_pct"]),
                "final_soc_mwh": float(row["final_soc"]),
                "qa_violations": int(row["qa_total_violation_count"]),
            }
        )
    for _, row in step3.iterrows():
        count = 1 if row["candidate"].startswith("single_forecast") else int(row["candidate"].split("_")[0].replace("three", "3").replace("five", "5").replace("seven", "7").replace("ten", "10"))
        rows.append(
            {
                "step": 3,
                "case": "uncertainty-aware scenario rolling horizon",
                "information": "causal-ridge center plus fixed residual quantiles",
                "horizon_hours": int(row["horizon_hours"]),
                "scenario_count": count,
                "revenue_metric": float(row["dispatch_revenue"]),
                "cove": float(row["dispatch_cove_index"]),
                "cove_reduction_vs_100mw_pct": float(row["cove_reduction_vs_100mw_baseload_pct"]),
                "final_soc_mwh": float(row["final_soc"]),
                "qa_violations": int(row["qa_total_violation_count"]),
            }
        )
    for _, row in oracle.iterrows():
        rows.append(
            {
                "step": 4,
                "case": "rolling-window Oracle ceiling",
                "information": "perfect future wind and price inside the window",
                "horizon_hours": int(row["horizon_hours"]),
                "scenario_count": 0,
                "revenue_metric": float(row["revenue_metric"]),
                "cove": float(row["cove"]),
                "cove_reduction_vs_100mw_pct": float(row["cove_improvement_vs_100mw_baseload_pct"]),
                "final_soc_mwh": float(row["final_soc"]),
                "qa_violations": 0,
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.DataFrame(rows)
    manifest.to_csv(args.out_dir / "final_controlled_ladder_manifest.csv", index=False)
    audit = {
        "status": "PASS",
        "evaluation_period": [str(step2.iloc[0]["test_start"]), str(step2.iloc[0]["test_end"])],
        "hours": int(step2.iloc[0]["hours"]),
        "execution_step_hours": 1,
        "replanning_interval_hours": 1,
        "annual_and_final_soc_target_mwh": 600.0,
        "benchmark_revenue_metric": benchmark_revenue,
        "benchmark_cove": benchmark_cove,
        "causal_ridge_forecast_sha256": str(best2["causal_ridge_forecast_sha256"]),
        "step2_winning_horizon_hours": int(best2["horizon_hours"]),
        "step2_step3_single_forecast_exact_match": True,
    }
    (args.out_dir / "final_controlled_ladder_QA.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(manifest.to_string(index=False))
    print(f"\nPASS: {args.out_dir / 'final_controlled_ladder_QA.json'}")


if __name__ == "__main__":
    main()
