"""One place to change Step 0 baseload/oracle benchmark settings.

Edit this file, then run:
    ../../venv/bin/python RUN_0_100MW_BASELOAD.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Where the rerun writes outputs. Change this if you want to keep multiple tests.
OUTPUT_DIR = HERE / "results" / "current_run_from_knobs"

# Full paper-period 100 MW baseload reference.
# This is separate from the 2020 B6/canonical check above.
FULL_PERIOD_DATA = REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"
FULL_PERIOD_START = "2014-01-01 00:00:00"
FULL_PERIOD_END = None
NORMALIZED_PRICE_TRAIN_END = "2014-01-01"
PRICE_THRESHOLD = 1000.0

# Storage setup Chris asked to keep common.
STORAGE_POWER_MW = 100.0
STORAGE_DURATION_H = 10.0
RTE = 0.55
GRID_CAP_MW = 249.0
TARGET_OUTPUT_MW = 100.0

# Battery SoC knobs. Leave as None to use the standard 20%-100% range and midpoint start.
MIN_SOC_MWH = None
MAX_SOC_MWH = None
INITIAL_SOC_MWH = None
YEAR_END_SOC_MWH = None

# Oracle horizons to test. Add 35 here if you want a 35-hour oracle benchmark.
HORIZONS = [24, 48, 168]

# Solver knobs.
MIP_GAP = 1e-6
TIME_LIMIT_SECONDS = None
