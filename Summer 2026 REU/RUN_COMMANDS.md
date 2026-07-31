# Summer 2026 REU Run Commands

Primary comparison for dispatch results:

```text
100-MW Constant-Output Baseload Benchmark
```

Wind-only/no-storage is printed only as secondary reference information.

## Step 0 - 100 MW Constant-Output Baseload Benchmark

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```

What it runs:

- the rule-based 100 MW storage benchmark;
- 2020 same-year oracle checks;
- the 2014-2023 100 MW benchmark used for comparison tables.

Important files:

```text
100 MW baseload/EXPERIMENT_KNOBS.py
100 MW baseload/results/current_run_from_knobs/constant_output_baseload_100mw_2014_2023_hourly.csv
100 MW baseload/results/current_run_from_knobs/constant_output_baseload_100mw_2014_2023_summary.csv
```

## Step 1 - Forecast RMSE Comparison

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

Current best:

```text
causal_lag_prediction_mw RMSE = 21.24 MW
```

Important files:

```text
causal ridge regression/EXPERIMENT_KNOBS.py
causal ridge regression/results/current_run_from_knobs/forecast_model_rmse_comparison.csv
causal ridge regression/results/current_run_from_knobs/causal_lag_forecast_outputs/causal_lag_forecast_predictions.csv
```

## Step 2 - Deterministic Forecast-Driven Rolling-Horizon MILP

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

Current best:

```text
48 h horizon
COVE gain vs 100 MW benchmark = 20.63%
Revenue metric = 7,536,849.56
```

Important files:

```text
rolling horizon/EXPERIMENT_KNOBS.py
rolling horizon/results/current_run_from_knobs/forecast_dispatch_summary.csv
rolling horizon/results/current_run_from_knobs/forecast_dispatch_48h.csv
```

Custom horizon example:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py \
  --direct-reserve-mw 75 \
  --horizons 35 \
  --execution-step-hours 24 \
  --replanning-interval-hours 24 \
  --storage-power-mw 100 \
  --storage-duration-h 10 \
  --primary-baseline-storage-duration-h 10 \
  --grid-cap-mw 249 \
  --out-dir "results/test_35h"
```

## Step 3 - Scenario-Based Rolling-Horizon MILP

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

Current best:

```text
3 scenarios
COVE gain vs 100 MW benchmark = 40.18%
Revenue gain vs 100 MW benchmark = 67.16%
```

Important files:

```text
different scenarios/EXPERIMENT_KNOBS.py
different scenarios/results/current_run_from_knobs/scenario_summary_vs_wind_only_and_100mw.csv
different scenarios/results/current_run_from_knobs/three_scenario_expected_nowcast_gated_labels.csv
```

To run a full scenario recompute, set this in
`different scenarios/EXPERIMENT_KNOBS.py`:

```python
RERUN_FROM_SOURCE = True
MAX_ORIGINS = None
```

Then rerun `RUN_3_SCENARIO_COMPARISON.py`.

## Step 4 - Perfect-Information Oracle Rolling-Horizon MILP

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

This prints two oracle blocks:

```text
Daily-replan oracle: execute 24 hours, then replan.
Hourly-replan oracle ceiling: execute 1 hour, then replan.
```

Current best daily oracle:

```text
168 h horizon
COVE gain vs 100 MW benchmark = 40.87%
Revenue metric = 10,116,705.90
```

Current hourly ceiling:

```text
168 h horizon
COVE gain vs 100 MW benchmark = 40.85%
Revenue metric = 10,127,810.67
```

Important files:

```text
oracle upper bound/EXPERIMENT_KNOBS.py
oracle upper bound/results/current_run_from_knobs/oracle_upper_bound_summary.csv
oracle upper bound/results/current_run_from_knobs/oracle_dispatch_168h.csv
oracle upper bound/results/hourly_168h_oracle_ceiling/oracle_hourly_168h_ceiling_summary.csv
oracle upper bound/results/hourly_168h_oracle_ceiling/oracle_dispatch_168h.csv
```

## Audit

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU"
../venv/bin/python AUDIT_DATA_CONFIG.py
```

Current result:

```text
Audited hourly files: 16
Passed common 100 MW / 10 h checks: 16/16
```

Audit file:

```text
audit/summer_2026_reu_data_config_audit.csv
```
