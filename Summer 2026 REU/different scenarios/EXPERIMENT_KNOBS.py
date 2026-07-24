"""One place to change Step 3 scenario-dispatch settings.

Edit this file, then run:
    ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent

# Where the full scenario rerun writes summaries and hourly CSVs.
OUTPUT_DIR = HERE / "results" / "current_run_from_knobs"

# Scenario/rolling-horizon knobs. Change HORIZON_HOURS to test 35, 72, etc.
HORIZON_HOURS = 48
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
GATE_MARGIN = 0.0
CALIBRATION_MODE = "in_sample_residual"
FORECAST_TRAIN_END = "2013-01-01"
CALIBRATION_END = "2014-01-01"

# Leave None for the full 2014-2023 run.
# Set to 168 or 720 for a quick test before a long full rerun.
MAX_ORIGINS = None
