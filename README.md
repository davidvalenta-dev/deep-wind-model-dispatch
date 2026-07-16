# Deep Wind Model Dispatch

This fork is now organized around the June 2026 research work on hybrid wind farm dispatch with energy storage.

## Start Here For Reproduction

For Chris/reviewer reproduction, use the frozen B6 path first. It is the
strictest package because it uses one consistent 2020 setup, raw realized LMP,
the corrected direct/curtailment execution, and a validator.

```bash
cd /Users/davidvalenta/deep-wind-model-dispatch
./venv/bin/python strategy_model/optimization/B6_CANONICAL_RUNNER.py
./venv/bin/python strategy_model/optimization/B6_FINAL_VALIDATE.py
```

Start with:

- [`Summer 2026 REU/`](Summer%202026%20REU/)
- [`PYTHON_REPRODUCTION_CHEAT_SHEET.md`](PYTHON_REPRODUCTION_CHEAT_SHEET.md)
- [`strategy_model/optimization/B6_FINAL_README.md`](strategy_model/optimization/B6_FINAL_README.md)
- [`strategy_model/optimization/B6_CANONICAL_RUNNER.py`](strategy_model/optimization/B6_CANONICAL_RUNNER.py)
- [`strategy_model/optimization/B6_FINAL_VALIDATE.py`](strategy_model/optimization/B6_FINAL_VALIDATE.py)

Important: older result folders below are research history unless they are
explicitly rerun under the B6 configuration. Do not mix their numbers with the
frozen B6 benchmark as if they use the same assumptions.

## Frozen B6 Benchmark Results

This is the current reviewer-safe computational package. It uses one consistent
setup: full 2020 Pyron wind, raw realized PYR_PYRON1 LMP, CAES-equivalent RTE
0.55, 249 MW grid cap, wind-only charging, 48-hour causal planning, 24-hour
execution, and 20% minimum/initial/final annual SoC.

| Run | Power | Duration | Energy | Raw realized revenue | QA |
| --- | ---: | ---: | ---: | ---: | --- |
| A Oracle | 100 MW | 6 h | 600 MWh | $12,927,456.69 | 0 violations |
| A Causal | 100 MW | 6 h | 600 MWh | $8,181,454.34 | 0 violations |
| B Oracle | 200 MW | 3 h | 600 MWh | $13,810,058.70 | 0 violations |
| B Causal | 200 MW | 3 h | 600 MWh | $8,196,866.97 | 0 violations |
| C Oracle | 100 MW | 10 h | 1000 MWh | $13,397,415.84 | 0 violations |
| C Causal | 100 MW | 10 h | 1000 MWh | $8,399,203.77 | 0 violations |

All six B6 hourly files contain 8,784 rows and satisfy the annual terminal SoC
rule. The validator prints `PASS`.

The simple idea is:

```text
wind data + price data + storage constraints -> optimizer / ML model -> when to charge, hold, or discharge
```

The two connected parts are:

1. **Power forecasting:** estimate wind farm power from wind/weather history.
2. **Dispatch optimization:** use the predicted or known power and electricity price to decide how storage should operate.


## June 2026 Research History Dashboard

The sections below document the broader research path. They are useful for the
project story, but they should not be compared directly against B6 unless the
experiment is rerun under the same B6 data, storage, SoC, recourse, and scoring
rules.

### 1. Power Forecasting

The new operational forecast baseline is in `power_model/src/causal_lag_forecast.py`.

It uses past power, wind speed, lag features, rolling history, and simple wind-power physics features such as speed squared and speed cubed. The output is predicted wind power in MW.

| Model | Test RMSE | Test MAE | Meaning |
| --- | ---: | ---: | --- |
| Causal lag ridge | 22.84 MW | 14.46 MW | Best tested operational power forecast |
| Lag-1 persistence | 25.26 MW | 15.69 MW | Just reuse the previous hour |
| Speed-only power curve | 43.85 MW | 31.38 MW | Uses wind speed only |
| Train mean | 71.50 MW | 61.48 MW | Weak baseline |

Files:

- Metrics: [`power_model/evaluation/causal_lag_forecast_metrics.csv`](power_model/evaluation/causal_lag_forecast_metrics.csv)
- Predictions: [`power_model/evaluation/causal_lag_forecast_predictions.csv`](power_model/evaluation/causal_lag_forecast_predictions.csv)
- Script: [`power_model/src/causal_lag_forecast.py`](power_model/src/causal_lag_forecast.py)

### 2. Nora Matching Case

This is the one-week case used to check that the Python Gurobi model matches Nora's MATLAB MILP setup.

Configuration:

| Item | Value |
| --- | ---: |
| Period | Jan. 6-12, 2020 |
| Horizon | 168 hours |
| Storage type | CAES |
| Storage power | 100 MW |
| Duration | 10 hours |
| Energy capacity | 1000 MWh |
| RTE | 55% |
| DoD | 80% |
| Cmin | 200 MWh |
| Initial SoC | 600 MWh |
| Final SoC | 600 MWh |
| Grid export cap | 249 MW |
| SoC indexing | N+1, final SoC after hour 168 |

Main raw-LMP result currently stored in the repo:

| Metric | Value |
| --- | ---: |
| Wind-only revenue | $451,354.54 |
| Baseload revenue | $432,923.47 |
| Gurobi revenue | $500,809.95 |
| Baseload COVE | 118.7663 |
| Gurobi COVE | 102.6671 |
| COVE reduction vs baseload | 13.56% |

Folder:

- [`strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/`](strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/)

Figures:

- [All plots](strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/nora_weekly_comparison_all_plots.png)
- [Wind generation](strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/wind_generation.png)
- [Electricity price](strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/electricity_price.png)
- [Delivered power](strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/delivered_power.png)
- [Net storage power](strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/net_storage_power.png)
- [State of charge](strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/state_of_charge.png)

### 3. Full Historical Gurobi Rolling-Horizon Dispatch

This is the constrained optimization benchmark over the long historical Pyron-style data.

The model keeps the battery chronological, obeys the storage limits, uses wind-only charging, prevents simultaneous charge and discharge, and enforces the grid export limit.

| Horizon | Gurobi COVE | Baseload COVE | COVE reduction | Runtime |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 1.247991 | 1.743062 | 28.40% | 16.81 s |
| 48 h | 1.203263 | 1.743062 | 30.97% | 29.23 s |
| 72 h | 1.186326 | 1.743062 | 31.94% | 45.19 s |
| 168 h | 1.179495 | 1.743062 | 32.33% | 102.59 s |

Interpretation: longer perfect-information horizons improve the result, but most of the gain already appears by 48-72 hours.

Folder:

- [`strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/`](strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/)

Figures:

- [COVE by horizon](strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/figure_01_cove_by_horizon.png)
- [Improvement by horizon](strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/figure_02_improvement_by_horizon.png)
- [Value metric by horizon](strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/figure_03_value_metric_by_horizon.png)
- [Runtime by horizon](strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/figure_04_runtime_by_horizon.png)
- [Example week SoC](strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/figure_05_example_week_soc.png)
- [Example week dispatch](strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/figure_06_example_week_dispatch.png)

### 4. Forecast-Driven Rolling-Horizon Dispatch

This is the more realistic test: plan using predicted wind/price, execute the first day, then move forward chronologically and score using what actually happened. The final causal run uses a 75 MW direct-export reserve, which protects against wind forecast underprediction under the strict planned-direct execution rule.

| Method | Horizon | Direct reserve | Revenue metric | COVE | Baseload COVE | COVE reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Causal forecast + direct reserve | 24 h | 75 MW | 7.379e6 | 7.0332 | 7.2736 | 3.31% |
| Causal forecast + direct reserve | 48 h | 75 MW | 7.611e6 | 6.8189 | 7.2736 | 6.25% |
| Causal forecast + direct reserve | 72 h | 75 MW | 7.595e6 | 6.8331 | 7.2736 | 6.06% |
| Causal forecast + direct reserve | 168 h | 75 MW | 7.545e6 | 6.8782 | 7.2736 | 5.44% |
| Oracle | 168 h | 0 MW | 1.062e7 | 4.8854 | 7.2736 | 32.83% |

Interpretation: with imperfect forecasts, the best tested reserve-adjusted causal horizon was 48 hours. The oracle result is much better because it knows the future.

Folder:

- [`strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/`](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/)

Figures:

- [Forecast vs oracle improvement](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/figure_01_forecast_vs_oracle_improvement.png)
- [Realized COVE by horizon](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/figure_02_realized_cove_by_horizon.png)
- [Realized value by horizon](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/figure_03_realized_value_by_horizon.png)
- [Forecast error by lead](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/figure_04_forecast_error_by_lead.png)
- [Forecast example week](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/figure_05_forecast_example_week.png)

### 5. Robustness And Statistics

The forecast backtest was also checked by year, forecast model, and sensitivity settings.

| Comparison | Result |
| --- | --- |
| 48 h vs 24 h | 48 h won all 9 yearly comparisons in the robustness file |
| 48 h vs 72 h | 48 h won 6 yearly comparisons |
| 48 h vs 168 h | 48 h won 8 yearly comparisons |
| Best tested wind forecast model in this folder | `NQF_RNN_target_speed_diagnostic` by COVE, but this is marked diagnostic because it is not fully causal |

Folder:

- [`strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/`](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/)

Figures:

- [Yearly horizon results](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/figure_01_yearly_horizon_results.png)
- [48h confidence intervals](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/figure_02_48h_confidence_intervals.png)
- [Forecast model comparison](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/figure_03_forecast_model_comparison.png)
- [Sensitivity analysis](strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/figure_04_sensitivity_analysis.png)

### 6. COVE-DV Teacher-Student Experiment

COVE-DV was the neural student model trained to imitate a MILP/Gurobi teacher.

The key idea was:

```text
Gurobi/MILP teacher decisions -> neural network learns dispatch policy -> test chronological COVE
```

Important result files:

- [`strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_results/cove_dv_key_results.csv`](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_results/cove_dv_key_results.csv)
- [`strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_key_results.csv`](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_key_results.csv)
- [`strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_from_rolling_gurobi_caes_100mw_24h/`](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_from_rolling_gurobi_caes_100mw_24h/)

Figures:

- [COVE-DV result](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_figures/01_cove_dv_breakthrough_result.png)
- [COVE-DV improvement](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_figures/02_cove_dv_improvement_percent.png)
- [Validation curve](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_figures/03_cove_dv_validation_curve.png)
- [Action signal example week](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_figures/04_cove_dv_action_signal_example_week.png)
- [Generation and price](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_figures/05_generation_price_example_week.png)
- [Dispatch example week](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_figures/06_cove_dv_dispatch_example_week.png)
- [Storage example week](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_figures/07_cove_dv_storage_example_week.png)
- [Nora chronological COVE-DV result](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_figures/01_nora_chronological_cove_result.png)
- [Nora chronological improvement](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_figures/02_nora_chronological_improvement.png)
- [Nora chronological training curve](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_figures/03_nora_chronological_training_curve.png)
- [Nora chronological action example week](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_figures/04_nora_chronological_action_example_week.png)
- [Nora chronological generation and price](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_figures/05_nora_chronological_generation_price.png)
- [Nora chronological dispatch example week](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_figures/06_nora_chronological_dispatch_example_week.png)
- [Nora chronological storage example week](strategy_model/optimization/archive/cove_dv_exploratory/cove_dv_nora_chronological_figures/07_nora_chronological_storage_example_week.png)

### 7. Uncertainty-Aware Scenario Dispatch

This is the newest exploratory result. Instead of optimizing one forecast, Gurobi sees several possible wind/price futures and chooses a first-hour action that works across those futures.

| Method | Revenue | Gain vs baseload | COVE reduction |
| --- | ---: | ---: | ---: |
| Single forecast closed-loop gated | $209.948M | 16.22% | 13.95% |
| Three-scenario closed-loop gated | $210.298M | 16.41% | 14.10% |
| Five-scenario closed-loop gated | $211.597M | 17.13% | 14.62% |
| Seven-scenario closed-loop gated | $212.098M | 17.41% | 14.83% |
| Ten-scenario closed-loop gated | $205.264M | 13.62% | 11.99% |

Interpretation: seven scenarios gave the best tested uncertainty-aware dispatch. Ten scenarios was worse because the extra extreme futures made the controller more conservative.

Folder:

- [`strategy_model/optimization/uncertainty_aware_dispatch_results/`](strategy_model/optimization/uncertainty_aware_dispatch_results/)

Figures:

- [Revenue breakthrough](strategy_model/optimization/uncertainty_aware_dispatch_results/final_figure_01_revenue_breakthrough.png)
- [COVE breakthrough](strategy_model/optimization/uncertainty_aware_dispatch_results/final_figure_02_cove_breakthrough.png)
- [Example week dispatch](strategy_model/optimization/uncertainty_aware_dispatch_results/final_figure_03_example_week_dispatch.png)
- [Uncertainty pipeline](strategy_model/optimization/uncertainty_aware_dispatch_results/final_figure_04_uncertainty_pipeline.png)

### 8. New Public Proxy Data

A new public-data pipeline was added to build a Pyron-shaped proxy dataset from currently available pieces.

Important caveat: the `power` column is a proxy based on ERCOT West-zone generation, not verified plant-level Pyron measured power.

Files:

- [`data/newest_pyron_shaped/newest_pyron_shaped_dataset_2026070701_2026070712.csv`](data/newest_pyron_shaped/newest_pyron_shaped_dataset_2026070701_2026070712.csv)
- [`data/newest_pyron_shaped/pyron_proxy_continuation_2024010101_2026070712_available_rows.csv`](data/newest_pyron_shaped/pyron_proxy_continuation_2024010101_2026070712_available_rows.csv)
- [`scripts/build_newest_pyron_shaped_dataset.py`](scripts/build_newest_pyron_shaped_dataset.py)

Proxy validation result:

| Horizon | Baseload COVE | Gurobi COVE | COVE reduction |
| ---: | ---: | ---: | ---: |
| 24 h | 23.4913 | 23.3139 | 0.76% |
| 48 h | 23.4913 | 23.3139 | 0.76% |
| 72 h | 23.4913 | 23.3139 | 0.76% |
| 168 h | 23.4913 | 23.3139 | 0.76% |

Folder:

- [`strategy_model/optimization/proxy_validation_results/`](strategy_model/optimization/proxy_validation_results/)

Figures:

- [Proxy COVE by horizon](strategy_model/optimization/proxy_validation_results/proxy_cove_by_horizon.png)
- [Proxy COVE improvement](strategy_model/optimization/proxy_validation_results/proxy_cove_improvement_by_horizon.png)
- [Proxy revenue by horizon](strategy_model/optimization/proxy_validation_results/proxy_revenue_by_horizon.png)
- [Proxy example week dispatch](strategy_model/optimization/proxy_validation_results/proxy_example_week_dispatch.png)

## Gurobi Model Constraints

The corrected Gurobi/MILP dispatch model uses the following physical constraints.

| Constraint | Meaning | Equation form |
| --- | --- | --- |
| SoC bounds | Battery cannot be too empty or too full | `Cmin <= SoC[t] <= Cmax` |
| Charge power | Cannot charge above storage rating | `0 <= P_ch[t] <= P_ES * u[t]` |
| Discharge power | Cannot discharge above storage rating | `0 <= P_dis[t] <= P_ES * (1 - u[t])` |
| Binary mode | Cannot charge and discharge at the same time | `u[t] in {0, 1}` |
| Available energy | Cannot discharge energy that is not in storage | `P_dis[t] / RTE <= SoC[t] - Cmin` |
| Wind-only charging | Storage can only charge from wind not sent directly | `P_dir[t] + P_ch[t] <= P_gen[t]` |
| Delivered power | Grid gets direct wind plus storage discharge | `P_delivered[t] = P_dir[t] + P_dis[t]` |
| Grid cap | Delivered power cannot exceed grid rating | `0 <= P_delivered[t] <= P_rated_grid` |
| SoC update | Battery changes hour by hour | `SoC[t+1] = SoC[t] + P_ch[t] - P_dis[t] / RTE` |
| Initial SoC | First window starts from the configured battery state | `SoC[0] = SoC_initial` |
| Chronological carryover | Later windows start from the previous executed battery state | `next SoC[0] = previous final SoC` |
| Terminal condition | Some experiments close the lookahead battery balance | `SoC[end] = SoC[0]` when selected |

## Revenue And COVE

Revenue is calculated as:

```python
revenue = sum(price[t] * delivered_power[t] for t in hours)
```

COVE is calculated as:

```python
cove = dispatch_cost / sum(price[t] * delivered_power[t] for t in hours)
```

So lower COVE is better because the same cost is being divided by more valuable delivered energy.

## Repository Map

| Folder | What it is |
| --- | --- |
| [`data/`](data/) | Processed historical data and new public proxy datasets |
| [`power_model/`](power_model/) | Power forecasting models and evaluations |
| [`strategy_model/`](strategy_model/) | Dispatch policy models and optimization experiments |
| [`strategy_model/optimization/`](strategy_model/optimization/) | Gurobi/MILP, COVE-DV, horizon, forecast, scenario, and Nora comparison experiments |
| [`scripts/`](scripts/) | Helper scripts for building public proxy data |

## Setup

From the repo root:

```bash
python3.11 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
pip install gurobipy
```

A Gurobi license is required for the Gurobi/MILP experiments.

## Large File Policy

The repo tracks scripts, READMEs, figures, summaries, and compact result tables.

The largest generated label/checkpoint CSVs are ignored because GitHub rejects very large files. They can be regenerated from the scripts.
