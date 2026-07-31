"""One place to change Step 3 scenario-dispatch settings.

Edit this file, then run:
    ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent

# Where the full scenario rerun writes summaries and hourly CSVs.
OUTPUT_DIR = HERE / "results" / "current_run_from_knobs"

# False means the RUN script prints the saved current 100 MW / 10-hour CAES results
# already saved in OUTPUT_DIR. Set True only if you intentionally want to rerun Gurobi.
RERUN_FROM_SOURCE = True

# Scenario/rolling-horizon knobs for the archived scenario paper result.
# This version uses hourly replanning: each 48-hour problem is solved, only
# the first hour is executed, then the controller replans with a fresh nowcast.
HORIZON_HOURS = 48
FORECAST_MODEL_MAX_HORIZON_HOURS = 48
EVALUATION_CUTOFF_HORIZON_HOURS = 48
EXECUTION_STEP_HOURS = 1
REPLANNING_INTERVAL_HOURS = 1
VARIANTS = [
    "single_recourse",
    "three_scenario_expected",
    "five_scenario_expected",
    "seven_scenario_expected",
    "ten_scenario_expected",
]

# Storage setup Chris asked to keep common.
STORAGE_POWER_MW = 100.0
STORAGE_DURATION_H = 10.0
RTE = 0.55
DOD = 0.8
GRID_CAP_MW = 249.0
INITIAL_SOC_MWH = None

# Forecast/scenario construction knobs.
NOWCAST_FIRST_HOUR = True
# Safety gate is on for the archived hourly-replan scenario result.
GATE_MARGIN = 0.0
APPLY_GATE_TO_SINGLE_FORECAST = False
FALLBACK_TARGET_MW = 85.67800432903339
DIRECT_RESERVE_MW = 75.0
TRAIN_ORIGIN_STRIDE = 24
RESIDUAL_ORIGIN_STRIDE = 1
CALIBRATION_MODE = "in_sample_residual"
FORECAST_TRAIN_END = "2013-01-01"
CALIBRATION_END = "2014-01-01"

# Leave None for the full 2014-2023 run.
# Set to 168 or 720 for a quick test before a long full rerun.
MAX_ORIGINS = None
