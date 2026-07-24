"""One place to change Step 4 oracle upper-bound settings.

Edit this file, then run:
    ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Where the full Gurobi oracle rerun writes summaries and hourly CSVs.
OUTPUT_DIR = HERE / "results" / "current_run_from_knobs"

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
INITIAL_SOC_MWH = None

# Oracle horizons to test. Add 35 here if you want a 35-hour perfect-future case.
HORIZONS = [24, 48, 72, 168]
MIP_GAP = 0.0
