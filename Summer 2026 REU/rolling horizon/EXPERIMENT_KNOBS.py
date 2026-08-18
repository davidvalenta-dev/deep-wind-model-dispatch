"""One place to change the controlled Step 2 horizon experiment.

Step 2 and the Step 3 one-forecast case intentionally use the same canonical
controller.  The only Step 2 treatment variable is planning horizon.

Edit this file, then run:
    ../../venv/bin/python RUN_2_ROLLING_HORIZON.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent

# Each horizon receives its own summary and full hourly CSV under this folder.
OUTPUT_DIR = HERE / "results" / "controlled_hourly_nowcast_from_knobs"

# Set True to run Gurobi. False reads a previously completed controlled run.
RERUN_FROM_SOURCE = False
# Resume helper: horizons listed here are read from their already completed
# source rerun while the remaining horizons are rebuilt.
REUSE_COMPLETED_HORIZONS = []

# Treatment variable: how far Gurobi plans ahead. The 48 h row is configured
# to be exactly the Step 3 one-forecast controller.
HORIZONS = [24, 48, 72, 168]

# Common forecast/test support. Keeping this at the longest tested horizon
# gives every row the same evaluation timestamps. Step 3 uses these values too.
FORECAST_MODEL_MAX_HORIZON_HOURS = 168
EVALUATION_CUTOFF_HORIZON_HOURS = 168

# Controlled execution protocol shared with Step 3.
EXECUTION_STEP_HOURS = 1
REPLANNING_INTERVAL_HOURS = 1
NOWCAST_FIRST_HOUR = True
DIRECT_RESERVE_MW = 75.0
GATE_MARGIN = 0.0
APPLY_GATE_TO_SINGLE_FORECAST = True
FALLBACK_TARGET_MW = 85.67800432903339

# Common 100 MW / 10 h CAES configuration.
STORAGE_POWER_MW = 100.0
STORAGE_DURATION_H = 10.0
RTE = 0.55
DOD = 0.8
GRID_CAP_MW = 249.0
INITIAL_SOC_MWH = None  # None gives the 600 MWh midpoint of 200-1,000 MWh.
# Chronological SoC carries between hours; there is never a reset. The physical
# annual corridor returns SoC to 600 MWh after each completed evaluation year.
ANNUAL_TARGET_SOC_MWH = 600.0
FINAL_TARGET_SOC_MWH = 600.0
ANNUAL_SOC_SETTLEMENT_HOURS = 720

# Same causal ridge training and residual settings as Step 3.
TRAIN_ORIGIN_STRIDE = 24
RESIDUAL_ORIGIN_STRIDE = 1
CALIBRATION_MODE = "in_sample_residual"
FORECAST_TRAIN_END = "2013-01-01"
CALIBRATION_END = "2014-01-01"

# Leave None for the complete test period. Use a small value only for a quick
# wiring test; Step 2 and Step 3 must use the same value for direct comparison.
MAX_ORIGINS = None
