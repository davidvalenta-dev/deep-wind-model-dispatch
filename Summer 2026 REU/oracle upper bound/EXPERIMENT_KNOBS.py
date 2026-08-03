"""One place to change Step 4 oracle upper-bound settings.

Edit this file, then run:
    ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Where the daily-replan Gurobi oracle rerun writes summaries and hourly CSVs.
OUTPUT_DIR = HERE / "results" / "current_run_from_knobs"
HOURLY_CEILING_OUTPUT_DIR = HERE / "results" / "hourly_168h_oracle_ceiling"

# False means the RUN script prints the saved current 100 MW / 10-hour CAES oracle results
# already saved in OUTPUT_DIR. Set True only for an intentional rerun.
RERUN_FROM_SOURCE = True

# Data and model config.
DATA = REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"
CONFIG = REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"
TRAIN_END = "2014-01-01"
TEST_END = None

# Forecast matrix knobs. Oracle dispatch uses realized future values for planning,
# but the runner still builds forecast matrices for common reporting.
ALPHA = 10.0
TRAIN_ORIGIN_STRIDE = 24

# Storage setup Chris asked to keep common.
STORAGE_POWER_MW = 100.0
STORAGE_DURATION_H = 10.0
GRID_CAP_MW = 249.0
MIN_SOC_FRAC = 0.2
MAX_SOC_FRAC = 1.0
INITIAL_SOC_MWH = 600.0
ANNUAL_TARGET_SOC_MWH = None

# Daily-replan oracle horizons to test. Add 35 here if you want a 35-hour case.
HORIZONS = [24, 48, 72, 168]
EXECUTION_STEP_HOURS = 24
REPLANNING_INTERVAL_HOURS = 24
TERMINAL_POLICY = "equal-initial"
MIP_GAP = 0.0

# Optional extra perfect-information reference: 168-hour lookahead with hourly replanning.
# This is computationally heavy on the full 2014-2023 dataset, so the default
# current folder uses the daily-replan oracle that matches the ladder.
RUN_HOURLY_168H_CEILING = False
HOURLY_CEILING_HORIZON = 168
HOURLY_CEILING_EXECUTION_STEP_HOURS = 1
HOURLY_CEILING_REPLANNING_INTERVAL_HOURS = 1
HOURLY_CEILING_TERMINAL_POLICY = "equal-initial"

# Legacy non-strategic storage-baseload setting. The primary comparison is now
# the 100 MW constant-output benchmark; wind-only stays as secondary reference.
PRIMARY_BASELINE_STORAGE_DURATION_H = 10.0
