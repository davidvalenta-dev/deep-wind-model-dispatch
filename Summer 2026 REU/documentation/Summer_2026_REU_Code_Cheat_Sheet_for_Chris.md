# Summer 2026 REU Code Cheat Sheet for Chris
Repo: `/Users/davidvalenta/deep-wind-model-dispatch`

Frozen pushed commit: `e184740da217ed811496c056aace5b7a61f6f860`

## Commands
```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```
```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```
```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```
```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```
```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

## Main line anchors
- **100 MW baseload rule:** `Summer 2026 REU/100 MW baseload/code/build_100mw_baseload_reference.py:98-119`
- **Causal ridge features:** `Summer 2026 REU/causal ridge regression/code/causal_lag_forecast.py:57-103`
- **Ridge solve:** `Summer 2026 REU/causal ridge regression/code/causal_lag_forecast.py:106-109`
- **Rolling horizon loop:** `Summer 2026 REU/rolling horizon/code/forecast_backtest_rolling_horizons.py:382-443`
- **Rolling Gurobi MILP:** `Summer 2026 REU/rolling horizon/code/rolling_horizon_gurobi_dispatch.py:101-163`
- **Scenario MILP:** `Summer 2026 REU/different scenarios/code/run_uncertainty_aware_dispatch.py:156-209`
- **Scenario non-anticipativity:** `Summer 2026 REU/different scenarios/code/run_uncertainty_aware_dispatch.py:189-195`
- **Oracle actual-future branch:** `Summer 2026 REU/oracle upper bound/code/forecast_backtest_rolling_horizons.py:410-412`
- **B6 QA:** `Summer 2026 REU/b6 verification/code/B6_CANONICAL_RUNNER.py:421-459`
