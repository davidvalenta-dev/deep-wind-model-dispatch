# Step 2 Rolling-Horizon Code

This folder contains the code for the deterministic rolling-horizon Gurobi step.

| File | Purpose |
| --- | --- |
| `forecast_backtest_rolling_horizons.py` | Full causal-forecast rolling-horizon backtest. This is the reserve-aware code path behind the 6.25% table. |
| `rolling_horizon_gurobi_dispatch.py` | Lower-level Gurobi/MILP dispatch model with storage constraints. |
| `compare_rolling_horizons.py` | Helper for comparing completed perfect-information horizon runs. |
| `nora_parameters_and_constraints.py` | Human-readable Nora/Chris parameter and constraint reference. |
| `dataset.py`, `model.py`, `storage.py`, `util.py` | Local helper modules needed by the copied Gurobi/storage code. |

The main quick reproduction command is:

```bash
../RUN_2_ROLLING_HORIZON.py
```

The full Gurobi rebuild command is:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --out-dir "results/full_rebuild_forecast_backtest_2014_2023"
```

The full rebuild is slower because it resolves all daily Gurobi windows.
