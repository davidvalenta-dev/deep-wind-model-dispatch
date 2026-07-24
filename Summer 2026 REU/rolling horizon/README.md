# Rolling Horizon

This folder answers the second question:

> Once we have causal forecasts, how far should Gurobi look ahead?

Run:

```bash
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

Before running, change all experiment settings in:

```text
EXPERIMENT_KNOBS.py
```

That file controls horizons, storage power, storage duration, grid cap, initial
SoC, min/max SoC fractions, direct reserve, and the output folder. For example,
to test a 35-hour horizon, set `HORIZONS = [35]`.

The script reruns the causal forecast horizons listed in `EXPERIMENT_KNOBS.py`
against baseload. By default those horizons are 24, 48, 72, and 168 hours.

Main result:

```text
24 h:  -1.15% COVE improvement
48 h:   0.95% COVE improvement
72 h:   0.83% COVE improvement
168 h:  0.58% COVE improvement
```

The best realistic case is the 48-hour planning horizon. In this setup, ridge predicts the next 48 hours, Gurobi optimizes those 48 hours, only the first 24 hours are executed, and then the process repeats. The storage system is the common 100 MW / 10-hour CAES setup, so maximum SoC is 1000 MWh.

Generated figures:

```text
figures/step2_causal_horizon_improvement.png
figures/step2_causal_horizon_cove.png
figures/step2_revenue_by_horizon.png
figures/step2_runtime_value_tradeoff.png
figures/step2_3d_horizon_revenue_cove.png
```

Fresh rerun outputs go here:

```text
results/current_run_from_knobs/
```

Official hourly outputs from the frozen result are stored here:

```text
results/full_hourly_outputs/forecast_dispatch_24h.csv
results/full_hourly_outputs/forecast_dispatch_48h.csv
results/full_hourly_outputs/forecast_dispatch_72h.csv
results/full_hourly_outputs/forecast_dispatch_168h.csv
```

## Code In This Folder

| File | What it does |
| --- | --- |
| `RUN_2_ROLLING_HORIZON.py` | Main command for Step 2. Reruns the deterministic Gurobi backtest from `EXPERIMENT_KNOBS.py`, prints the horizon table, and regenerates figures. |
| `code/forecast_backtest_rolling_horizons.py` | Full deterministic forecast/oracle Gurobi backtest runner. It can rebuild the saved 2014-2023 horizon table. |
| `code/rolling_horizon_gurobi_dispatch.py` | Core Gurobi/MILP dispatch engine with storage, grid, charging, discharging, direct-wind, curtailment, and SoC constraints. |
| `code/nora_parameters_and_constraints.py` | Human-readable constraint checklist for the Nora/Chris storage setup. |
| `code/run_nora_matching_forecast_horizons.py` | Shared helper used for forecast-driven rolling-horizon runs. |
| `code/compare_rolling_horizons.py` | Helper for the older full-dataset oracle horizon comparison. |
| `code/dataset.py`, `code/model.py`, `code/storage.py`, `code/util.py` | Shared support code copied here so this folder can be inspected without hunting through the whole repo. |

You usually do not need a long terminal command anymore. Prefer changing
`EXPERIMENT_KNOBS.py`, then running `RUN_2_ROLLING_HORIZON.py`.

Full direct rebuild command, if you want to bypass the knobs file:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 24 48 72 168 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/full_rebuild_forecast_backtest_2014_2023"
```

The main `RUN_2_ROLLING_HORIZON.py` command reruns Gurobi using
`EXPERIMENT_KNOBS.py`. Outputs from that run are written to the configured
output folder, which defaults to `results/current_run_from_knobs/`.

Example custom reruns:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 248 --out-dir "results/test_248h"
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 48 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/test_100mw_10h"
```
