#!/usr/bin/env python3
"""Merge independently computed Step 3 variants into the canonical result folder."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_nora_matching_forecast_horizons as base
from run_best_forecast_dispatch_search import annualized_wind_only_cost


VARIANT_DIRS = {
    "three_scenario_expected": "parallel_three",
    "five_scenario_expected": "parallel_five",
    "seven_scenario_expected": "parallel_seven",
    "ten_scenario_expected": "parallel_ten",
}


def normalize_cove_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Recompute every COVE field with the frozen 100 MW / 10 h cost model."""
    result = frame.copy()
    dispatch_cost = base.annualized_dispatch_cost()
    wind_cost = annualized_wind_only_cost()
    result["dispatch_cove_index"] = dispatch_cost / result["dispatch_revenue"]
    result["annualized_dispatch_cost_usd"] = dispatch_cost
    result["baseload_cove_index"] = dispatch_cost / result["baseload_revenue"]
    result["wind_only_cove_index"] = wind_cost / result["wind_only_revenue"]
    result["100mw_baseload_cove"] = dispatch_cost / result["100mw_baseload_revenue"]
    result["cove_reduction_vs_baseload_pct"] = (
        1.0 - result["dispatch_cove_index"] / result["baseload_cove_index"]
    ) * 100.0
    result["cove_reduction_vs_wind_only_pct"] = (
        1.0 - result["dispatch_cove_index"] / result["wind_only_cove_index"]
    ) * 100.0
    result["cove_reduction_vs_100mw_baseload_pct"] = (
        1.0 - result["dispatch_cove_index"] / result["100mw_baseload_cove"]
    ) * 100.0
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parallel-root", type=Path, required=True)
    parser.add_argument("--step2-horizon-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[pd.DataFrame] = []

    step2_summary = pd.read_csv(args.step2_horizon_dir / "uncertainty_aware_summary.csv")
    single = step2_summary[
        step2_summary["candidate"].str.startswith("single_forecast_recourse")
    ].copy()
    if len(single) != 1:
        raise RuntimeError("Expected exactly one Step 2 single-forecast row.")
    rows.append(single)

    single_labels = args.step2_horizon_dir / "single_forecast_recourse_nowcast_gated_labels.csv"
    if not single_labels.exists():
        raise FileNotFoundError(single_labels)
    shutil.copy2(single_labels, args.out_dir / single_labels.name)

    for variant, directory in VARIANT_DIRS.items():
        source_dir = args.parallel_root / directory
        summary_file = source_dir / "uncertainty_aware_summary.csv"
        if not summary_file.exists():
            raise FileNotFoundError(summary_file)
        summary = pd.read_csv(summary_file)
        selected = summary[summary["candidate"].str.startswith(variant)].copy()
        if len(selected) != 1:
            raise RuntimeError(f"Expected exactly one summary row for {variant}.")
        rows.append(selected)

        labels = source_dir / f"{variant}_nowcast_gated_labels.csv"
        if not labels.exists():
            raise FileNotFoundError(labels)
        shutil.copy2(labels, args.out_dir / labels.name)

        if directory == "parallel_three":
            for shared_name in ["experiment_metadata.json", "forecast_matrices.npz"]:
                shared = source_dir / shared_name
                if shared.exists():
                    shutil.copy2(shared, args.out_dir / shared.name)

    merged = normalize_cove_metrics(pd.concat(rows, ignore_index=True, sort=False))
    qa_columns = [
        "annual_soc_target_violation_count",
        "final_soc_target_violation_count",
        "qa_total_violation_count",
    ]
    failures = {
        column: int(pd.to_numeric(merged[column], errors="raise").sum())
        for column in qa_columns
    }
    if any(failures.values()):
        raise RuntimeError(f"Refusing to merge Step 3 results with QA failures: {failures}")
    if not (pd.to_numeric(merged["final_soc"]) - 600.0).abs().le(1e-5).all():
        raise RuntimeError("Not every Step 3 case ends at 600 MWh.")
    if merged["causal_ridge_forecast_sha256"].nunique() != 1:
        raise RuntimeError("Step 3 variants do not share one frozen causal-ridge forecast.")

    destination = args.out_dir / "uncertainty_aware_summary.csv"
    merged.to_csv(destination, index=False)
    metadata_path = args.out_dir / "experiment_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        metadata["annualized_costs_usd"] = {
            "wind_only": annualized_wind_only_cost(),
            "wind_plus_100mw_caes": base.annualized_dispatch_cost(),
        }
        metadata["merged_parallel_sources"] = {
            variant: str(args.parallel_root / directory)
            for variant, directory in VARIANT_DIRS.items()
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(merged[[
        "candidate",
        "horizon_hours",
        "dispatch_revenue",
        "dispatch_cove_index",
        "cove_reduction_vs_100mw_baseload_pct",
        "final_soc",
        "qa_total_violation_count",
    ]].to_string(index=False))
    print(f"Merged canonical Step 3 summary: {destination}")


if __name__ == "__main__":
    main()
