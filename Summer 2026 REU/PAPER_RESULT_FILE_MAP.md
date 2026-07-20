# Paper Result File Map

This file gives the current official paper-facing ladder. Use this map when writing the paper or showing a reviewer where each number comes from.

## Official Ladder

| Step | Question | Command | Main result |
| --- | --- | --- | ---: |
| 1 | Which power forecast is best? | `Summer 2026 REU/causal ridge regression/RUN_1_FORECAST_RMSE.py` | causal lag / ridge-style forecast, 21.24 MW RMSE |
| 2 | Which deterministic rolling horizon is best? | `Summer 2026 REU/rolling horizon/RUN_2_ROLLING_HORIZON.py` | 48 h horizon, 6.25% COVE improvement vs baseload |
| 3 | Do forecast scenarios improve dispatch? | `Summer 2026 REU/different scenarios/RUN_3_SCENARIO_COMPARISON.py` | 3 scenarios, 23.19% COVE reduction vs baseload |
| Context | What is the perfect-information upper bound? | printed by `RUN_2_ROLLING_HORIZON.py` | 168 h oracle, 32.83% COVE improvement vs baseload |

## Current Result Files

| Result | File |
| --- | --- |
| Forecast model comparison | `Summer 2026 REU/causal ridge regression/results/forecast_model_rmse_comparison.csv` |
| Deterministic rolling horizon summary | `Summer 2026 REU/rolling horizon/results/causal_ridge_rolling_horizon_summary.csv` |
| Scenario summary | `Summer 2026 REU/different scenarios/results/scenario_48h_full_ladder/uncertainty_aware_summary.csv` |
| Scenario metadata | `Summer 2026 REU/different scenarios/results/scenario_48h_full_ladder/experiment_metadata.json` |

## Current Figures

| Step | Figure |
| --- | --- |
| Forecast RMSE | `Summer 2026 REU/causal ridge regression/figures/step1_forecast_rmse_comparison.png` |
| Horizon COVE improvement | `Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_improvement.png` |
| Horizon COVE values | `Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_cove.png` |
| Scenario COVE improvement | `Summer 2026 REU/different scenarios/figures/step3_scenario_cove_improvement.png` |
| Scenario revenue gain | `Summer 2026 REU/different scenarios/figures/step3_scenario_revenue_gain.png` |

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

The deterministic case uses the causal ridge forecast, a 75 MW direct-export reserve, Nora/Chris storage constraints, and baseload as the comparison.

| Horizon | Direct reserve | Revenue metric | COVE | Baseload COVE | COVE improvement |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 24 h | 75 MW | 7,378,742.01 | 7.033181 | 7.273584 | 3.31% |
| 48 h | 75 MW | 7,610,575.51 | 6.818936 | 7.273584 | 6.25% |
| 72 h | 75 MW | 7,594,786.43 | 6.833112 | 7.273584 | 6.06% |
| 168 h | 75 MW | 7,544,993.73 | 6.878207 | 7.273584 | 5.44% |

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
