# Summer 2026 REU

This folder is the clean paper-facing version of the project. It groups the final research files into three pieces:

1. `causal ridge regression`
2. `rolling horizon`
3. `different scenarios`

Raw input data files are intentionally not copied here. This folder contains the scripts, summaries, figures, metadata, and verification outputs used to explain the paper numbers.

## Main Paper Story

The paper is about forecast-aware wind-storage dispatch. The workflow is:

1. Predict future wind generation and electricity price.
2. Give those predictions to Gurobi.
3. Let Gurobi choose direct-to-grid, charging, discharging, and storage state.
4. Execute the plan chronologically with rolling horizon logic.
5. Compare the result against baseload and oracle/perfect-information upper bounds.

## Folder Guide

| Folder | Purpose |
| --- | --- |
| `causal ridge regression` | Forecast-based dispatch backtest using causal ridge/lag forecasts |
| `rolling horizon` | Gurobi/MILP rolling-horizon solver, horizon tests, and B6 verification |
| `different scenarios` | Scenario-based uncertainty-aware dispatch result |

## Important Warning

Do not mix the numbers across folders unless the paper clearly says which experiment they came from. The scenario result, causal ridge forecast result, rolling-horizon full-dataset result, and B6 verification result are related, but they are not the same exact run.

