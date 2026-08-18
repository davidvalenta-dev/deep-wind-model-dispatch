#!/usr/bin/env python3
"""Build and fingerprint the exact causal-ridge forecasts used by Steps 2-3."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTROLLER = (
    REPO_ROOT
    / "Summer 2026 REU"
    / "different scenarios"
    / "code"
    / "run_uncertainty_aware_dispatch.py"
)


def load_controller():
    spec = importlib.util.spec_from_file_location("canonical_scenario_controller", CONTROLLER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import canonical controller: {CONTROLLER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metric_rows(actual: np.ndarray, predicted: np.ndarray, variable: str) -> list[dict]:
    groups = [(0, 24), (24, 48), (48, 72), (72, predicted.shape[1])]
    rows = []
    for start, end in groups:
        observed = actual[:, start:end].reshape(-1)
        estimate = predicted[:, start:end].reshape(-1)
        error = estimate - observed
        rows.append(
            {
                "variable": variable,
                "lead_hours": f"{start + 1}-{end}",
                "rmse": float(np.sqrt(np.mean(error**2))),
                "mae": float(np.mean(np.abs(error))),
                "bias": float(np.mean(error)),
                "correlation": float(np.corrcoef(estimate, observed)[0, 1]),
                "samples": int(len(error)),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-horizon-hours", type=int, default=168)
    parser.add_argument("--train-origin-stride", type=int, default=24)
    args = parser.parse_args()

    controller = load_controller()
    controller.HORIZON = int(args.max_horizon_hours)
    df = pd.read_csv(controller.base.DATA_PATH, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df[["datetime", "power_generated", "lmp", "user_load_zonal"]].dropna().reset_index(drop=True)
    train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64("2014-01-01")))
    raw_lmp = df["lmp"].to_numpy(float)
    config = controller.util.load_config(controller.CONFIG_PATH)
    capped_price = np.minimum(raw_lmp, float(config["price_threshold"]))
    df["lmp"] = capped_price / float(capped_price[:train_end].mean())
    origins = np.arange(train_end, len(df), 1)
    origins = origins[origins + int(args.max_horizon_hours) <= len(df)]

    wind, price, wind_models, price_models = controller.build_forecasts(
        df,
        train_end,
        origins,
        int(args.train_origin_stride),
        int(args.max_horizon_hours),
    )
    actual_wind = np.vstack(
        [df["power_generated"].to_numpy(float)[origin : origin + args.max_horizon_hours] for origin in origins]
    )
    actual_price = np.vstack(
        [df["lmp"].to_numpy(float)[origin : origin + args.max_horizon_hours] for origin in origins]
    )
    fingerprint = controller.forecast_fingerprint(wind, price, wind_models, price_models)
    rows = metric_rows(actual_wind, wind, "generation_mw")
    rows += metric_rows(actual_price, price, "price_normalized")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out_dir / "canonical_dispatch_forecast_accuracy_by_lead.csv", index=False)
    metadata = {
        "forecast_name": "frozen_causal_direct_lead_ridge",
        "forecast_sha256": fingerprint,
        "training_start": str(df["datetime"].iloc[0]),
        "training_end": str(df["datetime"].iloc[train_end - 1]),
        "evaluation_start": str(df["datetime"].iloc[origins[0]]),
        "evaluation_end": str(df["datetime"].iloc[origins[-1] + args.max_horizon_hours - 1]),
        "max_horizon_hours": int(args.max_horizon_hours),
        "train_origin_stride": int(args.train_origin_stride),
        "controller_source": str(CONTROLLER),
    }
    (args.out_dir / "canonical_dispatch_forecast_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"Frozen causal-ridge forecast SHA256: {fingerprint}")


if __name__ == "__main__":
    main()
