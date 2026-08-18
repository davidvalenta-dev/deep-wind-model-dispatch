"""One place to change Step 0 baseload/oracle benchmark settings.

Edit this file, then run:
    ../../venv/bin/python RUN_0_100MW_BASELOAD.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Where the rerun writes outputs. Change this if you want to keep multiple tests.
OUTPUT_DIR = HERE / "results" / "frozen_controlled"
RERUN_FROM_SOURCE = False

# Full paper-period 100 MW baseload reference.
# This is separate from the 2020 B6/canonical check above.
FULL_PERIOD_DATA = REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"
FULL_PERIOD_START = "2014-01-01 00:00:00"
# Match the active Summer 2026 ladder window. The last week of 2023 is
# excluded because the 168-hour planning horizon needs a complete future window.
FULL_PERIOD_END = "2023-12-23 05:00:00"
NORMALIZED_PRICE_TRAIN_END = "2014-01-01"
PRICE_THRESHOLD = 1000.0

# Storage setup Chris asked to keep common.
STORAGE_POWER_MW = 100.0
STORAGE_DURATION_H = 10.0
RTE = 0.55
GRID_CAP_MW = 249.0
TARGET_OUTPUT_MW = 100.0

# Battery SoC knobs from Chris's requested 100 MW / 10 h CAES setup.
MIN_SOC_MWH = 200.0
MAX_SOC_MWH = 1000.0
INITIAL_SOC_MWH = 600.0
YEAR_END_SOC_MWH = 600.0
ANNUAL_SOC_SETTLEMENT_HOURS = 720
