# Summer 2026 REU Reproduction Ladder

Run one command in each folder. The three folders are meant to be read like a ladder:

1. Forecast quality: choose the forecast model.
2. Rolling-horizon dispatch: use that forecast inside Gurobi.
3. Scenario dispatch: add multiple possible forecast futures.

## Step 1: Causal Ridge Regression

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

This prints the RMSE comparison between forecasting methods.

Main result:

```text
Causal lag / ridge-style forecast RMSE = 21.24 MW
Lag-1 persistence RMSE = 23.60 MW
RNN RMSE = 46.21 MW
```

This step does not report COVE because it only predicts power. COVE starts after dispatch.

## Step 2: Rolling-Horizon Gurobi

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

This prints the causal ridge + Gurobi horizon comparison against baseload.

Main result:

```text
Best realistic horizon = 48 h
COVE improvement vs baseload = 6.25%
```

This means ridge predicts a 48-hour window, Gurobi optimizes that window, the first 24 hours are executed, the battery state is updated, and the process repeats.

## Step 3: Different Scenarios

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

This prints the single-forecast and multi-scenario comparison against baseload.
It uses the same 48-hour forecast lookahead selected in Step 2, but replans every hour so the scenario controller can share only the first action across possible futures.

Main result:

```text
Best scenario count = 3 scenarios
Revenue gain vs baseload = 30.19%
COVE reduction vs baseload = 23.19%
```

## Clean Ladder Summary

| Step | Result |
| --- | ---: |
| Baseload | 0.00% COVE improvement |
| Causal ridge forecast | 21.24 MW RMSE; no COVE yet |
| Causal ridge + 48h rolling-horizon Gurobi | 6.25% COVE improvement |
| 3-scenario 48h hourly-replan dispatch | 23.19% COVE improvement |
| Oracle upper bound | 32.83% COVE improvement |

## Figures Generated

Each command regenerates figures in its own folder:

```text
causal ridge regression/figures/step1_forecast_rmse_comparison.png
rolling horizon/figures/step2_causal_horizon_improvement.png
rolling horizon/figures/step2_causal_horizon_cove.png
different scenarios/figures/step3_scenario_cove_improvement.png
different scenarios/figures/step3_scenario_revenue_gain.png
```
