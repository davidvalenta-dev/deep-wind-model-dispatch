# Paper Result File Map

This document maps the paper claims to the exact repository files that produced or store the numbers. Use this when writing the manuscript, answering Chris, or showing a reviewer how each result can be traced back to code.

## Main Paper Story

The paper should focus on three connected pieces:

1. Forecasting: causal ridge/lag-style forecasts for wind generation and price.
2. Dispatch: rolling-horizon Gurobi/MILP optimization under storage constraints.
3. Uncertainty: scenario-based dispatch using multiple possible wind and price futures.

B6 is a separate 2020 verification benchmark. It is useful for proving that the code mechanics, SoC rules, raw LMP revenue calculation, and planned-direct execution logic are correct, but it is not the main multi-year paper result.

## One-Sentence Version

The main paper numbers come from `run_uncertainty_aware_dispatch.py` and `forecast_backtest_rolling_horizons.py`; the shared Gurobi storage constraints are in `rolling_horizon_gurobi_dispatch.py`; COVE and revenue formulas are in `strategy_model/src/util.py`; and the B6 verification package is in `B6_CANONICAL_RUNNER.py` plus `b6_final_results/`.

## Result Map

| Paper topic | What it means | Main runner/code | Main result files | Figures |
| --- | --- | --- | --- | --- |
| Scenario dispatch | Gurobi sees several possible 24-hour wind/price futures and chooses an action that works across them | `strategy_model/optimization/run_uncertainty_aware_dispatch.py` | `strategy_model/optimization/uncertainty_aware_dispatch_results/final_breakthrough_summary.csv`; `strategy_model/optimization/uncertainty_aware_dispatch_results/uncertainty_aware_summary.csv` | `strategy_model/optimization/uncertainty_aware_dispatch_results/final_figure_01_revenue_breakthrough.png`; `final_figure_02_cove_breakthrough.png`; `final_figure_03_example_week_dispatch.png`; `final_figure_04_uncertainty_pipeline.png` |
| Best scenario result | Seven-scenario closed-loop gated case | Same as above | Same as above | Same as above |
| Causal ridge / forecast backtest | Forecast model predicts future generation and price; Gurobi dispatches using those predictions | `strategy_model/optimization/forecast_backtest_rolling_horizons.py` | `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_summary.csv`; `forecast_accuracy_by_lead.csv`; `forecast_dispatch_24h.csv`; `forecast_dispatch_48h.csv`; `forecast_dispatch_72h.csv`; `forecast_dispatch_168h.csv` | `figure_01_forecast_vs_oracle_improvement.png`; `figure_02_realized_cove_by_horizon.png`; `figure_03_realized_value_by_horizon.png`; `figure_04_forecast_error_by_lead.png`; `figure_05_forecast_example_week.png` |
| Oracle upper bound | Gurobi gets actual future wind and price, so it is not deployable; it is the best-case comparison | `strategy_model/optimization/forecast_backtest_rolling_horizons.py` | `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/oracle_dispatch_24h.csv`; `oracle_dispatch_48h.csv`; `oracle_dispatch_72h.csv`; `oracle_dispatch_168h.csv`; summarized in `forecast_dispatch_summary.csv` | Same forecast backtest figures |
| Rolling-horizon Gurobi solver | The actual MILP/Gurobi storage model: charge, discharge, direct wind, delivered power, SoC, constraints | `strategy_model/optimization/rolling_horizon_gurobi_dispatch.py` | Used by older rolling-horizon/COVE-DV experiments; exact output depends on caller | `strategy_model/optimization/rolling_horizon_gurobi_results/` |
| Robustness/statistics | Year-by-year horizon comparison, confidence intervals, forecast method comparison, sensitivity | `strategy_model/optimization/analyze_forecast_backtest_robustness.py` | `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/yearly_horizon_results.csv`; `paired_statistical_tests.csv`; `yearly_win_counts.csv`; `forecast_model_comparison.csv`; `sensitivity_results.csv` | `figure_01_yearly_horizon_results.png`; `figure_02_48h_confidence_intervals.png`; `figure_03_forecast_model_comparison.png`; `figure_04_sensitivity_analysis.png` |
| Revenue and COVE formulas | Revenue is sum of power times price; COVE is cost divided by valued revenue | `strategy_model/src/util.py` | Called by the dispatch runners | No standalone figure |
| B6 verification | Frozen 2020 check requested by Chris: A/B/C x Oracle/Causal using raw realized LMP | `strategy_model/optimization/B6_CANONICAL_RUNNER.py` | `strategy_model/optimization/b6_final_results/David_B6_run_summary.csv`; `David_B6_QA_summary.csv`; six hourly CSV files; logs | Not the main paper figures |

## Scenario Dispatch Numbers

Use these for the scenario/uncertainty part of the paper.

Source file:

`strategy_model/optimization/uncertainty_aware_dispatch_results/final_breakthrough_summary.csv`

Key result:

| Method | Test period | Baseload revenue | Dispatch revenue | Revenue gain vs baseload | Baseload COVE | Dispatch COVE | COVE reduction vs baseload |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Seven-scenario closed-loop gated | 2014-01-01 to 2023-12-29 | $180,653,095.06 | $212,097,824.78 | 17.41% | 0.324684 | 0.276547 | 14.83% |
| Five-scenario closed-loop gated | 2014-01-01 to 2023-12-29 | $180,653,095.06 | $211,596,820.64 | 17.13% | 0.324684 | 0.277202 | 14.62% |
| Three-scenario closed-loop gated | 2014-01-01 to 2023-12-29 | $180,653,095.06 | $210,298,180.87 | 16.41% | 0.324684 | 0.278914 | 14.10% |
| Single forecast closed-loop gated | 2014-01-01 to 2023-12-29 | $180,653,095.06 | $209,947,648.70 | 16.22% | 0.324684 | 0.279380 | 13.95% |
| Ten-scenario closed-loop gated | 2014-01-01 to 2023-12-29 | $180,653,095.06 | $205,263,577.22 | 13.62% | 0.324684 | 0.285755 | 11.99% |

How to describe it:

The seven-scenario controller was the strongest scenario result in this run. The ten-scenario controller was worse because adding more scenarios can make the controller too conservative; more futures do not automatically mean better dispatch.

What not to claim:

Do not say this is the B6 result. Do not say this is the same as the 2020 frozen benchmark. It is the multi-year scenario dispatch result.

## Causal Ridge / Forecast Backtest Numbers

Use these for the causal forecast and horizon comparison part of the paper.

Source files:

- `strategy_model/optimization/forecast_backtest_rolling_horizons.py`
- `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_summary.csv`
- `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/experiment_metadata.json`

Metadata from the result folder:

| Item | Value |
| --- | --- |
| Forecast training period in metadata | 1980-01-01 01:00:00 through 2013-12-31 23:00:00 |
| Backtest period in metadata | 2014-01-01 00:00:00 through 2023-12-29 20:00:00 |
| Storage | CAES |
| Storage rating | 100 MW |
| Storage duration | 24 hours |
| Capacity | 2400 MWh |
| RTE | 0.55 |
| Grid limit | 249 MW |
| Best causal forecast horizon | 48 hours |

Key result:

| Method | Horizon | Revenue metric | Baseload revenue metric | COVE | Baseload COVE | COVE reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Causal forecast | 24 h | 7,900,680.73 | 7,134,863.37 | 6.568551 | 7.273584 | 9.69% |
| Causal forecast | 48 h | 8,137,281.56 | 7,134,863.37 | 6.377563 | 7.273584 | 12.32% |
| Causal forecast | 72 h | 8,121,648.93 | 7,134,863.37 | 6.389838 | 7.273584 | 12.15% |
| Causal forecast | 168 h | 8,069,691.73 | 7,134,863.37 | 6.430980 | 7.273584 | 11.58% |
| Oracle | 24 h | 9,932,289.40 | 7,134,863.37 | 5.224981 | 7.273584 | 28.16% |
| Oracle | 48 h | 10,370,623.54 | 7,134,863.37 | 5.004137 | 7.273584 | 31.20% |
| Oracle | 72 h | 10,529,444.46 | 7,134,863.37 | 4.928657 | 7.273584 | 32.24% |
| Oracle | 168 h | 10,605,317.62 | 7,134,863.37 | 4.893397 | 7.273584 | 32.72% |

How to describe it:

The causal forecast result is realistic because Gurobi uses forecasts rather than the actual future. The oracle result is not realistic but shows the upper bound if future wind and price were known. In the causal forecast backtest, 48 hours was best; in the oracle case, longer lookahead helped more because there was no forecast error.

What not to claim:

Do not mix the `revenue_metric` values from this normalized-price backtest with the raw USD values from the scenario result or B6. They are different result sets.

## Robustness and Statistics Files

Use these when the paper needs year-by-year support.

Folder:

`strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/`

Important files:

| File | What it supports |
| --- | --- |
| `yearly_horizon_results.csv` | Year-by-year causal horizon results |
| `yearly_win_counts.csv` | Counts which horizon won each year |
| `paired_statistical_tests.csv` | Confidence intervals and sign-flip tests |
| `forecast_model_comparison.csv` | Forecast model comparison |
| `sensitivity_results.csv` | Storage/sensitivity checks |
| `analysis_metadata.json` | Analysis settings and caveats |

Important robustness result:

| Comparison | Years | 48h wins | Mean value difference | 95% CI | p-value |
| --- | ---: | ---: | ---: | --- | ---: |
| 48h minus 24h | 9 | 9 | 24,600.95 | [7,880.34, 47,391.92] | 0.003906 |
| 48h minus 72h | 9 | 6 | 737.69 | [-105.91, 1,604.58] | 0.156250 |
| 48h minus 168h | 9 | 8 | 5,737.26 | [1,290.18, 12,917.40] | 0.019531 |

Horizon wins:

| Horizon | Years won |
| ---: | ---: |
| 24 h | 0 |
| 48 h | 6 |
| 72 h | 2 |
| 168 h | 1 |

How to describe it:

The 48-hour horizon is the strongest practical horizon in the robustness analysis, especially compared with 24 hours and 168 hours. The 48-hour versus 72-hour difference is smaller and less statistically decisive.

## Shared Gurobi Dispatch Solver

Important file:

`strategy_model/optimization/rolling_horizon_gurobi_dispatch.py`

This file contains:

- `solve_window(...)`: builds the Gurobi MILP.
- `continuous_baseload(...)`: builds the baseload comparison.
- `cove_value(...)`: calls the COVE function.
- `check_constraints(...)`: checks physical constraint violations.

Main constraints inside `solve_window(...)`:

| Constraint | Meaning |
| --- | --- |
| `soc[0] == start_soc` | Battery starts each optimization window at the carried-forward SoC |
| `soc[hours] == start_soc` when terminal policy is equal-initial | Terminal SoC condition for that window |
| `p_dir[t] + p_ch[t] <= generation[t]` | Storage charges only from wind; no grid charging |
| `p_delivered[t] == p_dir[t] + p_dis[t]` | Delivered power equals direct wind plus discharge |
| `p_ch[t] <= rating * u[t]` | Binary charge mode |
| `p_dis[t] <= rating * (1 - u[t])` | Binary discharge mode |
| `p_dis[t] / rte <= soc[t] - min_soc` | Cannot discharge energy that is not available above minimum SoC |
| `soc[t + 1] == soc[t] + p_ch[t] - p_dis[t] / rte` | Chronological battery update |
| Objective `sum(price[t] * p_delivered[t])` | Maximize value/revenue over the planning window |

## Revenue and COVE Formula Files

Important file:

`strategy_model/src/util.py`

Functions:

- `revenue(power, price)`: computes `sum(power * price)`.
- `cove(power, price, ...)`: computes annualized cost divided by revenue/value.
- `get_storage_specs(...)`: gets storage cost and efficiency assumptions.
- `get_rte(...)`: gets round-trip efficiency for storage type.

Simple explanation:

Revenue measures how much money/value the delivered power earns. COVE measures cost per valued energy. Lower COVE is better.

## B6 Verification Package

Use this only as validation, not as the main paper result.

Files:

| File/folder | Purpose |
| --- | --- |
| `strategy_model/optimization/B6_CANONICAL_RUNNER.py` | Final frozen 2020 benchmark runner |
| `strategy_model/optimization/B6_FINAL_VALIDATE.py` | Verifies rows, revenue, SoC, and constraints |
| `strategy_model/optimization/b6_final_results/David_B6_run_summary.csv` | Six-run summary |
| `strategy_model/optimization/b6_final_results/David_B6_QA_summary.csv` | QA checks |
| `strategy_model/optimization/b6_final_results/David_B6_frozen_config.json` | Frozen configuration |
| `strategy_model/optimization/b6_final_results/*.csv` | Six hourly output files |

What B6 proves:

B6 proves the corrected code can run a clean 2020 benchmark with raw realized LMP, common annual SoC rule, planned-direct wind execution, zero constraint violations, and reproducible hourly CSVs.

What B6 does not prove:

B6 is not the full nine-year paper result. It is a clean verification package.

## Suggested Paper Wording

Use this wording to avoid mixing result sets:

"The main paper experiments evaluate forecast-aware and scenario-aware rolling-horizon dispatch over the 2014-2023 Pyron backtest period. The scenario result is reported using realized raw revenue and COVE reduction relative to baseload. A separate B6 2020 benchmark is used only as a verification package to confirm the MILP implementation, SoC accounting, direct-wind execution, and raw-LMP revenue calculation under a frozen configuration."

## Do Not Mix These Numbers

| Result set | Period | Main purpose | Main file |
| --- | --- | --- | --- |
| Forecast backtest | 2014-2023 | Horizon/oracle/causal comparison | `forecast_dispatch_summary.csv` |
| Scenario dispatch | 2014-2023 | Main uncertainty-aware paper result | `final_breakthrough_summary.csv` |
| Robustness | Complete years inside 2014-2023 | Yearly statistics and CI | `forecast_backtest_robustness/` |
| B6 | 2020 only | Verification requested by Chris | `b6_final_results/` |
| COVE-DV / teacher-student | Earlier exploratory work | Historical ML idea, not the main final paper result | `cove_dv_*` folders |

