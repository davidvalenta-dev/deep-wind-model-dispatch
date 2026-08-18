# Step 3 Source Code

`run_uncertainty_aware_dispatch.py` is the canonical controller shared by
Steps 2 and 3. It builds the causal-ridge center forecast, constructs fixed
residual-quantile futures, solves the Gurobi MILP, executes one realized hour,
updates chronological SoC, and replans. `run_nora_matching_forecast_horizons.py`
contains shared data, forecast, storage, and metric helpers.

Use `../RUN_3_SCENARIO_COMPARISON.py` as the front door and change only
`../EXPERIMENT_KNOBS.py`. Frozen outputs are in `../results/frozen_controlled/`.
