# Summer 2026 REU Figure Index

All 34 figures are generated from frozen CSV outputs by
`common/regenerate_all_figures.py`. The palette is deliberately restrained:
navy and teal identify the main methods, while gray, steel, and muted plum
provide comparison colors. No 3D chart is used in the final set.

## Step 0: 100 MW Constant-Output Benchmark

| File | Question answered |
| --- | --- |
| `100 MW baseload/figures/step0_100mw_baseload_2014_2023_example_week.png` | How does the rule deliver toward 100 MW while storage SoC changes? |
| `100 MW baseload/figures/step0_energy_flow_totals.png` | How much energy was delivered, shifted, curtailed, or left as shortfall? |
| `100 MW baseload/figures/step0_soc_duration_curve.png` | How often did storage operate near its lower or upper SoC limit? |
| `100 MW baseload/figures/step0_annual_raw_revenue.png` | How did raw realized revenue vary by evaluation year? |

## Step 1: Causal Forecast Selection

| File | Question answered |
| --- | --- |
| `causal ridge regression/figures/step1_forecast_rmse_comparison.png` | Which tested forecast has the lowest RMSE? |
| `causal ridge regression/figures/step1_rmse_mae_tradeoff.png` | Do the RMSE and MAE rankings agree? |
| `causal ridge regression/figures/step1_example_forecast_week.png` | What do actual power and causal forecasts look like hour by hour? |
| `causal ridge regression/figures/step1_causal_error_distribution.png` | Is the causal forecast centered, and how wide are typical errors? |
| `causal ridge regression/figures/step1_actual_vs_predicted_density.png` | Where do actual and predicted power pairs occur most often? |
| `causal ridge regression/figures/step1_error_by_power_bin.png` | Does forecast error change with operating power? |
| `causal ridge regression/figures/step1_dispatch_forecast_accuracy_by_lead.png` | How does forecast accuracy change farther into the future? |
| `causal ridge regression/figures/step1_split_stability.png` | Does the method remain competitive across train, validation, and test splits? |

## Step 2: Deterministic Rolling Horizon

| File | Question answered |
| --- | --- |
| `rolling horizon/figures/step2_controlled_hourly_horizon_improvement.png` | How does COVE reduction change from 24 to 168 hours? |
| `rolling horizon/figures/step2_controlled_hourly_horizon_cove.png` | What is the absolute COVE at each planning horizon? |
| `rolling horizon/figures/step2_controlled_hourly_horizon_revenue.png` | What revenue metric is associated with each horizon? |
| `rolling horizon/figures/step2_incremental_cove_gain.png` | How much additional value is gained by each horizon extension? |
| `rolling horizon/figures/step2_runtime_value_tradeoff.png` | What computational cost accompanies the COVE improvement? |
| `rolling horizon/figures/step2_revenue_cove_small_multiples.png` | Do revenue and COVE move consistently across horizons? |
| `rolling horizon/figures/step2_horizon_scorecard.png` | Which horizon balances revenue, COVE, and runtime? |

## Step 3: Scenario-Count Sweep

| File | Question answered |
| --- | --- |
| `different scenarios/figures/step3_scenario_cove_improvement.png` | Did more forecast futures improve COVE reduction? |
| `different scenarios/figures/step3_scenario_revenue_gain.png` | Did more forecast futures improve the revenue metric? |
| `different scenarios/figures/step3_revenue_cove_tradeoff.png` | How do scenario revenue and COVE results relate? |
| `different scenarios/figures/step3_ladder_revenue_progression.png` | How do the benchmark, single forecast, and best multi-scenario case compare? |
| `different scenarios/figures/step3_scenario_scorecard.png` | What are the revenue and COVE trends in a readable 2D view? |
| `different scenarios/figures/step3_delta_vs_one_forecast.png` | How far did each multi-scenario case move relative to one forecast? |
| `different scenarios/figures/step3_runtime_by_scenario_count.png` | How quickly did computation grow with scenario count? |
| `different scenarios/figures/step3_scenario_count_sensitivity.png` | Is performance monotonic as more scenarios are added? |

## Step 4: Perfect-Information Oracle

| File | Question answered |
| --- | --- |
| `oracle upper bound/figures/step4_oracle_improvement_by_horizon.png` | How much COVE reduction is possible with perfect window information? |
| `oracle upper bound/figures/step4_oracle_cove_by_horizon.png` | Where does absolute Oracle COVE begin to plateau? |
| `oracle upper bound/figures/step4_oracle_revenue_by_horizon.png` | How does the Oracle revenue metric change by horizon? |
| `oracle upper bound/figures/step4_oracle_runtime_value_tradeoff.png` | What runtime is required for each Oracle value level? |
| `oracle upper bound/figures/step4_incremental_oracle_gain.png` | How quickly do perfect-information gains diminish? |
| `oracle upper bound/figures/step4_gap_to_168h_oracle.png` | How far is each shorter window from the 168-hour Oracle ceiling? |
| `oracle upper bound/figures/step4_oracle_scorecard.png` | What do Oracle revenue and COVE look like side by side? |
