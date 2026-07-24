# Paper Result File Map

This file gives the current official paper-facing ladder. Use this map when writing the paper or showing a reviewer where each number comes from.

## Official Ladder

| Step | Question | Command | Main result |
| --- | --- | --- | ---: |
| 1 | Which power forecast is best? | `Summer 2026 REU/causal ridge regression/RUN_1_FORECAST_RMSE.py` | causal lag / ridge-style forecast, 21.24 MW RMSE |
| 2 | Which deterministic rolling horizon is best? | `Summer 2026 REU/rolling horizon/RUN_2_ROLLING_HORIZON.py` | 48 h horizon, 0.95% COVE improvement vs baseload |
| 3 | Do forecast scenarios improve dispatch? | `Summer 2026 REU/different scenarios/RUN_3_SCENARIO_COMPARISON.py` | 3 scenarios, 23.19% COVE reduction vs baseload |
| 4 | What is the perfect-information upper bound? | `Summer 2026 REU/oracle upper bound/RUN_4_ORACLE_UPPER_BOUND.py` | 168 h oracle, 26.21% COVE improvement vs baseload |

## Current Result Files

| Result | File |
| --- | --- |
| Forecast model comparison | `Summer 2026 REU/causal ridge regression/results/forecast_model_rmse_comparison.csv` |
| Causal lag/ridge generated predictions | `Summer 2026 REU/causal ridge regression/results/causal_lag_forecast_outputs/causal_lag_forecast_predictions.csv` |
| Deterministic rolling horizon summary | `Summer 2026 REU/rolling horizon/results/causal_ridge_rolling_horizon_summary.csv` |
| Deterministic rolling horizon hourly CSVs | `Summer 2026 REU/rolling horizon/results/full_hourly_outputs/forecast_dispatch_*.csv` |
| Scenario summary | `Summer 2026 REU/different scenarios/results/scenario_48h_full_ladder/uncertainty_aware_summary.csv` |
| Scenario hourly CSVs | `Summer 2026 REU/different scenarios/results/scenario_48h_full_ladder/*_labels.csv` |
| Scenario metadata | `Summer 2026 REU/different scenarios/results/scenario_48h_full_ladder/experiment_metadata.json` |
| Oracle upper-bound summary | `Summer 2026 REU/oracle upper bound/results/oracle_upper_bound_summary.csv` |
| Oracle hourly CSVs | `Summer 2026 REU/oracle upper bound/results/full_hourly_outputs/oracle_dispatch_*.csv` |
| 100-MW baseload hourly CSVs | `Summer 2026 REU/100 MW baseload/results/full_hourly_outputs/*.csv` |

## Current Figures

| Step | Figure |
| --- | --- |
| Forecast RMSE | `Summer 2026 REU/causal ridge regression/figures/step1_forecast_rmse_comparison.png` |
| Forecast RMSE/MAE tradeoff | `Summer 2026 REU/causal ridge regression/figures/step1_rmse_mae_tradeoff.png` |
| Forecast example week | `Summer 2026 REU/causal ridge regression/figures/step1_example_forecast_week.png` |
| Forecast error distribution | `Summer 2026 REU/causal ridge regression/figures/step1_causal_error_distribution.png` |
| Horizon COVE improvement | `Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_improvement.png` |
| Horizon COVE values | `Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_cove.png` |
| Horizon revenue | `Summer 2026 REU/rolling horizon/figures/step2_revenue_by_horizon.png` |
| Horizon runtime/value tradeoff | `Summer 2026 REU/rolling horizon/figures/step2_runtime_value_tradeoff.png` |
| Horizon 3D tradeoff | `Summer 2026 REU/rolling horizon/figures/step2_3d_horizon_revenue_cove.png` |
| Scenario COVE improvement | `Summer 2026 REU/different scenarios/figures/step3_scenario_cove_improvement.png` |
| Scenario revenue gain | `Summer 2026 REU/different scenarios/figures/step3_scenario_revenue_gain.png` |
| Scenario revenue/COVE tradeoff | `Summer 2026 REU/different scenarios/figures/step3_revenue_cove_tradeoff.png` |
| Scenario ladder revenue | `Summer 2026 REU/different scenarios/figures/step3_ladder_revenue_progression.png` |
| Scenario 3D tradeoff | `Summer 2026 REU/different scenarios/figures/step3_3d_scenario_revenue_cove.png` |
| Oracle improvement | `Summer 2026 REU/oracle upper bound/figures/step4_oracle_improvement_by_horizon.png` |
| Oracle COVE | `Summer 2026 REU/oracle upper bound/figures/step4_oracle_cove_by_horizon.png` |
| Oracle runtime/value tradeoff | `Summer 2026 REU/oracle upper bound/figures/step4_oracle_runtime_value_tradeoff.png` |
| Oracle 3D ceiling | `Summer 2026 REU/oracle upper bound/figures/step4_3d_oracle_revenue_cove.png` |

## Step 1: Forecast Model

| Model | RMSE MW | MAE MW | Bias MW |
| --- | ---: | ---: | ---: |
| causal_lag_prediction_mw | 21.24 | 13.62 | -0.18 |
| lag1_persistence_prediction_mw | 23.60 | 14.55 | 0.00 |
| speed_power_curve_prediction_mw | 41.86 | 30.79 | -1.34 |
| rnn_preds | 46.21 | 33.31 | -3.62 |
| physics_preds | 50.85 | 36.49 | 8.59 |
| prob_preds | 71.69 | 50.42 | -0.73 |

Step 1 only checks prediction accuracy. It does not have revenue or COVE because dispatch has not happened yet.

## Step 2: Deterministic Rolling-Horizon Gurobi

The deterministic case uses the causal ridge forecast, a 75 MW direct-export reserve, the common 100 MW / 10-hour CAES storage setup, Nora/Chris storage constraints, and baseload as the comparison.

| Horizon | Direct reserve | Revenue metric | COVE | Baseload COVE | COVE improvement |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 24 h | 75 MW | 7,380,822.51 | 6.966260 | 6.887330 | -1.15% |
| 48 h | 75 MW | 7,536,863.07 | 6.822033 | 6.887330 | 0.95% |
| 72 h | 75 MW | 7,528,047.69 | 6.830021 | 6.887330 | 0.83% |
| 168 h | 75 MW | 7,508,616.74 | 6.847696 | 6.887330 | 0.58% |

The 48-hour deterministic horizon is best because it looks far enough ahead to use storage, but not so far that forecast errors dominate the plan.

## Step 3: Scenario Dispatch

The scenario case keeps the causal ridge forecast and 48-hour Gurobi lookahead. It changes the controller from one predicted future to multiple possible futures and executes only the first hour before replanning.

| Method | Revenue | Revenue gain vs baseload | COVE | COVE reduction vs baseload |
| --- | ---: | ---: | ---: | ---: |
| Baseload | 271,870,402.70 | 0.00% | 0.215746 | 0.00% |
| 1 forecast | 337,322,348.04 | 24.07% | 0.173884 | 19.40% |
| 3 scenarios | 353,949,333.45 | 30.19% | 0.165716 | 23.19% |
| 5 scenarios | 353,117,910.43 | 29.88% | 0.166106 | 23.01% |
| 7 scenarios | 353,220,656.50 | 29.92% | 0.166058 | 23.03% |
| 10 scenarios | 341,858,797.71 | 25.74% | 0.171577 | 20.47% |

The three-scenario controller is best in the full 48-hour ladder run. Five and seven scenarios are very close. Ten scenarios performs worse because it becomes too conservative.

## Step 4: Oracle Upper Bound

The oracle case keeps the same saved horizon table as Step 2 but filters to the perfect-future rows. It is not deployable because Gurobi sees actual future wind and price.

| Horizon | Revenue metric | COVE | Baseload COVE | COVE improvement |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 9,819,350.07 | 5.236266 | 6.887330 | 23.97% |
| 48 h | 10,073,630.57 | 5.104091 | 6.887330 | 25.89% |
| 72 h | 10,112,687.75 | 5.084378 | 6.887330 | 26.18% |
| 168 h | 10,116,705.90 | 5.082358 | 6.887330 | 26.21% |

The 168-hour oracle is the highest upper-bound case in the current folder.

## Constraints Confirmed

The current scenario result uses:

| Constraint or parameter | Value |
| --- | ---: |
| Storage power | 100 MW |
| Storage duration | 10 h |
| Energy capacity | 1000 MWh |
| Minimum SoC | 200 MWh |
| Initial SoC | 600 MWh |
| Round-trip efficiency | 55% |
| Grid export limit | 249 MW |
| SoC indexing | N+1 |
| Charging source | wind only |
| Grid charging | no |
| Simultaneous charge/discharge | no |
| Chronological SoC carryover | yes |
| Realized max grid violation | 0 |
| Realized max SoC violation | 0 |
| Realized max energy-balance violation | about `1e-14`, numerical roundoff |

## Archived Material

Older figures and older scenario outputs were moved to:

```text
_archive_legacy_summer_reu_figures_20260720/
_archive_legacy_summer_reu_outputs_20260720/
```

They are preserved for history but are not the current paper-facing ladder.
