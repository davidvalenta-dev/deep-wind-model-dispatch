#!/usr/bin/env python3
"""Recompute the Step 1 forecast RMSE comparison table.

This is the script behind the forecast-method comparison. It rebuilds the
causal lag/ridge prediction, then compares it with the saved prediction outputs
from the earlier power-model work.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAUSAL_OUTPUT = HERE / "results" / "causal_lag_forecast_outputs"
DEFAULT_PYRON_RESULTS = REPO_ROOT / "power_model" / "evaluation" / "pyron_model_results.csv"
DEFAULT_OUTPUT = HERE / "results" / "forecast_model_rmse_comparison.csv"


def error_row(
    source: str,
    model: str,
    datetimes: pd.Series,
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, float | int | str]:
    errors = predicted - actual
    return {
        "source": source,
        "model": model,
        "start": str(datetimes.iloc[0]),
        "end": str(datetimes.iloc[-1]),
        "samples": int(len(errors)),
        "rmse_mw": float(np.sqrt(np.mean(errors**2))),
        "mae_mw": float(np.mean(np.abs(errors))),
        "bias_mw": float(np.mean(errors)),
    }


def build_causal_predictions(output_dir: Path) -> Path:
    script = Path(__file__).resolve().parent / "causal_lag_forecast.py"
    subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output_dir)],
        check=True,
    )
    return output_dir / "causal_lag_forecast_predictions.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Part 1 power forecast RMSE values.")
    parser.add_argument("--causal-output-dir", default=str(DEFAULT_CAUSAL_OUTPUT))
    parser.add_argument("--pyron-results", default=str(DEFAULT_PYRON_RESULTS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Use existing causal lag/ridge predictions instead of rebuilding them first.",
    )
    args = parser.parse_args()

    causal_output = Path(args.causal_output_dir)
    causal_predictions = causal_output / "causal_lag_forecast_predictions.csv"
    if not args.skip_rebuild or not causal_predictions.exists():
        causal_predictions = build_causal_predictions(causal_output)

    rows: list[dict[str, float | int | str]] = []

    causal = pd.read_csv(causal_predictions, parse_dates=["datetime"])
    causal_actual = causal["actual_power_mw"].to_numpy(dtype=float)
    for column in [
        "causal_lag_prediction_mw",
        "lag1_persistence_prediction_mw",
        "speed_power_curve_prediction_mw",
    ]:
        rows.append(
            error_row(
                source=str(causal_predictions.relative_to(HERE)),
                model=column,
                datetimes=causal["datetime"],
                actual=causal_actual,
                predicted=causal[column].to_numpy(dtype=float),
            )
        )

    pyron_path = Path(args.pyron_results)
    pyron = pd.read_csv(pyron_path, parse_dates=["datetime"])
    pyron_actual = pyron["historical_power"].to_numpy(dtype=float)
    for column in ["rnn_preds", "physics_preds", "prob_preds"]:
        rows.append(
            error_row(
                source=str(pyron_path.relative_to(REPO_ROOT)),
                model=column,
                datetimes=pyron["datetime"],
                actual=pyron_actual,
                predicted=pyron[column].to_numpy(dtype=float),
            )
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    comparison = pd.DataFrame(rows).sort_values("rmse_mw")
    comparison.to_csv(output, index=False)
    print(comparison.to_string(index=False))
    print(f"Saved comparison to {output}")


if __name__ == "__main__":
    main()
