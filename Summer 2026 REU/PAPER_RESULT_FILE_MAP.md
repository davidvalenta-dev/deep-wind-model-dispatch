# Paper Result File Map

This file maps each current paper-facing number to the folder that generates it.

Primary dispatch benchmark:

```text
100-MW Constant-Output Baseload Benchmark
```

Secondary reference:

```text
Wind-only / no storage
```

## Current Ladder

| Step | Question | Command | Main result |
| ---: | --- | --- | --- |
| 0 | What is the primary benchmark? | `100 MW baseload/RUN_0_100MW_BASELOAD.py` | 100 MW benchmark built with zero QA violations |
| 1 | Which power forecast is best? | `causal ridge regression/RUN_1_FORECAST_RMSE.py` | causal lag/ridge forecast, 21.24 MW RMSE |
| 2 | Which deterministic horizon is best? | `rolling horizon/RUN_2_ROLLING_HORIZON.py` | 48 h, 20.63% COVE gain vs 100 MW benchmark |
| 3 | Do scenarios improve dispatch? | `different scenarios/RUN_3_SCENARIO_COMPARISON.py` | 3 scenarios, 40.18% COVE gain vs 100 MW benchmark |
| 4 | What is the perfect-information ceiling? | `oracle upper bound/RUN_4_ORACLE_UPPER_BOUND.py` | 168 h daily oracle, 40.87% COVE gain vs 100 MW benchmark |

## Result Files

| Result | File |
| --- | --- |
| 100 MW benchmark summary | `100 MW baseload/results/current_run_from_knobs/constant_output_baseload_100mw_2014_2023_summary.csv` |
| 100 MW benchmark hourly CSV | `100 MW baseload/results/current_run_from_knobs/constant_output_baseload_100mw_2014_2023_hourly.csv` |
| Forecast comparison | `causal ridge regression/results/current_run_from_knobs/forecast_model_rmse_comparison.csv` |
| Causal forecast predictions | `causal ridge regression/results/current_run_from_knobs/causal_lag_forecast_outputs/causal_lag_forecast_predictions.csv` |
| Deterministic horizon summary | `rolling horizon/results/current_run_from_knobs/forecast_dispatch_summary.csv` |
| Deterministic hourly CSVs | `rolling horizon/results/current_run_from_knobs/forecast_dispatch_*.csv` |
| Scenario enriched summary | `different scenarios/results/current_run_from_knobs/scenario_summary_vs_wind_only_and_100mw.csv` |
| Scenario hourly CSVs | `different scenarios/results/current_run_from_knobs/*_labels.csv` |
| Daily oracle summary | `oracle upper bound/results/current_run_from_knobs/oracle_upper_bound_summary.csv` |
| Daily oracle hourly CSVs | `oracle upper bound/results/current_run_from_knobs/oracle_dispatch_*.csv` |
| Hourly oracle ceiling summary | `oracle upper bound/results/hourly_168h_oracle_ceiling/oracle_hourly_168h_ceiling_summary.csv` |
| Hourly oracle ceiling CSV | `oracle upper bound/results/hourly_168h_oracle_ceiling/oracle_dispatch_168h.csv` |
| Data/config audit | `audit/summer_2026_reu_data_config_audit.csv` |

## Current Numbers

| Case | Main metric |
| --- | ---: |
| 100 MW benchmark, Step 2/4 period | revenue metric 5,981,942.95; COVE 8.595322 |
| Causal lag/ridge forecast | 21.24 MW RMSE |
| Best deterministic case | 48 h, 20.63% COVE gain vs 100 MW benchmark |
| Best scenario case | 3 scenarios, 40.18% COVE gain vs 100 MW benchmark |
| Best daily oracle | 168 h, 40.87% COVE gain vs 100 MW benchmark |
| Hourly oracle ceiling | 168 h, 40.85% COVE gain vs 100 MW benchmark |

## QA Status

`AUDIT_DATA_CONFIG.py` checked the active hourly CSVs for SoC bounds, charge and
discharge limits, grid cap, and delivered-power consistency.

```text
Audited hourly files: 16
Passed common 100 MW / 10 h checks: 16/16
```
