# Summer 2026 REU Reproduction Ladder

Run one command in each folder. Step 0 is the Chris-requested 100 MW
constant-output baseload. The next three folders are the realistic paper
ladder, and the oracle folder is the perfect-future ceiling.

0. 100 MW baseload: rule-based storage benchmark.
1. Forecast quality: choose the forecast model.
2. Rolling-horizon dispatch: use that forecast inside Gurobi.
3. Scenario dispatch: add multiple possible forecast futures.
4. Oracle upper bound: show the best possible perfect-future Gurobi result.

## One Place To Change Settings

Every folder has a file named:

```text
EXPERIMENT_KNOBS.py
```

Change that file before running the folder command. That is where you change
things like storage power, storage duration, initial SoC, min/max SoC, horizon
length, scenario count, direct reserve, and output folder.

The `RUN_*.py` scripts now actually rerun the calculations from those knobs.
They do not only read old CSVs. New summaries, hourly CSVs, and figures are
written to the folder configured by `OUTPUT_DIR`, which defaults to:

```text
results/current_run_from_knobs/
```

Example: to test a 35-hour rolling horizon, open
`rolling horizon/EXPERIMENT_KNOBS.py`, set `HORIZONS = [35]`, then run
`RUN_2_ROLLING_HORIZON.py`.

## Step 0: 100 MW Constant-Output Baseload

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```

This prints the required 2020 rule-based 100 MW baseload benchmark, compares
the canonical 2020 oracle horizons against it, and also compares the B6 A/B/C
causal/oracle runs against it by raw realized revenue.

Main result:

```text
100-MW baseload revenue = $9,091,719.37
100-MW baseload COVE    = 5.655336
QA violations           = 0
Best canonical oracle   = +47.37% revenue vs 100-MW baseload
B6 C causal             = -7.62% revenue vs 100-MW baseload
B6 C oracle             = +47.36% revenue vs 100-MW baseload
```

Fresh rerun outputs go here:

```text
100 MW baseload/results/current_run_from_knobs/
```

Official frozen hourly CSV outputs:

```text
100 MW baseload/results/full_hourly_outputs/
```

Important: this is Chris's 100 MW constant-output baseload. The older rolling
and scenario paper folders may use a different evaluation period or reporting
scale, so their raw COVE values should not be mixed with this benchmark unless
the same canonical setup is rerun.

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

Fresh rerun outputs go here:

```text
causal ridge regression/results/current_run_from_knobs/
```

Official hourly forecast output:

```text
causal ridge regression/results/causal_lag_forecast_outputs/causal_lag_forecast_predictions.csv
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
COVE improvement vs baseload = 0.95%
```

This means ridge predicts a 48-hour window, Gurobi optimizes that window, the first 24 hours are executed, the battery state is updated, and the process repeats.

Extra figures generated:

```text
figures/step2_revenue_by_horizon.png
figures/step2_runtime_value_tradeoff.png
figures/step2_3d_horizon_revenue_cove.png
```

Fresh rerun outputs go here:

```text
rolling horizon/results/current_run_from_knobs/
```

Official hourly dispatch CSV outputs:

```text
rolling horizon/results/full_hourly_outputs/forecast_dispatch_24h.csv
rolling horizon/results/full_hourly_outputs/forecast_dispatch_48h.csv
rolling horizon/results/full_hourly_outputs/forecast_dispatch_72h.csv
rolling horizon/results/full_hourly_outputs/forecast_dispatch_168h.csv
```

Custom horizon example:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 248 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/test_248h"
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

Fresh rerun outputs go here:

```text
different scenarios/results/current_run_from_knobs/
```

Official hourly scenario CSV outputs:

```text
different scenarios/results/scenario_48h_full_ladder/*_labels.csv
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
COVE improvement vs baseload = 26.21%
```

Fresh rerun outputs go here:

```text
oracle upper bound/results/current_run_from_knobs/
```

Official hourly oracle CSV outputs:

```text
oracle upper bound/results/full_hourly_outputs/oracle_dispatch_24h.csv
oracle upper bound/results/full_hourly_outputs/oracle_dispatch_48h.csv
oracle upper bound/results/full_hourly_outputs/oracle_dispatch_72h.csv
oracle upper bound/results/full_hourly_outputs/oracle_dispatch_168h.csv
```

Custom oracle horizon example:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --oracle-only --horizons 248 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/oracle_248h"
```

## Clean Ladder Summary

| Step | Result |
| --- | ---: |
| 100 MW constant-output baseload | $9.09M revenue; COVE 5.655; 0 QA violations |
| Causal ridge forecast | 21.24 MW RMSE; no COVE yet |
| Causal ridge + 48h rolling-horizon Gurobi | 0.95% COVE improvement |
| 3-scenario 48h hourly-replan dispatch | 23.19% COVE improvement |
| Oracle upper bound | 26.21% COVE improvement |

## Figures Generated

Each command regenerates figures in its own folder:

```text
100 MW baseload/figures/step0_100mw_baseload_example_week.png
100 MW baseload/figures/step0_oracle_vs_100mw_baseload.png
100 MW baseload/figures/step0_b6_revenue_vs_100mw_baseload.png
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
