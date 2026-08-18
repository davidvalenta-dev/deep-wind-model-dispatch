# Step 4 Source Code

`forecast_backtest_rolling_horizons.py` runs the rolling-window Oracle using
realized future wind and price inside each horizon. It executes one hour and
replans hourly. `rolling_horizon_gurobi_dispatch.py` defines the physical
Gurobi MILP. The remaining modules are required data/model/storage helpers.

Use `../RUN_4_ORACLE_UPPER_BOUND.py` as the front door and change only
`../EXPERIMENT_KNOBS.py`. Frozen outputs are in `../results/frozen_controlled/`.
