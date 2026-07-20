# Summer 2026 REU Reproduction Ladder

Run one command in each folder. The first three folders are the realistic ladder, and the oracle folder is the perfect-future ceiling:

1. Forecast quality: choose the forecast model.
2. Rolling-horizon dispatch: use that forecast inside Gurobi.
3. Scenario dispatch: add multiple possible forecast futures.
4. Oracle upper bound: show the best possible perfect-future Gurobi result.

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

Extra figures generated:

```text
figures/step1_rmse_mae_tradeoff.png
figures/step1_example_forecast_week.png
figures/step1_causal_error_distribution.png
```

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

Extra figures generated:

```text
figures/step2_revenue_by_horizon.png
figures/step2_runtime_value_tradeoff.png
figures/step2_3d_horizon_revenue_cove.png
```

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

Extra figures generated:

```text
figures/step3_revenue_cove_tradeoff.png
figures/step3_ladder_revenue_progression.png
figures/step3_3d_scenario_revenue_cove.png
```

## Step 4: Oracle Upper Bound

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

This prints the perfect-future Gurobi horizon comparison. It is not realistic because Gurobi sees actual future wind and price.

Main result:

```text
Best oracle horizon = 168 h
COVE improvement vs baseload = 32.83%
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
causal ridge regression/figures/step1_rmse_mae_tradeoff.png
causal ridge regression/figures/step1_example_forecast_week.png
causal ridge regression/figures/step1_causal_error_distribution.png
rolling horizon/figures/step2_causal_horizon_improvement.png
rolling horizon/figures/step2_causal_horizon_cove.png
rolling horizon/figures/step2_revenue_by_horizon.png
rolling horizon/figures/step2_runtime_value_tradeoff.png
rolling horizon/figures/step2_3d_horizon_revenue_cove.png
different scenarios/figures/step3_scenario_cove_improvement.png
different scenarios/figures/step3_scenario_revenue_gain.png
different scenarios/figures/step3_revenue_cove_tradeoff.png
different scenarios/figures/step3_ladder_revenue_progression.png
different scenarios/figures/step3_3d_scenario_revenue_cove.png
oracle upper bound/figures/step4_oracle_improvement_by_horizon.png
oracle upper bound/figures/step4_oracle_cove_by_horizon.png
oracle upper bound/figures/step4_oracle_runtime_value_tradeoff.png
oracle upper bound/figures/step4_3d_oracle_revenue_cove.png
```
