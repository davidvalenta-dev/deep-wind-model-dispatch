"""One place to change Step 2 rolling-horizon dispatch settings.

Edit this file, then run:
    ../../venv/bin/python RUN_2_ROLLING_HORIZON.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Where the full Gurobi rerun writes summaries and hourly CSVs.
OUTPUT_DIR = HERE / "results" / "current_run_from_knobs"

# False means the RUN script prints the saved current 100 MW / 10-hour CAES results
# already saved in OUTPUT_DIR. Set True only if you intentionally want to rerun Gurobi.
RERUN_FROM_SOURCE = True

# Data and model config.
DATA = REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"
CONFIG = REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"
TRAIN_END = "2014-01-01"
TEST_END = None

# Forecast model knobs.
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

# Dispatch knobs. Add 35 here if you want to test a 35-hour horizon.
HORIZONS = [24, 48, 72, 168]
EXECUTION_STEP_HOURS = 24
REPLANNING_INTERVAL_HOURS = 24
TERMINAL_POLICY = "equal-initial"
DIRECT_RESERVE_MW = 75.0
MIP_GAP = 0.0

# Legacy non-strategic storage-baseload setting. The primary comparison is now
# the 100 MW constant-output benchmark; wind-only stays as secondary reference.
PRIMARY_BASELINE_STORAGE_DURATION_H = 10.0

# Keep True if you also want oracle rows printed as context in the same rerun.
RUN_ORACLE_CONTEXT = False
