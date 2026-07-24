# Step 2 Rolling-Horizon Code

This folder contains the code for the deterministic rolling-horizon Gurobi step.

| File | Purpose |
| --- | --- |
| `forecast_backtest_rolling_horizons.py` | Full causal-forecast rolling-horizon backtest. This is the reserve-aware code path behind the current 100 MW / 10-hour table and it writes one hourly CSV per tested horizon. |
| `rolling_horizon_gurobi_dispatch.py` | Lower-level Gurobi/MILP dispatch model with storage constraints. |
| `compare_rolling_horizons.py` | Helper for comparing completed perfect-information horizon runs. |
| `nora_parameters_and_constraints.py` | Human-readable Nora/Chris parameter and constraint reference. |
| `dataset.py`, `model.py`, `storage.py`, `util.py` | Local helper modules needed by the copied Gurobi/storage code. |

The main quick reproduction command is run from the parent folder:

```bash
cd ..
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

For normal reruns, change `../EXPERIMENT_KNOBS.py` first. That file is the
one place for horizons, storage power, storage duration, grid cap, initial SoC,
min/max SoC, direct reserve, solver gap, and output folder.

The full Gurobi rebuild command is:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 24 48 72 168 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/full_rebuild_forecast_backtest_2014_2023"
```

That command writes full hourly outputs such as:

```text
results/full_rebuild_forecast_backtest_2014_2023/forecast_dispatch_24h.csv
results/full_rebuild_forecast_backtest_2014_2023/forecast_dispatch_48h.csv
results/full_rebuild_forecast_backtest_2014_2023/forecast_dispatch_72h.csv
results/full_rebuild_forecast_backtest_2014_2023/forecast_dispatch_168h.csv
```

To test a different horizon without using the knobs file:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 248 --out-dir "results/test_248h"
```

To test a different storage setup:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 48 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/test_100mw_10h"
```

The full rebuild is slower because it resolves all daily Gurobi windows.
