# Summer 2026 REU

This folder is organized as a three-step research ladder. Each step has one command to run and produces its own printed table and figures.

## Folder Map

| Folder | Purpose | Command |
| --- | --- | --- |
| `causal ridge regression` | Compare forecast models using RMSE | `../../venv/bin/python RUN_1_FORECAST_RMSE.py` |
| `rolling horizon` | Compare Gurobi horizons using the causal ridge forecast | `../../venv/bin/python RUN_2_ROLLING_HORIZON.py` |
| `different scenarios` | Compare single forecast vs 3/5/7/10 scenarios | `../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py` |

## Main Story

Baseload is the reference case. First, the causal ridge forecast is checked against other prediction methods. Then that forecast is used inside Gurobi with rolling-horizon dispatch. Finally, scenario dispatch adds several possible forecast futures so the controller is less dependent on one predicted path.

## Best Results

| Step | Best result |
| --- | ---: |
| Forecast model | Causal lag / ridge-style forecast, 21.24 MW RMSE |
| Rolling horizon | 48-hour horizon, 6.25% COVE improvement vs baseload |
| Scenario dispatch | 3 scenarios, 23.19% COVE improvement vs baseload |
| Oracle upper bound | 168-hour perfect-information case, 32.83% COVE improvement vs baseload |

See `RUN_COMMANDS.md` for exact commands and figure names.
