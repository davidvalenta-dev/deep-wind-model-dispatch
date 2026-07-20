# Rolling Horizon

This folder answers the second question:

> Once we have causal forecasts, how far should Gurobi look ahead?

Run:

```bash
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

The script compares 24, 48, 72, and 168-hour causal forecast horizons against baseload.

Main result:

```text
24 h:  3.31% COVE improvement
48 h:  6.25% COVE improvement
72 h:  6.06% COVE improvement
168 h: 5.44% COVE improvement
```

The best realistic case is the 48-hour planning horizon. In this setup, ridge predicts the next 48 hours, Gurobi optimizes those 48 hours, only the first 24 hours are executed, and then the process repeats.

Generated figures:

```text
figures/step2_causal_horizon_improvement.png
figures/step2_causal_horizon_cove.png
figures/step2_revenue_by_horizon.png
figures/step2_runtime_value_tradeoff.png
figures/step2_3d_horizon_revenue_cove.png
```

## Code In This Folder

| File | What it does |
| --- | --- |
| `RUN_2_ROLLING_HORIZON.py` | Main command for Step 2. Prints the horizon table and regenerates the paper-facing figures from the saved official result. |
| `code/forecast_backtest_rolling_horizons.py` | Full deterministic forecast/oracle Gurobi backtest runner. It can rebuild the saved 2014-2023 horizon table. |
| `code/rolling_horizon_gurobi_dispatch.py` | Core Gurobi/MILP dispatch engine with storage, grid, charging, discharging, direct-wind, curtailment, and SoC constraints. |
| `code/nora_parameters_and_constraints.py` | Human-readable constraint checklist for the Nora/Chris storage setup. |
| `code/run_nora_matching_forecast_horizons.py` | Shared helper used for forecast-driven rolling-horizon runs. |
| `code/compare_rolling_horizons.py` | Helper for the older full-dataset oracle horizon comparison. |
| `code/dataset.py`, `code/model.py`, `code/storage.py`, `code/util.py` | Shared support code copied here so this folder can be inspected without hunting through the whole repo. |

Full rebuild command:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --out-dir "results/full_rebuild_forecast_backtest_2014_2023"
```

The main `RUN_2_ROLLING_HORIZON.py` command is faster because it reads the frozen official summary table. The full rebuild command reruns Gurobi.
