"""One place to change Step 1 forecast/RMSE settings.

Edit this file, then run:
    ../../venv/bin/python RUN_1_FORECAST_RMSE.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Input data for the causal lag/ridge forecast.
DATASET = REPO_ROOT / "data" / "processed" / "dataset_14-23.csv"

# Ridge regularization. Larger values smooth the model more.
CAUSAL_ALPHA = 1e-6

# Earlier neural-network/physics/probabilistic forecast file used for comparison.
PYRON_RESULTS = REPO_ROOT / "power_model" / "evaluation" / "pyron_model_results.csv"

# Where this rerun writes outputs.
OUTPUT_DIR = HERE / "results" / "frozen_controlled"
CAUSAL_OUTPUT_DIR = OUTPUT_DIR / "causal_lag_forecast_outputs"
RMSE_OUTPUT = OUTPUT_DIR / "forecast_model_rmse_comparison.csv"

# True rebuilds the forecasts from source. False reads the saved CSVs and
# regenerates the terminal table/figures without retraining.
RERUN_FROM_SOURCE = False

# Set True only if you want to reuse the existing causal prediction CSV.
SKIP_REBUILD = False

# Exact multi-lead causal ridge used unchanged by every forecast-driven
# dispatch experiment in Steps 2 and 3.
DISPATCH_FORECAST_MAX_HORIZON_HOURS = 168
DISPATCH_FORECAST_TRAIN_ORIGIN_STRIDE = 24
DISPATCH_FORECAST_OUTPUT_DIR = OUTPUT_DIR / "canonical_dispatch_forecast"
