# Deep Wind Model Dispatch

This repository contains the Summer 2026 REU work on forecast-aware dispatch for a hybrid wind farm with energy storage. The final paper-facing workflow is organized as a realistic ladder plus an oracle upper bound:

```text
baseload -> choose forecast model -> choose rolling window -> choose scenario count
                                      -> compare with oracle upper bound
```

The clean reproduction folder is:

[`Summer 2026 REU/`](Summer%202026%20REU/)

## Current Paper-Facing Results

| Ladder step | What changes | Best result |
| --- | --- | ---: |
| Baseload | Reference case: sell/store by the baseline rule | 0.00% COVE improvement |
| Forecast model | Compare power forecasts by RMSE | causal lag / ridge-style forecast, 21.24 MW RMSE |
| Rolling-horizon Gurobi | Use the selected forecast and test 24/48/72/168 h windows | 48 h window, 0.95% COVE improvement |
| Scenario dispatch | Use the selected forecast/window and test 1/3/5/7/10 futures | 3 scenarios, 23.19% COVE reduction and 30.19% revenue gain |
| Oracle upper bound | Perfect future wind and price, not deployable | 168 h oracle, 26.21% COVE improvement |

The final realistic method is:

```text
causal ridge forecast + 48-hour Gurobi lookahead + 3-scenario dispatch
```

The oracle upper bound is not realistic. It gives Gurobi the actual future wind and price to show the ceiling: `168 h oracle = 26.21% COVE improvement`.

## Run The Ladder

Run one command in each folder. To change a horizon, SoC value, storage size,
scenario count, output folder, or other experiment setting, open the
`EXPERIMENT_KNOBS.py` file inside that same folder first. The `RUN_*.py` command
then reruns the experiment from those knobs and writes fresh summaries, hourly
CSVs, and figures into `results/current_run_from_knobs/`.

Example: to test a 35-hour oracle horizon, edit
`Summer 2026 REU/oracle upper bound/EXPERIMENT_KNOBS.py` and set
`HORIZONS = [35]`, then run `RUN_4_ORACLE_UPPER_BOUND.py`.

### 1. Forecast Model

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

Output:

| Forecast method | RMSE |
| --- | ---: |
| causal lag / ridge-style forecast | 21.24 MW |
| lag-1 persistence | 23.60 MW |
| speed-to-power curve | 41.86 MW |
| RNN | 46.21 MW |
| physics model | 50.85 MW |
| probabilistic model | 71.69 MW |

### 2. Rolling-Horizon Gurobi

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

Output:

| Horizon | Direct reserve | COVE | COVE improvement vs baseload | Revenue metric |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 75 MW | 6.966260 | -1.15% | 7,380,822.51 |
| 48 h | 75 MW | 6.822033 | 0.95% | 7,536,863.07 |
| 72 h | 75 MW | 6.830021 | 0.83% | 7,528,047.69 |
| 168 h | 75 MW | 6.847696 | 0.58% | 7,508,616.74 |

The 48-hour window is best because it looks far enough ahead to use storage, but not so far that forecast errors dominate the plan.

### 3. Scenario Dispatch

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

Output:

| Method | Revenue | Revenue gain vs baseload | COVE | COVE reduction vs baseload |
| --- | ---: | ---: | ---: | ---: |
| Baseload | $271,870,402.70 | 0.00% | 0.215746 | 0.00% |
| 1 forecast | $337,322,348.04 | 24.07% | 0.173884 | 19.40% |
| 3 scenarios | $353,949,333.45 | 30.19% | 0.165716 | 23.19% |
| 5 scenarios | $353,117,910.43 | 29.88% | 0.166106 | 23.01% |
| 7 scenarios | $353,220,656.50 | 29.92% | 0.166058 | 23.03% |
| 10 scenarios | $341,858,797.71 | 25.74% | 0.171577 | 20.47% |

Three scenarios is the best tested case in the current 48-hour ladder. Five and seven are very close; ten is worse because it becomes too conservative.

### 4. Oracle Upper Bound

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

Output:

| Horizon | COVE | COVE improvement vs baseload | Revenue metric |
| ---: | ---: | ---: | ---: |
| 24 h | 5.236266 | 23.97% | 9,819,350.07 |
| 48 h | 5.104091 | 25.89% | 10,073,630.57 |
| 72 h | 5.084378 | 26.18% | 10,112,687.75 |
| 168 h | 5.082358 | 26.21% | 10,116,705.90 |

The 168-hour oracle is the best upper-bound case because it sees the most future information.

## Current Figures

| Figure | Path |
| --- | --- |
| Forecast RMSE | [`Summer 2026 REU/causal ridge regression/figures/step1_forecast_rmse_comparison.png`](Summer%202026%20REU/causal%20ridge%20regression/figures/step1_forecast_rmse_comparison.png) |
| Forecast RMSE/MAE tradeoff | [`Summer 2026 REU/causal ridge regression/figures/step1_rmse_mae_tradeoff.png`](Summer%202026%20REU/causal%20ridge%20regression/figures/step1_rmse_mae_tradeoff.png) |
| Forecast example week | [`Summer 2026 REU/causal ridge regression/figures/step1_example_forecast_week.png`](Summer%202026%20REU/causal%20ridge%20regression/figures/step1_example_forecast_week.png) |
| Forecast error distribution | [`Summer 2026 REU/causal ridge regression/figures/step1_causal_error_distribution.png`](Summer%202026%20REU/causal%20ridge%20regression/figures/step1_causal_error_distribution.png) |
| Horizon improvement | [`Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_improvement.png`](Summer%202026%20REU/rolling%20horizon/figures/step2_causal_horizon_improvement.png) |
| Horizon COVE | [`Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_cove.png`](Summer%202026%20REU/rolling%20horizon/figures/step2_causal_horizon_cove.png) |
| Horizon revenue | [`Summer 2026 REU/rolling horizon/figures/step2_revenue_by_horizon.png`](Summer%202026%20REU/rolling%20horizon/figures/step2_revenue_by_horizon.png) |
| Horizon runtime/value tradeoff | [`Summer 2026 REU/rolling horizon/figures/step2_runtime_value_tradeoff.png`](Summer%202026%20REU/rolling%20horizon/figures/step2_runtime_value_tradeoff.png) |
| Horizon 3D tradeoff | [`Summer 2026 REU/rolling horizon/figures/step2_3d_horizon_revenue_cove.png`](Summer%202026%20REU/rolling%20horizon/figures/step2_3d_horizon_revenue_cove.png) |
| Scenario COVE improvement | [`Summer 2026 REU/different scenarios/figures/step3_scenario_cove_improvement.png`](Summer%202026%20REU/different%20scenarios/figures/step3_scenario_cove_improvement.png) |
| Scenario revenue gain | [`Summer 2026 REU/different scenarios/figures/step3_scenario_revenue_gain.png`](Summer%202026%20REU/different%20scenarios/figures/step3_scenario_revenue_gain.png) |
| Scenario revenue/COVE tradeoff | [`Summer 2026 REU/different scenarios/figures/step3_revenue_cove_tradeoff.png`](Summer%202026%20REU/different%20scenarios/figures/step3_revenue_cove_tradeoff.png) |
| Scenario ladder revenue | [`Summer 2026 REU/different scenarios/figures/step3_ladder_revenue_progression.png`](Summer%202026%20REU/different%20scenarios/figures/step3_ladder_revenue_progression.png) |
| Scenario 3D tradeoff | [`Summer 2026 REU/different scenarios/figures/step3_3d_scenario_revenue_cove.png`](Summer%202026%20REU/different%20scenarios/figures/step3_3d_scenario_revenue_cove.png) |
| Oracle upper bound | [`Summer 2026 REU/oracle upper bound/figures/step4_oracle_improvement_by_horizon.png`](Summer%202026%20REU/oracle%20upper%20bound/figures/step4_oracle_improvement_by_horizon.png) |
| Oracle COVE | [`Summer 2026 REU/oracle upper bound/figures/step4_oracle_cove_by_horizon.png`](Summer%202026%20REU/oracle%20upper%20bound/figures/step4_oracle_cove_by_horizon.png) |
| Oracle runtime/value tradeoff | [`Summer 2026 REU/oracle upper bound/figures/step4_oracle_runtime_value_tradeoff.png`](Summer%202026%20REU/oracle%20upper%20bound/figures/step4_oracle_runtime_value_tradeoff.png) |
| Oracle 3D ceiling | [`Summer 2026 REU/oracle upper bound/figures/step4_3d_oracle_revenue_cove.png`](Summer%202026%20REU/oracle%20upper%20bound/figures/step4_3d_oracle_revenue_cove.png) |

## Storage And Dispatch Constraints

The Gurobi/MILP dispatch model follows the Nora/Chris operating constraints: wind-only charging, no grid charging, no simultaneous charge/discharge, grid export cap, chronological SoC, and N+1 SoC indexing.

The paper-facing dispatch folders use the 100 MW, 10 h Nora/Chris CAES setup:

| Item | Value |
| --- | ---: |
| Storage power | 100 MW |
| Storage duration | 10 h |
| Energy capacity | 1000 MWh |
| Minimum SoC | 200 MWh |
| Initial SoC | 600 MWh |
| Round-trip efficiency | 55% |
| Grid export limit | 249 MW |
| Charging source | wind only |
| Grid charging | no |
| Simultaneous charge/discharge | no |
| Chronological SoC carryover | yes |
| SoC indexing | N+1 |

The deterministic rolling-horizon, oracle, and scenario folders now all use the common 100 MW / 10-hour storage setup. Older 100 MW / 24-hour results are preserved only as legacy material and are not the current paper-facing numbers.

The latest 48-hour scenario run had zero grid/SoC violations and only numerical roundoff around `1e-14` in balance checks.

## Revenue And COVE

Revenue is calculated from realized delivered power and realized price:

```python
revenue = sum(price[t] * delivered_power[t] for t in hours)
```

COVE is calculated as:

```python
cove = annualized_cost / revenue
```

Lower COVE is better because the same annualized cost is divided by more valuable delivered energy.

## Repository Map

| Folder | Purpose |
| --- | --- |
| [`Summer 2026 REU/`](Summer%202026%20REU/) | Current paper-facing reproduction ladder |
| [`power_model/`](power_model/) | Wind/power forecasting models and evaluation files |
| [`strategy_model/`](strategy_model/) | Dispatch, Gurobi/MILP, scenario, and benchmark experiments |
| [`strategy_model/optimization/`](strategy_model/optimization/) | Main optimization scripts and result folders |
| [`docs/`](docs/) | Meeting notes, architecture notes, and paper-direction documents |
| [`data/`](data/) | Processed datasets and public proxy/DAM data work |

## B6 Verification Package

The B6 package is a separate 2020 verification task requested by Chris. It is not the main paper ladder, but it validates the implementation under a frozen one-year setup.

Useful files:

- [`Summer 2026 REU/b6 verification/code/B6_CANONICAL_RUNNER.py`](Summer%202026%20REU/b6%20verification/code/B6_CANONICAL_RUNNER.py)
- [`Summer 2026 REU/b6 verification/code/B6_FINAL_VALIDATE.py`](Summer%202026%20REU/b6%20verification/code/B6_FINAL_VALIDATE.py)
- [`Summer 2026 REU/b6 verification/`](Summer%202026%20REU/b6%20verification/)

## Setup

```bash
python3.11 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
pip install gurobipy
```

A Gurobi license is required for the optimization experiments.

## Archived Material

Older figures and older scenario outputs were preserved in archive folders so the current `Summer 2026 REU` folder only shows the final ladder:

```text
_archive_legacy_summer_reu_figures_20260720/
_archive_legacy_summer_reu_outputs_20260720/
```

Those files are history, not the current paper-facing result set.
