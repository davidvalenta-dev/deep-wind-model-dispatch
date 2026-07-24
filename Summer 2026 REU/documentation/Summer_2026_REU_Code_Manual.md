# Summer 2026 REU Code Manual

Generated 2026-07-24 from the local repository at `/Users/davidvalenta/deep-wind-model-dispatch`. This manual explains every Python file under `Summer 2026 REU/`, including what it does, what it reads, what it writes, what to run, and which functions/classes matter.

## One-Sentence Project Map

The project predicts wind/power and price, sends those forecasts into a constrained Gurobi dispatch optimizer, compares against baseload, and uses oracle/scenario experiments to understand how much value comes from better information.

## Run Ladder

| Step | Folder | Command | Meaning |
| --- | --- | --- | --- |
| 0 | 100 MW baseload | cd "Summer 2026 REU/100 MW baseload" && ../../venv/bin/python RUN_0_100MW_BASELOAD.py | Builds the simple 100 MW constant-output benchmark and same-year oracle checks. This is the lower reference case for Chris: it follows a rule instead of maximizing revenue with forecasts. |
| 1 | causal ridge regression | cd "Summer 2026 REU/causal ridge regression" && ../../venv/bin/python RUN_1_FORECAST_RMSE.py | Compares forecast models and selects the causal lag/ridge-style power forecast. This is forecast-only: no battery dispatch, no Gurobi, no COVE. |
| 2 | rolling horizon | cd "Summer 2026 REU/rolling horizon" && ../../venv/bin/python RUN_2_ROLLING_HORIZON.py | Runs deterministic forecast-driven Gurobi dispatch. It uses the causal forecast, tests different lookahead horizons, executes only the first part, then rolls forward chronologically. |
| 3 | different scenarios | cd "Summer 2026 REU/different scenarios" && ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py | Runs uncertainty-aware dispatch. Instead of one predicted future, it gives Gurobi multiple possible futures and requires the first action to work across them. |
| 4 | oracle upper bound | cd "Summer 2026 REU/oracle upper bound" && ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py | Runs the perfect-future ceiling. Gurobi sees actual future wind and actual future price, so this is not deployable but shows the upper bound under the same storage constraints. |
| 5 | b6 verification | cd "Summer 2026 REU/b6 verification" and run the B6 runner/validator from code/ when Chris asks for the frozen B6 package. | Contains the separate B6 frozen 2020 validation packet requested by Chris. It reruns exactly six A/B/C oracle/causal cases and validates the hourly outputs. |

## Key Formulas

Revenue is the money score: `revenue = sum(realized_price[t] * delivered_power[t])`. COVE is the cost score: `COVE = annualized_cost / revenue`, so lower COVE is better. SoC is battery energy: `SoC[t+1] = SoC[t] + charge[t] - discharge[t] / RTE` in the dispatch code. The main constraints are wind-only charging, no grid charging, no simultaneous charge/discharge, SoC bounds, charge/discharge power limits, delivered power equals direct wind plus discharge, and delivered power cannot exceed the 249 MW grid cap.

## Every Python File At A Glance

| File | Lines | Role |
| --- | --- | --- |
| 100 MW baseload/EXPERIMENT_KNOBS.py | 33 | The one place to change the 100 MW baseload/oracle benchmark settings before rerunning Step 0. |
| 100 MW baseload/RUN_0_100MW_BASELOAD.py | 325 | Main Step 0 command. It reruns the 100 MW baseload and oracle benchmark from the knobs file, prints the summary, writes comparison CSVs, and regenerates figures. |
| 100 MW baseload/code/canonical_benchmark_oracle_runner.py | 687 | The real Step 0 computation engine. It loads complete 2020 wind and raw RTM LMP, runs the 100 MW rule-based baseload, solves oracle MILPs with Gurobi, writes hourly CSVs, summaries, QA reports, and metadata. |
| b6 verification/code/B6_CANONICAL_RUNNER.py | 767 | The full frozen B6 package runner. It runs exactly six 2020 cases: architectures A, B, C crossed with Oracle and Causal. |
| b6 verification/code/B6_FINAL_VALIDATE.py | 113 | QA validator for the B6 final package. |
| causal ridge regression/EXPERIMENT_KNOBS.py | 27 | The one place to change Step 1 forecast/RMSE settings. |
| causal ridge regression/RUN_1_FORECAST_RMSE.py | 170 | Main Step 1 command. It rebuilds the causal lag/ridge forecast, compares it to other forecast methods, prints RMSE/MAE/bias, and regenerates forecast figures. |
| causal ridge regression/code/causal_lag_forecast.py | 196 | Builds the causal lag/ridge-style power forecast used in the dispatch experiments. It predicts power from information available before prediction time. |
| causal ridge regression/code/compare_forecast_rmse.py | 130 | Compares the causal lag/ridge forecast against other saved forecast methods using the same error metrics. |
| different scenarios/EXPERIMENT_KNOBS.py | 41 | The one place to change Step 3 scenario-dispatch settings. |
| different scenarios/RUN_3_SCENARIO_COMPARISON.py | 248 | Main Step 3 command. It reruns the scenario-dispatch experiment from the knobs file, prints baseload/single/scenario comparison, and regenerates figures. |
| different scenarios/code/run_best_forecast_dispatch_search.py | 482 | Older helper for comparing forecast candidates and summarizing dispatch value. It remains in the scenario folder because scenario summaries reuse its revenue/COVE-style accounting ideas. |
| different scenarios/code/run_nora_matching_forecast_horizons.py | 775 | Copy of the Nora-style horizon helper used by scenario code. It supplies shared forecasting, Gurobi, revenue, COVE, and constraint functions. |
| different scenarios/code/run_uncertainty_aware_dispatch.py | 749 | The main uncertainty-aware dispatch engine. It builds multiple plausible wind/price futures, solves a scenario MILP, executes the first hour, and repeats. |
| oracle upper bound/EXPERIMENT_KNOBS.py | 36 | The one place to change Step 4 perfect-future oracle settings. |
| oracle upper bound/RUN_4_ORACLE_UPPER_BOUND.py | 205 | Main Step 4 command. It reruns the perfect-future oracle upper-bound backtest from the knobs file, filters oracle rows, prints results, and regenerates figures. |
| oracle upper bound/code/build_oracle_summary.py | 66 | Small post-processing helper that extracts oracle rows from a combined forecast/oracle summary table. |
| oracle upper bound/code/dataset.py | 44 | Tiny PyTorch Dataset wrappers copied from the original power-model code. They let tensors be indexed by PyTorch DataLoader. |
| oracle upper bound/code/forecast_backtest_rolling_horizons.py | 1016 | Copied deterministic/oracle backtest engine used by the oracle folder. In Step 4 it is called with --oracle-only, so it writes only perfect-future oracle rows and hourly CSVs. |
| oracle upper bound/code/model.py | 190 | Original neural-network model definitions copied into the folder so old model-loading utilities still work locally. |
| oracle upper bound/code/rolling_horizon_gurobi_dispatch.py | 496 | Copied lower-level Gurobi MILP dispatch engine used by the oracle folder. Same constraints as the rolling-horizon folder. |
| oracle upper bound/code/storage.py | 159 | Storage technology definitions: lithium-ion, CAES, hydro, lead-acid, flow battery, zinc, hydrogen, gravitational, and thermal. |
| oracle upper bound/code/util.py | 368 | Original utility module for storage lookup, COVE/revenue math, price normalization, config loading, model loading, dataset loading, and plotting losses. |
| rolling horizon/EXPERIMENT_KNOBS.py | 39 | The one place to change Step 2 deterministic rolling-horizon settings. |
| rolling horizon/RUN_2_ROLLING_HORIZON.py | 238 | Main Step 2 command. It reruns deterministic forecast-driven rolling-horizon Gurobi from the knobs file, prints the horizon table, and regenerates figures. |
| rolling horizon/code/compare_rolling_horizons.py | 318 | Post-processing helper for comparing completed rolling-horizon runs across horizons. |
| rolling horizon/code/dataset.py | 44 | Tiny PyTorch Dataset wrappers copied from the original power-model code. They let tensors be indexed by PyTorch DataLoader. |
| rolling horizon/code/forecast_backtest_rolling_horizons.py | 1016 | The main deterministic forecast-backtest engine. It trains causal forecasts on early data, rolls through the test period, sends forecast windows to Gurobi, executes only the first day, and scores against actual realized wind and price. |
| rolling horizon/code/model.py | 190 | Original neural-network model definitions copied into the folder so old model-loading utilities still work locally. |
| rolling horizon/code/nora_parameters_and_constraints.py | 99 | Human-readable Python reference for Nora/Chris storage parameters and MILP constraints. |
| rolling horizon/code/rolling_horizon_gurobi_dispatch.py | 496 | Lower-level Gurobi MILP dispatch model. This is where charge, discharge, direct wind, delivered power, binary mode, and SoC constraints are enforced. |
| rolling horizon/code/run_nora_matching_forecast_horizons.py | 771 | Older/shared helper for Nora-style forecast horizon experiments. It includes direct forecast models, Gurobi dispatch, frozen-day execution, Nora week validation, and plotting. |
| rolling horizon/code/storage.py | 159 | Storage technology definitions: lithium-ion, CAES, hydro, lead-acid, flow battery, zinc, hydrogen, gravitational, and thermal. |
| rolling horizon/code/util.py | 368 | Original utility module for storage lookup, COVE/revenue math, price normalization, config loading, model loading, dataset loading, and plotting losses. |

## 100 MW baseload

Builds the simple 100 MW constant-output benchmark and same-year oracle checks. This is the lower reference case for Chris: it follows a rule instead of maximizing revenue with forecasts.

Main command: `cd "Summer 2026 REU/100 MW baseload" && ../../venv/bin/python RUN_0_100MW_BASELOAD.py`

### 100 MW baseload/EXPERIMENT_KNOBS.py

| Question | Answer |
| --- | --- |
| Purpose | The one place to change the 100 MW baseload/oracle benchmark settings before rerunning Step 0. |
| When to run | Do not run this file directly. Edit it, then run RUN_0_100MW_BASELOAD.py. |
| Reads | No data loaded directly. It only defines paths and numeric settings. |
| Writes | No output by itself. Its values are imported by RUN_0_100MW_BASELOAD.py. |
| Line count | 33 |

Top docstring: One place to change Step 0 baseload/oracle benchmark settings. Edit this file, then run: ../../venv/bin/python RUN_0_100MW_BASELOAD.py

Code flow:

- Defines repository paths.
- Defines storage power, duration, RTE, grid cap, target output, SoC limits, horizons, and solver settings.
- The Step 0 wrapper converts these constants into command-line flags for the real runner.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| REPO_ROOT | HERE.parents[1] |
| OUTPUT_DIR | HERE / 'results' / 'current_run_from_knobs' |
| STORAGE_POWER_MW | 100.0 |
| STORAGE_DURATION_H | 10.0 |
| RTE | 0.55 |
| GRID_CAP_MW | 249.0 |
| TARGET_OUTPUT_MW | 100.0 |
| MIN_SOC_MWH | None |
| MAX_SOC_MWH | None |
| INITIAL_SOC_MWH | None |
| YEAR_END_SOC_MWH | None |
| HORIZONS | [24, 48, 168] |
| MIP_GAP | 1e-06 |
| TIME_LIMIT_SECONDS | None |

Important imports: `pathlib:Path`

### 100 MW baseload/RUN_0_100MW_BASELOAD.py

| Question | Answer |
| --- | --- |
| Purpose | Main Step 0 command. It reruns the 100 MW baseload and oracle benchmark from the knobs file, prints the summary, writes comparison CSVs, and regenerates figures. |
| When to run | ../../venv/bin/python RUN_0_100MW_BASELOAD.py |
| Reads | EXPERIMENT_KNOBS.py, canonical_benchmark_oracle_runner.py, and the CSV outputs created by that runner. |
| Writes | results/current_run_from_knobs/, comparison CSVs, and figures/step0_*.png. |
| Line count | 325 |

Top docstring: Step 0: 100-MW Constant-Output Baseload Benchmark. Run from this folder: ../../venv/bin/python RUN_0_100MW_BASELOAD.py This folder is the reference case Chris asked for. It is a rule-based wind-storage benchmark, not a Gurobi revenue optimizer: - if wind is above 100 MW, deliver 100 MW, charge with extra wind, curtail rest; - if wind is below 100 MW, deliver wind and discharge storage toward 100 MW; - keep SoC between 200 and 1000 MWh; - start at 600 MWh; - do not force final SoC back to 600 MWh. The script also compares the canonical 2020 oracle rolling-horizon cases against this 100-MW baseload because they use the same 2020 data and storage configuration.

Code flow:

- Builds a command using the knobs file.
- Runs canonical_benchmark_oracle_runner.py as a subprocess.
- Reads the summary and QA CSVs that were just produced.
- Prints baseload, oracle, and B6 comparison tables.
- Draws figures for example week, oracle vs baseload, and B6 vs baseload.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| RESULTS | Path(knobs.OUTPUT_DIR) |
| FIGURES | HERE / 'figures' |
| SUMMARY_FILE | RESULTS / 'canonical_summary.csv' |
| QA_FILE | RESULTS / 'canonical_QA_report.csv' |
| HOURLY_FILE | RESULTS / 'constant_output_baseload_100mw_2020_hourly.csv' |
| COMPARISON_FILE | RESULTS / 'oracle_vs_100mw_baseload_comparison.csv' |
| B6_SUMMARY_FILE | HERE.parent / 'b6 verification' / 'b6_final_results' / 'David_B6_run_summary.csv' |
| B6_COMPARISON_FILE | RESULTS / 'b6_2020_vs_100mw_baseload_revenue_comparison.csv' |
| RUNNER | HERE / 'code' / 'canonical_benchmark_oracle_runner.py' |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| read_rows | 60 | path | Reads a required CSV output and raises an error if it is missing. |
| pct_gain | 67 | value, base | Computes percent gain relative to a baseline. |
| pct_reduction | 71 | value, base | Computes percent reduction relative to a baseline, used for COVE improvement. |
| add_optional | 75 | cmd, flag, value | Adds a command-line flag only when the knob value is not None. |
| rerun_from_knobs | 80 | - | Builds the real command from EXPERIMENT_KNOBS.py and runs it as a subprocess. |
| main | 113 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, csv, os, subprocess, sys, tempfile, pathlib:Path, matplotlib, matplotlib.pyplot, pandas, EXPERIMENT_KNOBS`

### 100 MW baseload/code/canonical_benchmark_oracle_runner.py

| Question | Answer |
| --- | --- |
| Purpose | The real Step 0 computation engine. It loads complete 2020 wind and raw RTM LMP, runs the 100 MW rule-based baseload, solves oracle MILPs with Gurobi, writes hourly CSVs, summaries, QA reports, and metadata. |
| When to run | Usually called by RUN_0_100MW_BASELOAD.py. Can also be run directly with --horizons, --storage-power-mw, --storage-duration-h, and SoC flags. |
| Reads | data/processed/pyron_power.csv and data/raw/prices/12cfb125-8fa9-4401-8b0f-9d928544b721.csv. |
| Writes | canonical_summary.csv, canonical_QA_report.csv, hourly CSVs, experiment_registry.csv, metadata JSON, commands.txt. |
| Line count | 687 |

Top docstring: Run Chris Qin's required canonical benchmark and oracle cases. This runner implements the tightly scoped cases from David_REU_Advisor_Feedback_and_Required_Actions_v1.0.pdf: 1. 100-MW Constant-Output Baseload Benchmark. 2. H-hour Perfect-Information Oracle Rolling-Horizon MILP for 24, 48, and 168 hour planning horizons. The default configuration is the required 2020 Pyron/RTM benchmark: - 100 MW / 10 h / 1000 MWh CAES - SoC bounds 200 to 1000 MWh - initial SoC 600 MWh - year-end SoC 600 MWh for oracle cases - RTE 0.55 applied on the discharge side - 249 MW grid export cap - wind-only charging and no grid charging - raw realized RTM LMP in USD/MWh Run from the repository root after copying this file into strategy_model/optimization/: ./venv/bin/python strategy_model/optimization/canonical_benchmark_oracle_runner.py

Code flow:

- Loads and aligns 8,784 hourly 2020 wind/price rows.
- Builds StorageConfig from command-line settings.
- Runs a simple 100 MW baseload rule hour by hour.
- For each oracle horizon, solves a Gurobi MILP every hour with actual future wind and price.
- Runs QA checks for SoC recursion, grid cap, wind-only charging, no simultaneous charge/discharge, and revenue math.
- Writes full hourly outputs and summaries.

| Line | Command-line argument |
| --- | --- |
| 554 | --repo |
| 555 | --out |
| 556 | --horizons |
| 557 | --storage-power-mw |
| 558 | --storage-duration-h |
| 559 | --rte |
| 560 | --target-output-mw |
| 561 | --grid-cap-mw |
| 562 | --min-soc-mwh |
| 563 | --max-soc-mwh |
| 564 | --initial-soc-mwh |
| 565 | --year-end-soc-mwh |
| 566 | --mip-gap |
| 567 | --time-limit |

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| StorageConfig | 48 | - | Frozen dataclass containing storage, cost, grid, SoC, and target-output settings for the canonical 2020 benchmark. |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| git_value | 84 | repo | Runs a Git command and returns the result for metadata/reproducibility. |
| parse_power_file | 91 | path | Parses the Pyron power CSV into timestamps and MW generation. |
| load_2020_pyron_rtm | 104 | repo | Loads complete 2020 wind generation and raw RTM LMP and aligns them into 8,784 hourly rows. |
| compute_cove | 176 | revenue_usd, config | Computes COVE as annualized cost divided by revenue. |
| run_constant_output_baseload | 182 | df, config | Implements the 100 MW rule-based baseload hour by hour. |
| solve_oracle_window | 241 | generation, price, initial_soc, config, enforce_terminal_600, mip_gap, time_limit | Builds and solves one perfect-information Gurobi MILP window. |
| run_oracle_rolling_horizon | 308 | df, planning_horizon_hours, config, mip_gap, time_limit | Runs the oracle MILP repeatedly through the year, executing the first hour each time. |
| chronological_continuity_error | 386 | timestamps | Checks for missing or duplicate hourly timestamps. |
| qa_for_labels | 392 | labels, config, case_type | Checks the hourly labels for physical, balance, revenue, and SoC violations. |
| summarize_case | 460 | case_id, case_name, labels, config, qa, extra | Turns hourly labels and QA into one summary row. |
| write_hourly | 496 | labels, path | Writes hourly labels to CSV with clean timestamps. |
| write_registry | 502 | output_dir, summaries, repo, commit, config | Writes a reproducibility registry describing each run. |
| main | 550 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, csv, json, math, os, subprocess, sys, time, dataclasses:dataclass, pathlib:Path, gurobipy, numpy, pandas, gurobipy:GRB`

## causal ridge regression

Compares forecast models and selects the causal lag/ridge-style power forecast. This is forecast-only: no battery dispatch, no Gurobi, no COVE.

Main command: `cd "Summer 2026 REU/causal ridge regression" && ../../venv/bin/python RUN_1_FORECAST_RMSE.py`

### causal ridge regression/EXPERIMENT_KNOBS.py

| Question | Answer |
| --- | --- |
| Purpose | The one place to change Step 1 forecast/RMSE settings. |
| When to run | Do not run directly. Edit it, then run RUN_1_FORECAST_RMSE.py. |
| Reads | Defines the dataset path, ridge alpha, old comparison forecast file, and output locations. |
| Writes | No output by itself. |
| Line count | 27 |

Top docstring: One place to change Step 1 forecast/RMSE settings. Edit this file, then run: ../../venv/bin/python RUN_1_FORECAST_RMSE.py

Code flow:

- Chooses the forecast dataset.
- Chooses ridge regularization alpha.
- Chooses where causal predictions and RMSE comparison tables are written.
- Lets you skip rebuilding predictions if needed.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| REPO_ROOT | HERE.parents[1] |
| DATASET | REPO_ROOT / 'data' / 'processed' / 'dataset_14-23.csv' |
| CAUSAL_ALPHA | 1e-06 |
| PYRON_RESULTS | REPO_ROOT / 'power_model' / 'evaluation' / 'pyron_model_results.csv' |
| OUTPUT_DIR | HERE / 'results' / 'current_run_from_knobs' |
| CAUSAL_OUTPUT_DIR | OUTPUT_DIR / 'causal_lag_forecast_outputs' |
| RMSE_OUTPUT | OUTPUT_DIR / 'forecast_model_rmse_comparison.csv' |
| SKIP_REBUILD | False |

Important imports: `pathlib:Path`

### causal ridge regression/RUN_1_FORECAST_RMSE.py

| Question | Answer |
| --- | --- |
| Purpose | Main Step 1 command. It rebuilds the causal lag/ridge forecast, compares it to other forecast methods, prints RMSE/MAE/bias, and regenerates forecast figures. |
| When to run | ../../venv/bin/python RUN_1_FORECAST_RMSE.py |
| Reads | EXPERIMENT_KNOBS.py, code/compare_forecast_rmse.py, dataset_14-23.csv, and pyron_model_results.csv. |
| Writes | results/current_run_from_knobs/forecast_model_rmse_comparison.csv, causal forecast predictions, and figures/step1_*.png. |
| Line count | 170 |

Top docstring: Step 1 of the Summer 2026 REU ladder: compare forecast RMSE. Run from this folder: ../../venv/bin/python RUN_1_FORECAST_RMSE.py This script does not run Gurobi. It only checks which forecasting method best predicts generated power. COVE starts in the dispatch steps after forecasts are fed into Gurobi.

Code flow:

- Builds the comparison command from EXPERIMENT_KNOBS.py.
- Runs compare_forecast_rmse.py.
- Sorts forecast methods by RMSE.
- Prints the ranking.
- Plots RMSE comparison, RMSE/MAE tradeoff, example forecast week, and error distribution.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| RESULTS | HERE / 'results' |
| FIGURES | HERE / 'figures' |
| RMSE_FILE | Path(knobs.RMSE_OUTPUT) |
| COMPARE_SCRIPT | HERE / 'code' / 'compare_forecast_rmse.py' |
| PREDICTIONS_FILE | Path(knobs.CAUSAL_OUTPUT_DIR) / 'causal_lag_forecast_predictions.csv' |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| load_rows | 42 | path | Reads a CSV file into a list of dictionaries so the wrapper can print and plot results. |
| rebuild_rmse_table | 49 | - | Helper function used by this script. |
| main | 71 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, csv, os, subprocess, sys, tempfile, pathlib:Path, matplotlib, matplotlib.pyplot, pandas, EXPERIMENT_KNOBS`

### causal ridge regression/code/causal_lag_forecast.py

| Question | Answer |
| --- | --- |
| Purpose | Builds the causal lag/ridge-style power forecast used in the dispatch experiments. It predicts power from information available before prediction time. |
| When to run | Usually called by compare_forecast_rmse.py. Can be run directly with --dataset, --alpha, and --output-dir. |
| Reads | data/processed/dataset_14-23.csv with datetime, wind speed, and power generated. |
| Writes | causal_lag_forecast_predictions.csv and causal_lag_forecast_metrics.csv. |
| Line count | 196 |

Top docstring: Forecast-only causal lag/ridge model for Step 1 of the REU ladder. This script does not run Gurobi and does not compute dispatch, revenue, or COVE. It rebuilds the power forecast used before the dispatch steps.

Code flow:

- Splits data chronologically into train/validation/test.
- Builds features from lagged power, lagged speed, squared/cubed speed, and calendar signals.
- Fits a ridge regression model.
- Builds a simple speed-to-power curve baseline.
- Writes predictions and metrics.

| Constant / knob | Value or expression |
| --- | --- |
| FEATURE_NAMES | ['bias', 'speed', 'speed_sq', 'speed_cu', 'lag_power_1h', 'lag_power_2h', 'lag_power_3h', 'lag_power_24h', 'hour_sin', ' |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| DEFAULT_DATASET | REPO_ROOT / 'data' / 'processed' / 'dataset_14-23.csv' |
| DEFAULT_OUTPUT | Path(__file__).resolve().parents[1] / 'results' / 'causal_lag_forecast_outputs' |

| Line | Command-line argument |
| --- | --- |
| 144 | --dataset |
| 149 | --alpha |
| 150 | --output-dir |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| rmse | 39 | y_true, y_pred | Computes root mean squared error. |
| mae | 43 | y_true, y_pred | Computes mean absolute error. |
| chronological_slices | 47 | n, train_frac, val_frac | Builds chronological train/validation/test splits. |
| build_causal_features | 57 | df, max_lag | Builds the feature table for the causal ridge forecast. |
| fit_ridge | 106 | X, y, alpha | Fits ridge regression by solving the regularized least-squares equations. |
| fit_speed_power_curve | 112 | X, y | Fits a simple binned speed-to-power curve baseline. |
| predict_speed_power_curve | 117 | coef, X | Predicts power from the speed-to-power curve baseline. |
| evaluate_predictions | 122 | name, y, pred, slices, power_scale | Computes RMSE, MAE, and bias for a set of predictions. |
| main | 140 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `argparse, pathlib:Path, numpy, pandas`

### causal ridge regression/code/compare_forecast_rmse.py

| Question | Answer |
| --- | --- |
| Purpose | Compares the causal lag/ridge forecast against other saved forecast methods using the same error metrics. |
| When to run | Usually called by RUN_1_FORECAST_RMSE.py. Can be run directly with --causal-output-dir, --dataset, --causal-alpha, --pyron-results, and --output. |
| Reads | Causal prediction CSV and power_model/evaluation/pyron_model_results.csv. |
| Writes | forecast_model_rmse_comparison.csv. |
| Line count | 130 |

Top docstring: Recompute the Step 1 forecast RMSE comparison table. This is the script behind the forecast-method comparison. It rebuilds the causal lag/ridge prediction, then compares it with the saved prediction outputs from the earlier power-model work.

Code flow:

- Optionally rebuilds causal predictions.
- Reads actual power and predictions.
- Computes RMSE, MAE, and bias for each method.
- Writes one comparison table.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parents[1] |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| DEFAULT_CAUSAL_OUTPUT | HERE / 'results' / 'causal_lag_forecast_outputs' |
| DEFAULT_PYRON_RESULTS | REPO_ROOT / 'power_model' / 'evaluation' / 'pyron_model_results.csv' |
| DEFAULT_OUTPUT | HERE / 'results' / 'forecast_model_rmse_comparison.csv' |

| Line | Command-line argument |
| --- | --- |
| 67 | --causal-output-dir |
| 68 | --dataset |
| 69 | --causal-alpha |
| 70 | --pyron-results |
| 71 | --output |
| 72 | --skip-rebuild |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| error_row | 27 | source, model, datetimes, actual, predicted | Creates one forecast-comparison row with RMSE, MAE, and bias. |
| build_causal_predictions | 47 | output_dir, dataset, alpha | Runs causal_lag_forecast.py and returns the prediction CSV path. |
| main | 65 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, subprocess, sys, pathlib:Path, numpy, pandas`

## rolling horizon

Runs deterministic forecast-driven Gurobi dispatch. It uses the causal forecast, tests different lookahead horizons, executes only the first part, then rolls forward chronologically.

Main command: `cd "Summer 2026 REU/rolling horizon" && ../../venv/bin/python RUN_2_ROLLING_HORIZON.py`

### rolling horizon/EXPERIMENT_KNOBS.py

| Question | Answer |
| --- | --- |
| Purpose | The one place to change Step 2 deterministic rolling-horizon settings. |
| When to run | Do not run directly. Edit it, then run RUN_2_ROLLING_HORIZON.py. |
| Reads | Defines data path, model config path, train/test dates, storage size, SoC fractions, horizons, direct reserve, and solver gap. |
| Writes | No output by itself. |
| Line count | 39 |

Top docstring: One place to change Step 2 rolling-horizon dispatch settings. Edit this file, then run: ../../venv/bin/python RUN_2_ROLLING_HORIZON.py

Code flow:

- Sets the common 100 MW / 10 h storage system.
- Sets the horizon list such as 24, 48, 72, 168, or a custom 35.
- Sets DIRECT_RESERVE_MW for realistic forecast underprediction handling.
- Chooses output folder for fresh reruns.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| REPO_ROOT | HERE.parents[1] |
| OUTPUT_DIR | HERE / 'results' / 'current_run_from_knobs' |
| DATA | REPO_ROOT / 'data' / 'processed' / 'dataset_1980-2023_withloads_fix.csv' |
| CONFIG | REPO_ROOT / 'strategy_model' / 'test' / 'run_016' / 'config_run_016.yaml' |
| TRAIN_END | '2014-01-01' |
| TEST_END | None |
| ALPHA | 10.0 |
| TRAIN_ORIGIN_STRIDE | 24 |
| STORAGE_POWER_MW | 100.0 |
| STORAGE_DURATION_H | 10.0 |
| GRID_CAP_MW | 249.0 |
| MIN_SOC_FRAC | 0.2 |
| MAX_SOC_FRAC | 1.0 |
| INITIAL_SOC_MWH | None |
| HORIZONS | [24, 48, 72, 168] |
| DIRECT_RESERVE_MW | 75.0 |
| MIP_GAP | 0.0 |
| RUN_ORACLE_CONTEXT | True |

Important imports: `pathlib:Path`

### rolling horizon/RUN_2_ROLLING_HORIZON.py

| Question | Answer |
| --- | --- |
| Purpose | Main Step 2 command. It reruns deterministic forecast-driven rolling-horizon Gurobi from the knobs file, prints the horizon table, and regenerates figures. |
| When to run | ../../venv/bin/python RUN_2_ROLLING_HORIZON.py |
| Reads | EXPERIMENT_KNOBS.py and code/forecast_backtest_rolling_horizons.py. |
| Writes | results/current_run_from_knobs/forecast_dispatch_summary.csv, forecast_dispatch_*h.csv hourly outputs, and figures/step2_*.png. |
| Line count | 238 |

Top docstring: Step 2 of the Summer 2026 REU ladder: causal forecast rolling horizon. Run from this folder: ../../venv/bin/python RUN_2_ROLLING_HORIZON.py This reruns the causal ridge + direct-reserve Gurobi result using the settings in EXPERIMENT_KNOBS.py. Gurobi gets a forecast window, executes only the first 24 hours, carries the battery state forward, and repeats.

Code flow:

- Builds a command from EXPERIMENT_KNOBS.py.
- Runs the Gurobi backtest.
- Filters causal_forecast_direct_reserve rows.
- Prints each horizon and picks the best COVE improvement.
- Plots COVE gain, COVE level, revenue, runtime, and a 3D horizon tradeoff.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| RESULTS | Path(knobs.OUTPUT_DIR) |
| FIGURES | HERE / 'figures' |
| SUMMARY_FILE | RESULTS / 'forecast_dispatch_summary.csv' |
| RUNNER | HERE / 'code' / 'forecast_backtest_rolling_horizons.py' |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| load_rows | 41 | path | Reads a CSV file into a list of dictionaries so the wrapper can print and plot results. |
| fmt_money | 48 | value | Formats numeric revenue values with commas and two decimals. |
| add_optional | 52 | cmd, flag, value | Adds a command-line flag only when the knob value is not None. |
| rerun_from_knobs | 57 | - | Builds the real command from EXPERIMENT_KNOBS.py and runs it as a subprocess. |
| main | 99 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, csv, os, subprocess, sys, tempfile, pathlib:Path, matplotlib, matplotlib.pyplot, mpl_toolkits.mplot3d:Axes3D, EXPERIMENT_KNOBS`

### rolling horizon/code/compare_rolling_horizons.py

| Question | Answer |
| --- | --- |
| Purpose | Post-processing helper for comparing completed rolling-horizon runs across horizons. |
| When to run | Run after full horizon outputs already exist. |
| Reads | Completed horizon result folders. |
| Writes | Comparison CSVs and performance/example-week figures. |
| Line count | 318 |

Top docstring: Compare rolling-horizon Gurobi dispatch results across look-ahead windows. This script expects completed runs from rolling_horizon_gurobi_dispatch.py. It keeps the storage design and constraints fixed, then compares only the planning horizon.

Code flow:

- Loads each horizon summary.
- Computes max constraint violation.
- Plots COVE/revenue/runtime comparisons.
- Loads an example week for visual dispatch comparison.

| Constant / knob | Value or expression |
| --- | --- |
| DEFAULT_HORIZONS | {24: 'horizon_24h', 48: 'horizon_48h', 72: 'horizon_72h'} |

| Line | Command-line argument |
| --- | --- |
| 223 | --base-dir |
| 231 | --weekly-dir |
| 239 | --example-start |
| 240 | --example-end |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| max_constraint_violation | 28 | row | Helper function used by this script. |
| load_summary | 37 | result_dir, horizon | Helper function used by this script. |
| style_axis | 56 | axis | Applies consistent plotting style. |
| save_performance_figures | 63 | comparison, output_dir | Helper function used by this script. |
| load_example_week | 149 | labels_path, start, end, horizon | Helper function used by this script. |
| save_example_week_figures | 168 | example, output_dir | Helper function used by this script. |
| main | 221 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, pathlib:Path, matplotlib, matplotlib.pyplot, numpy, pandas`

### rolling horizon/code/dataset.py

| Question | Answer |
| --- | --- |
| Purpose | Tiny PyTorch Dataset wrappers copied from the original power-model code. They let tensors be indexed by PyTorch DataLoader. |
| When to run | Not run directly. |
| Reads | In-memory tensors/arrays. |
| Writes | Dataset objects used by model/data-loading utilities. |
| Line count | 44 |

Code flow:

- VF2Dataset returns two-input examples.
- VFDataset returns regular feature/target examples.
- These are support classes for old neural-network utilities, not the main Gurobi result.

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| VF2Dataset | 4 | Dataset | PyTorch Dataset wrapper returning examples with two feature inputs. |
| VFDataset | 27 | Dataset | PyTorch Dataset wrapper returning feature/target examples. |

Important imports: `torch.utils.data:Dataset`

### rolling horizon/code/forecast_backtest_rolling_horizons.py

| Question | Answer |
| --- | --- |
| Purpose | The main deterministic forecast-backtest engine. It trains causal forecasts on early data, rolls through the test period, sends forecast windows to Gurobi, executes only the first day, and scores against actual realized wind and price. |
| When to run | Usually called by RUN_2_ROLLING_HORIZON.py or RUN_4_ORACLE_UPPER_BOUND.py. Direct flags control data, config, train/test split, storage, horizons, direct reserve, and oracle-only mode. |
| Reads | data/processed/dataset_1980-2023_withloads_fix.csv, strategy_model/test/run_016/config_run_016.yaml, and helper modules. |
| Writes | forecast_dispatch_summary.csv, forecast_accuracy_by_lead.csv, forecast_dispatch_*h.csv, oracle_dispatch_*h.csv, figures, and metadata. |
| Line count | 1016 |

Top docstring: Backtest rolling-horizon Gurobi dispatch with causal forecasts. The forecasting models are trained on an early chronological period and frozen. During the later backtest, every daily forecast uses only values observed before that forecast was issued. Gurobi plans from forecast wind generation and price, but only the first 24 hours are executed and scored against actual outcomes.

Code flow:

- Builds lag/calendar features for generation and price forecasts.
- Creates forecast matrices for every rolling origin.
- Optionally creates actual-future matrices for oracle runs.
- Calls solve_window() from rolling_horizon_gurobi_dispatch.py.
- Executes planned actions against actual wind/price with recourse.
- Applies direct reserve to avoid blindly curtailing forecast underprediction.
- Checks realized constraints and summarizes revenue/COVE.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| SUMMER_STEP_DIR | Path(__file__).resolve().parents[1] |
| STRATEGY_SRC | REPO_ROOT / 'strategy_model' / 'src' |
| OPTIMIZATION_DIR | REPO_ROOT / 'strategy_model' / 'optimization' |
| PAST_LAGS | (1, 2, 3, 6, 12, 24, 48, 168) |
| DEFAULT_HORIZONS | (24, 48, 72, 168) |

| Line | Command-line argument |
| --- | --- |
| 713 | --data |
| 722 | --config |
| 732 | --train-end |
| 733 | --test-end |
| 734 | --alpha |
| 735 | --train-origin-stride |
| 736 | --price-signal |
| 742 | --mip-gap |
| 743 | --storage-power-mw |
| 744 | --storage-duration-h |
| 745 | --grid-cap-mw |
| 746 | --initial-soc |
| 752 | --min-soc-frac |
| 753 | --max-soc-frac |
| 754 | --direct-reserve-mw |
| 764 | --horizons |
| 771 | --oracle-only |
| 776 | --skip-oracle |
| 777 | --out-dir |

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| DirectForecastModel | 51 | - | Small container for direct multi-step forecast model coefficients and normalization statistics. |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| calendar_features | 64 | timestamps | Creates hour/day/month cyclical features. |
| origin_features | 81 | values, origins | Builds forecast features for many rolling origins. |
| single_origin_features | 96 | values, origin | Builds forecast features for one origin and one future lead. |
| fit_direct_models | 112 | values, datetimes, train_end, max_horizon, target_min, target_max, alpha, origin_stride, known_future_values | Fits direct multi-step forecast models for wind generation and price. |
| make_forecast_matrix | 166 | values, datetimes, origins, models, known_future_values | Creates a matrix of forecasts, one row per origin and one column per lead hour. |
| make_known_future_matrix | 191 | values, origins, max_horizon | Creates an oracle matrix using actual future values instead of forecasts. |
| forecast_metrics | 202 | actual, origins, forecasts, name | Calculates forecast error by lead-time block. |
| execute_plan_against_actual | 235 | planned, actual_generation, initial_soc, config, min_soc_frac, max_soc_frac | Converts a forecast plan into realized feasible operation using actual wind and price. |
| check_realized_constraints | 299 | labels, config, min_soc_frac, max_soc_frac | Checks realized hourly dispatch for constraint violations. |
| apply_direct_reserve | 355 | solution, config, direct_reserve_mw | Adds planned direct-wind reserve for causal forecast execution. |
| run_horizon | 382 | df, test_start, origins, generation_forecasts, price_forecasts, horizon, config, initial_soc, min_soc_frac, max_soc_frac, mip_gap, perfect_information, direct_reserve_mw | Runs one horizon length through the rolling-horizon backtest. |
| style_axis | 525 | axis | Applies consistent plotting style. |
| save_figures | 532 | summary, metrics, labels_by_horizon, output_dir, horizons | Writes summary figures to disk. |
| main | 709 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, json, math, os, sys, time, dataclasses:dataclass, pathlib:Path, matplotlib, matplotlib.pyplot, numpy, pandas, util, rolling_horizon_gurobi_dispatch:continuous_baseload,cove_value,fixed_costs,solve_window`

### rolling horizon/code/model.py

| Question | Answer |
| --- | --- |
| Purpose | Original neural-network model definitions copied into the folder so old model-loading utilities still work locally. |
| When to run | Not run directly. |
| Reads | PyTorch tensors. |
| Writes | Predicted model outputs from neural-network forward passes. |
| Line count | 190 |

Code flow:

- VFNN_2 and VFNN define feed-forward neural networks.
- PLinear defines a positive/parameterized linear layer style helper.
- These files support original NQF/power-model utilities but are not the main Summer ladder command.

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| VFNN_2 | 8 | nn.Module | Original feed-forward neural network that accepts two input branches. |
| VFNN | 109 | nn.Module | Original feed-forward neural network for value/power forecasting. |
| PLinear | 176 | nn.Module | Original custom linear layer helper used by neural-network code. |

Important imports: `torch, torch.nn, torch.nn.functional, util, numpy`

### rolling horizon/code/nora_parameters_and_constraints.py

| Question | Answer |
| --- | --- |
| Purpose | Human-readable Python reference for Nora/Chris storage parameters and MILP constraints. |
| When to run | Can be run to print the constraint checklist. |
| Reads | No data files. |
| Writes | Printed parameter/constraint summary. |
| Line count | 99 |

Top docstring: Reviewer-facing summary of the storage parameters and MILP constraints. This file does not replace the optimizer. The active Gurobi implementation is `rolling_horizon_gurobi_dispatch.py`. This file is the quick place to show Chris/reviewers exactly what physical rules the dispatch model is supposed to follow.

Code flow:

- Defines the canonical 100 MW / 10 h CAES case.
- Defines B6 architectures.
- Lists each operational constraint in plain wording.
- Prints a concise summary for meetings/reviewers.

| Constant / knob | Value or expression |
| --- | --- |
| NORA_CAES_100MW_10H | StorageCase(name='Nora matching CAES case', storage_power_mw=100.0, duration_hours=10.0, round_trip_efficiency=0.55, dep |
| B6_ARCHITECTURES | {'A': {'energy_capacity_mwh': 600.0, 'soc_20pct_mwh': 120.0}, 'B': {'energy_capacity_mwh': 600.0, 'soc_20pct_mwh': 120.0 |
| CONSTRAINTS | ['State of charge is bounded: Cmin <= SoC(t) <= Cmax.', 'Charging power is bounded by the storage power rating.', 'Disch |

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| StorageCase | 15 | - | Simple dataclass for printing storage cases and constraints in the Nora parameters file. |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| print_summary | 69 | - | Prints the Nora/Chris parameter and constraint checklist. |

Important imports: `__future__:annotations, dataclasses:dataclass`

### rolling horizon/code/rolling_horizon_gurobi_dispatch.py

| Question | Answer |
| --- | --- |
| Purpose | Lower-level Gurobi MILP dispatch model. This is where charge, discharge, direct wind, delivered power, binary mode, and SoC constraints are enforced. |
| When to run | Used as a helper by forecast_backtest_rolling_horizons.py, but can also be run directly for rolling-horizon optimization. |
| Reads | Forecast or actual generation/price arrays plus storage config. |
| Writes | Hourly labels, summary metrics, constraint checks, and optional progress files. |
| Line count | 496 |

Top docstring: Rolling-horizon Gurobi dispatch with Nora's MILP constraints. This experiment uses Gurobi as the mixed-integer teacher for COVE-DV. Summary: - At each time step, Gurobi looks ahead a fixed number of hours. - It chooses charge, discharge, hold, direct-to-grid, delivered power, and storage. - Only the first part of that plan is executed. - Then the battery state carries forward chronologically and the window rolls. The default model includes Nora's operational constraints: - storage capacity limits, - charging/discharging power limits, - one binary charge/discharge mode per hour, - available-energy discharge limit, - wind-only charging, - delivered power definition, - grid export limit, - storage state update, - end-of-horizon SoC_initial = SoC_final.

Code flow:

- Defines the MILP variables P_dir, P_ch, P_dis, P_delivered, SoC, and charge/discharge mode.
- Adds wind-only charging, grid cap, no simultaneous charge/discharge, and SoC update constraints.
- Maximizes price times delivered power.
- Runs windows chronologically and carries SoC forward.
- Summarizes revenue, COVE, curtailment, runtime, and violations.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| STRATEGY_SRC | REPO_ROOT / 'strategy_model' / 'src' |

| Line | Command-line argument |
| --- | --- |
| 415 | --data |
| 416 | --config |
| 417 | --out-dir |
| 418 | --hours |
| 419 | --offset |
| 420 | --horizon-hours |
| 421 | --step-hours |
| 422 | --terminal-policy |
| 423 | --initial-soc |
| 424 | --min-soc-frac |
| 425 | --max-soc-frac |
| 426 | --mip-gap |
| 427 | --time-limit |
| 428 | --max-windows |
| 429 | --progress-every |
| 430 | --storage-type |
| 431 | --storage-rating |
| 432 | --storage-duration |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| load_data | 44 | data_path, config, offset, hours | Loads generation and price data for rolling-horizon dispatch. |
| cove_value | 52 | power, price, config | Computes COVE value for a given revenue and storage setup. |
| continuous_baseload | 66 | power, config, initial_soc | Computes the baseload reference for comparison. |
| fixed_costs | 90 | config | Computes annualized wind/storage cost used in COVE. |
| solve_window | 101 | generation, price, config, initial_soc, terminal_policy, min_soc_frac, max_soc_frac, mip_gap, time_limit | Builds and solves one Gurobi MILP dispatch window. |
| check_constraints | 193 | labels, config, min_soc_frac, max_soc_frac | Checks Gurobi output for constraint violations. |
| write_progress | 223 | path, rows | Writes progress checkpoints during long rolling runs. |
| run_rolling | 234 | df, config, horizon_hours, step_hours, terminal_policy, initial_soc, min_soc_frac, max_soc_frac, mip_gap, time_limit, max_windows, progress_every, checkpoint_path | Runs the low-level rolling-horizon loop across many windows. |
| add_compatibility_columns | 340 | labels, config | Adds older column names so old analysis scripts still work. |
| summarize | 362 | labels, window_rows, config, args | Creates summary metrics from hourly dispatch labels. |
| main | 413 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, csv, json, math, sys, time, pathlib:Path, numpy, pandas, util`

### rolling horizon/code/run_nora_matching_forecast_horizons.py

| Question | Answer |
| --- | --- |
| Purpose | Older/shared helper for Nora-style forecast horizon experiments. It includes direct forecast models, Gurobi dispatch, frozen-day execution, Nora week validation, and plotting. |
| When to run | Mainly used as support code and historical comparison. Scenario code imports pieces from it. |
| Reads | Processed Pyron dataset and Nora January week data when validating the matching case. |
| Writes | Forecast horizon summaries, figures, labels, and Nora validation outputs when run directly. |
| Line count | 771 |

Code flow:

- Trains direct forecasts.
- Builds weekly generation and price forecasts.
- Solves Nora-compatible Gurobi windows.
- Executes frozen day actions against realized values.
- Computes revenue/COVE and constraint checks.
- Builds comparison figures.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| OUT | Path(__file__).resolve().parent / 'nora_matching_forecast_horizon_results' |
| DATA_PATH | REPO_ROOT / 'data' / 'processed' / 'dataset_1980-2023_withloads_fix.csv' |
| NORA_PATH | Path(os.environ.get('NORA_WEEK_XLSX', '/Users/davidvalenta/Downloads/january6-12.xlsx')) |
| HORIZONS | [24, 48, 72, 168] |
| STEP_HOURS | 24 |
| PAST_LAGS | (1, 2, 3, 6, 12, 24, 48, 168) |
| PS | 100.0 |
| DURATION_HOURS | 10.0 |
| RTE | 0.55 |
| SQRT_RTE | math.sqrt(RTE) |
| CMAX | PS * DURATION_HOURS |
| DOD | 0.8 |
| CMIN | CMAX * (1.0 - DOD) |
| SOC0 | (CMIN + CMAX) / 2.0 |
| GRID_CAP | 249.0 |
| FCR | 0.065 |
| WF_CAPEX | 1968.0 |
| WF_OPEX | 43.0 |
| CAES_CAPEX | 2044.0 |
| CAES_OPEX | 28.1 |

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| DirectForecastModel | 50 | - | Small container for direct multi-step forecast model coefficients and normalization statistics. |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| calendar_features | 63 | timestamps | Creates hour/day/month cyclical features. |
| origin_features | 80 | values, origins | Builds forecast features for many rolling origins. |
| single_origin_features | 95 | values, origin | Builds forecast features for one origin and one future lead. |
| fit_direct_models | 110 | values, datetimes, train_end, max_horizon, target_min, target_max, alpha, origin_stride | Fits direct multi-step forecast models for wind generation and price. |
| make_generation_forecasts | 151 | values, datetimes, origins, models | Helper function used by this script. |
| make_weekly_price_forecasts | 171 | prices, origins, max_horizon | Helper function used by this script. |
| forecast_metrics | 180 | actual, origins, forecasts, variable | Calculates forecast error by lead-time block. |
| solve_window_nora | 206 | forecast_generation, forecast_price, start_soc, horizon | Optimize one forecast window with the Nora-matching Gurobi equations. |
| execute_frozen_day | 257 | planned, actual_generation, start_soc, execute_len | Helper function used by this script. |
| run_forecast_horizon | 313 | df, origins, generation_forecasts, price_forecasts, horizon | Helper function used by this script. |
| revenue | 392 | power, price | Computes revenue from price and delivered/generated power. |
| annualized_dispatch_cost | 396 | - | Helper function used by this script. |
| continuous_baseload | 402 | generation | Computes the baseload reference for comparison. |
| check_realized_constraints | 422 | labels | Checks realized hourly dispatch for constraint violations. |
| summarize | 444 | labels_by_horizon | Creates summary metrics from hourly dispatch labels. |
| validate_nora_week | 483 | - | Helper function used by this script. |
| make_figures | 501 | summary, metrics, labels_by_horizon | Creates the script-specific figures. |
| main | 646 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, json, math, os, time, dataclasses:dataclass, pathlib:Path, gurobipy, matplotlib, matplotlib.pyplot, numpy, pandas, gurobipy:GRB`

### rolling horizon/code/storage.py

| Question | Answer |
| --- | --- |
| Purpose | Storage technology definitions: lithium-ion, CAES, hydro, lead-acid, flow battery, zinc, hydrogen, gravitational, and thermal. |
| When to run | Not run directly. |
| Reads | No data files. |
| Writes | Storage objects with capital cost, operating cost, duration, and efficiency values. |
| Line count | 159 |

Code flow:

- Base Storage stores cost/performance fields.
- Each child class fills in values for one storage technology.
- Util functions use these classes for RTE, cost, and COVE calculations.

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| Storage | 4 | - | Base storage technology object containing efficiency/cost/duration fields. |
| BatteryLI | 26 | Storage | Lithium-ion storage parameter class. |
| CAES | 45 | Storage | Compressed-air energy storage parameter class. |
| Hydro | 58 | Storage | Hydropower/pumped-storage style parameter class. |
| BatteryLA | 71 | Storage | Lead-acid battery parameter class. |
| BatteryVRF | 90 | Storage | Vanadium redox flow battery parameter class. |
| Zinc | 109 | Storage | Zinc storage parameter class. |
| Hydrogen | 122 | Storage | Hydrogen storage parameter class. |
| Gravitational | 135 | Storage | Gravitational storage parameter class. |
| Thermal | 148 | Storage | Thermal storage parameter class. |

Important imports: `numpy`

### rolling horizon/code/util.py

| Question | Answer |
| --- | --- |
| Purpose | Original utility module for storage lookup, COVE/revenue math, price normalization, config loading, model loading, dataset loading, and plotting losses. |
| When to run | Not run directly. |
| Reads | Config YAML, CSV data, PyTorch model checkpoints, and storage names. |
| Writes | Loaded models/datasets, normalized prices, revenue/COVE calculations, and plots. |
| Line count | 368 |

Code flow:

- Maps storage names to storage objects.
- Computes revenue, value factor, and COVE.
- Normalizes price columns.
- Loads YAML configs and saved PyTorch models.
- Builds train/validation/test datasets.

| Constant / knob | Value or expression |
| --- | --- |
| STORAGE_TYPES | np.array(['battery-li', 'caes', 'hydro', 'battery-la', 'battery-vrf', 'hydrogen', 'zinc', 'grav', 'thermal']) |
| STORAGE_OBJECTS | np.array([BatteryLI(), CAES(), Hydro(), BatteryLA(), BatteryVRF(), Hydrogen(), Zinc(), Gravitational(), Thermal()]) |
| FCR | 0.065 |
| WF_CAPEX | 1968 |
| WF_OPEX | 43 |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| get_storage_object | 19 | type | Returns the storage object for a storage name. |
| get_rte | 23 | type, rating, duration | Returns storage round-trip efficiency. |
| get_storage_specs | 27 | type, rating, duration | Returns storage cost/performance parameters. |
| cove | 37 | power, price, storage_type, storage_rating, storage_duration, wf_rating, num_modules | Computes cost of valued energy in the older utility style. |
| revenue | 48 | power, price, range | Computes revenue from price and delivered/generated power. |
| value_factor | 56 | power, price | Computes the value factor of generation relative to price. |
| batchwise_revenue | 61 | batch_power, batch_price | Computes revenue over batches/tensors. |
| batchwise_value_factor | 65 | batch_power, batch_price | Computes value factor over batches/tensors. |
| batchwise_cove | 71 | batch_power, batch_price, epsilon, storage_type, storage_rating, storage_duration, wf_rating, num_modules | Computes COVE over batches/tensors. |
| normalize_price | 89 | prices, config | Normalizes price data for model training. |
| load_config | 101 | file_path | Loads YAML experiment configuration. |
| save_config | 106 | config, file_path | Writes YAML experiment configuration. |
| load_model | 110 | model_path, config_path, with_loads | Loads a saved PyTorch model. |
| load_model_with_loads | 118 | model_path, config_path | Loads a saved PyTorch model that includes load features. |
| load_dataset_no_split | 131 | csv_path, config, with_loads, cf | Loads a dataset without train/test splitting. |
| load_dataset_split_as_tensors | 150 | csv_path, config | Loads dataset splits as tensors. |
| load_dataset_no_split_with_loads | 194 | csv_path, config, cf | Loads dataset with load features and no split. |
| load_dataset | 214 | csv_path, config, with_loads, no_shuffle, cf | Loads train/validation/test datasets. |
| load_dataset_with_loads | 274 | csv_path, config | Loads datasets that include load features. |
| load_experiment | 331 | folder_name, dataset_path, with_loads, cf, no_split, no_shuffle | Loads a saved experiment folder. |
| plot_losses | 343 | train_losses, val_losses, fname | Plots training and validation losses. |
| format_num | 362 | num | Formats numbers for display. |

Important imports: `numpy, yaml, matplotlib.pyplot, torch, os, model:VFNN,VFNN_2, pandas, dataset:VFDataset,VF2Dataset, torch.utils.data:Dataset,DataLoader, storage:*`

## different scenarios

Runs uncertainty-aware dispatch. Instead of one predicted future, it gives Gurobi multiple possible futures and requires the first action to work across them.

Main command: `cd "Summer 2026 REU/different scenarios" && ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py`

### different scenarios/EXPERIMENT_KNOBS.py

| Question | Answer |
| --- | --- |
| Purpose | The one place to change Step 3 scenario-dispatch settings. |
| When to run | Do not run directly. Edit it, then run RUN_3_SCENARIO_COMPARISON.py. |
| Reads | Defines scenario variants, horizon, storage, RTE, DoD, grid cap, calibration mode, and quick-run limit. |
| Writes | No output by itself. |
| Line count | 41 |

Top docstring: One place to change Step 3 scenario-dispatch settings. Edit this file, then run: ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py

Code flow:

- Sets 48-hour scenario lookahead by default.
- Selects 1/3/5/7/10 scenario variants.
- Lets you use MAX_ORIGINS for a quick partial test or None for full run.
- Chooses output folder for fresh reruns.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| OUTPUT_DIR | HERE / 'results' / 'current_run_from_knobs' |
| HORIZON_HOURS | 48 |
| VARIANTS | ['single_recourse', 'three_scenario_expected', 'five_scenario_expected', 'seven_scenario_expected', 'ten_scenario_expect |
| STORAGE_POWER_MW | 100.0 |
| STORAGE_DURATION_H | 10.0 |
| RTE | 0.55 |
| DOD | 0.8 |
| GRID_CAP_MW | 249.0 |
| INITIAL_SOC_MWH | None |
| NOWCAST_FIRST_HOUR | True |
| GATE_MARGIN | 0.0 |
| CALIBRATION_MODE | 'in_sample_residual' |
| FORECAST_TRAIN_END | '2013-01-01' |
| CALIBRATION_END | '2014-01-01' |
| MAX_ORIGINS | None |

Important imports: `pathlib:Path`

### different scenarios/RUN_3_SCENARIO_COMPARISON.py

| Question | Answer |
| --- | --- |
| Purpose | Main Step 3 command. It reruns the scenario-dispatch experiment from the knobs file, prints baseload/single/scenario comparison, and regenerates figures. |
| When to run | ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py |
| Reads | EXPERIMENT_KNOBS.py and code/run_uncertainty_aware_dispatch.py. |
| Writes | results/current_run_from_knobs/uncertainty_aware_summary.csv, scenario label CSVs, and figures/step3_*.png. |
| Line count | 248 |

Top docstring: Step 3 of the Summer 2026 REU ladder: uncertainty-aware scenarios. Run from this folder: ../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py This reruns baseload, single-forecast dispatch, and multi-scenario dispatch using the settings in EXPERIMENT_KNOBS.py.

Code flow:

- Builds the scenario command from EXPERIMENT_KNOBS.py.
- Runs the scenario Gurobi experiment.
- Reads uncertainty_aware_summary.csv.
- Prints revenue/COVE gains versus baseload.
- Creates COVE, revenue, tradeoff, ladder, and 3D scenario figures.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| RESULTS | Path(knobs.OUTPUT_DIR) |
| FIGURES | HERE / 'figures' |
| SUMMARY_FILE | RESULTS / 'uncertainty_aware_summary.csv' |
| RUNNER | HERE / 'code' / 'run_uncertainty_aware_dispatch.py' |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| load_rows | 40 | path | Reads a CSV file into a list of dictionaries so the wrapper can print and plot results. |
| short_name | 47 | candidate | Converts long scenario candidate names into readable labels for tables and plots. |
| money | 58 | value | Formats numeric revenue values as dollars. |
| add_optional | 62 | cmd, flag, value | Adds a command-line flag only when the knob value is not None. |
| rerun_from_knobs | 67 | - | Builds the real command from EXPERIMENT_KNOBS.py and runs it as a subprocess. |
| main | 107 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, csv, os, subprocess, sys, tempfile, pathlib:Path, matplotlib, matplotlib.pyplot, mpl_toolkits.mplot3d:Axes3D, EXPERIMENT_KNOBS`

### different scenarios/code/run_best_forecast_dispatch_search.py

| Question | Answer |
| --- | --- |
| Purpose | Older helper for comparing forecast candidates and summarizing dispatch value. It remains in the scenario folder because scenario summaries reuse its revenue/COVE-style accounting ideas. |
| When to run | Historical/support script; not the main Step 3 command. |
| Reads | Forecast candidates, actual future matrices, and completed dispatch outputs. |
| Writes | Candidate summaries and figures when run directly. |
| Line count | 482 |

Code flow:

- Builds actual future matrices.
- Applies clipping to generation and price forecasts.
- Computes COVE reduction from revenues.
- Evaluates several forecast candidates.
- Makes figures comparing forecast/dispatch choices.

| Constant / knob | Value or expression |
| --- | --- |
| REPO | Path(__file__).resolve().parents[3] |
| BASE_DIR | Path(__file__).resolve().parent |
| OUT | BASE_DIR / 'best_forecast_dispatch_search_results' |
| MAX_HORIZON | 168 |
| HORIZONS | [24, 48, 72, 168] |
| PRICE_CLIP | (-500.0, 1500.0) |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| matrix_from_indices | 29 | values, origins, indexer | Builds horizon matrices by taking future values at each origin. |
| actual_future_matrix | 38 | values, origins | Builds actual future matrices for evaluation/oracle comparisons. |
| hourly_climatology_matrix | 42 | values, datetimes, train_end, origins, statistic | Builds a simple hour-of-day historical average forecast matrix. |
| clip_generation | 66 | forecasts | Keeps generation predictions inside physical bounds. |
| clip_price | 70 | forecasts | Clips price forecasts to avoid extreme unstable values. |
| cove_reduction_from_revenues | 74 | dispatch_revenue, baseload_revenue | Computes COVE reduction implied by revenue changes. |
| candidate_summary | 78 | labels, candidate, wind_forecast, price_forecast, horizon, is_oracle | Summarizes one forecast/dispatch candidate. |
| evaluate_forecasts | 123 | values, origins, forecast_map, variable | Evaluates multiple forecast candidates. |
| legacy_power_model_metrics | 137 | - | Loads metrics from older power-model outputs. |
| make_figures | 187 | summary, forecast_metrics, legacy_metrics | Creates the script-specific figures. |
| main | 275 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, json, math, sys, pathlib:Path, matplotlib, matplotlib.pyplot, numpy, pandas, run_nora_matching_forecast_horizons`

### different scenarios/code/run_nora_matching_forecast_horizons.py

| Question | Answer |
| --- | --- |
| Purpose | Copy of the Nora-style horizon helper used by scenario code. It supplies shared forecasting, Gurobi, revenue, COVE, and constraint functions. |
| When to run | Support file; scenario runner imports it as base. |
| Reads | Processed Pyron dataset and optional Nora validation week. |
| Writes | Only when run directly: forecast horizon summaries and figures. |
| Line count | 775 |

Code flow:

- Defines storage/cost constants.
- Fits direct forecasts.
- Solves Nora-compatible dispatch windows.
- Executes frozen plans.
- Computes revenue, COVE, and constraint checks.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| OUT | Path(__file__).resolve().parent / 'nora_matching_forecast_horizon_results' |
| DATA_PATH | REPO_ROOT / 'data' / 'processed' / 'dataset_1980-2023_withloads_fix.csv' |
| NORA_PATH | Path(os.environ.get('NORA_WEEK_XLSX', '/Users/davidvalenta/Downloads/january6-12.xlsx')) |
| HORIZONS | [24, 48, 72, 168] |
| STEP_HOURS | 24 |
| PAST_LAGS | (1, 2, 3, 6, 12, 24, 48, 168) |
| PS | 100.0 |
| DURATION_HOURS | 10.0 |
| RTE | 0.55 |
| SQRT_RTE | math.sqrt(RTE) |
| CMAX | PS * DURATION_HOURS |
| DOD | 0.8 |
| CMIN | CMAX * (1.0 - DOD) |
| SOC0 | (CMIN + CMAX) / 2.0 |
| GRID_CAP | 249.0 |
| FCR | 0.065 |
| WF_CAPEX | 1968.0 |
| WF_OPEX | 43.0 |
| CAES_CAPEX | 2044.0 |
| CAES_OPEX | 28.1 |

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| DirectForecastModel | 50 | - | Small container for direct multi-step forecast model coefficients and normalization statistics. |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| calendar_features | 63 | timestamps | Creates hour/day/month cyclical features. |
| origin_features | 80 | values, origins | Builds forecast features for many rolling origins. |
| single_origin_features | 95 | values, origin | Builds forecast features for one origin and one future lead. |
| fit_direct_models | 110 | values, datetimes, train_end, max_horizon, target_min, target_max, alpha, origin_stride | Fits direct multi-step forecast models for wind generation and price. |
| make_generation_forecasts | 151 | values, datetimes, origins, models | Helper function used by this script. |
| make_weekly_price_forecasts | 171 | prices, origins, max_horizon | Helper function used by this script. |
| forecast_metrics | 180 | actual, origins, forecasts, variable | Calculates forecast error by lead-time block. |
| solve_window_nora | 210 | forecast_generation, forecast_price, start_soc, horizon | Optimize one forecast window with the Nora-matching Gurobi equations. |
| execute_frozen_day | 261 | planned, actual_generation, start_soc, execute_len | Helper function used by this script. |
| run_forecast_horizon | 317 | df, origins, generation_forecasts, price_forecasts, horizon | Helper function used by this script. |
| revenue | 396 | power, price | Computes revenue from price and delivered/generated power. |
| annualized_dispatch_cost | 400 | - | Helper function used by this script. |
| continuous_baseload | 406 | generation | Computes the baseload reference for comparison. |
| check_realized_constraints | 426 | labels | Checks realized hourly dispatch for constraint violations. |
| summarize | 448 | labels_by_horizon | Creates summary metrics from hourly dispatch labels. |
| validate_nora_week | 487 | - | Helper function used by this script. |
| make_figures | 505 | summary, metrics, labels_by_horizon | Creates the script-specific figures. |
| main | 650 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, json, math, os, time, dataclasses:dataclass, pathlib:Path, gurobipy, matplotlib, matplotlib.pyplot, numpy, pandas, gurobipy:GRB`

### different scenarios/code/run_uncertainty_aware_dispatch.py

| Question | Answer |
| --- | --- |
| Purpose | The main uncertainty-aware dispatch engine. It builds multiple plausible wind/price futures, solves a scenario MILP, executes the first hour, and repeats. |
| When to run | Usually called by RUN_3_SCENARIO_COMPARISON.py. Direct flags control horizon, storage, scenario variants, max origins, calibration mode, and output folder. |
| Reads | Processed Pyron dataset and forecast/dispatch helpers from run_nora_matching_forecast_horizons.py. |
| Writes | uncertainty_aware_summary.csv, one hourly labels CSV per scenario method, figures, and metadata. |
| Line count | 749 |

Code flow:

- Builds central wind and price forecasts.
- Computes residual quantiles for uncertainty bands.
- Creates scenario matrices for pessimistic/central/optimistic futures.
- Solves a scenario MILP where the first-hour action is shared across futures.
- Executes that first hour against actual realized wind/price.
- Compares single forecast, 3, 5, 7, and 10 scenario cases against baseload.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| BASE_DIR | Path(__file__).resolve().parent |
| OUT | BASE_DIR.parents[0] / 'results' / 'scenario_48h_full_ladder' |
| HORIZON | 48 |
| SCENARIO_SPECS | {'three_scenario_expected': {'weights': np.array([0.5, 0.25, 0.25], dtype=float), 'wind_quantiles': [0.5, 0.1, 0.9], 'pr |

| Line | Command-line argument |
| --- | --- |
| 533 | --horizon-hours |
| 534 | --storage-power-mw |
| 535 | --storage-duration-h |
| 536 | --rte |
| 537 | --dod |
| 538 | --grid-cap-mw |
| 539 | --initial-soc-mwh |
| 545 | --max-origins |
| 546 | --variants |
| 557 | --nowcast-first-hour |
| 564 | --no-nowcast-first-hour |
| 570 | --gate-margin |
| 571 | --out-dir |
| 572 | --calibration-mode |
| 578 | --forecast-train-end |
| 579 | --calibration-end |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| matrix_from_indices | 70 | values, origins, indexer | Builds horizon matrices by taking future values at each origin. |
| build_forecasts | 78 | df, train_end, origins | Helper function used by this script. |
| conformal_quantile | 102 | values, q | Computes a conformal-style quantile value from residuals. |
| residual_quantiles | 111 | df, residual_start, residual_end, models, quantiles, method | Estimates residual quantiles used to build uncertainty scenarios. |
| scenario_matrices | 138 | center_wind, center_price, quantile_lookup, spec | Builds multiple forecast futures from central forecast plus residual quantiles. |
| solve_scenario_window | 156 | generation_scenarios, price_scenarios, weights, start_soc, risk_lambda | Builds and solves one scenario MILP window with shared first-hour action. |
| execute_first_hour_storage_action | 226 | action, actual_generation, start_soc | Executes only the first-hour scenario action against realized wind/price. |
| baseline_value_for_scenarios | 263 | generation_scenarios, price_scenarios, weights, start_soc, target_mw | Computes the baseline value used in the scenario comparison. |
| baseline_first_hour_action | 298 | actual_generation, start_soc, target_mw | Builds a simple baseline first-hour action. |
| run_single_forecast_recourse | 333 | df, origins, wind_center, price_center, max_origins, nowcast_first_hour, gate_margin, baseline_target_mw | Runs the one-forecast recourse controller. |
| run_scenario_controller | 394 | df, origins, wind_center, price_center, quantile_lookup, spec_name, max_origins, nowcast_first_hour, gate_margin, baseline_target_mw | Runs the multi-scenario controller through the test period. |
| make_label_row | 458 | df, origin, horizon, forecast_generation, forecast_price, action, realized | Creates one hourly output row for scenario labels. |
| summarize | 492 | labels, candidate, wind_forecast, price_forecast | Creates summary metrics from hourly dispatch labels. |
| make_figures | 504 | summary | Creates the script-specific figures. |
| main | 530 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, json, math, os, sys, time, pathlib:Path, gurobipy, matplotlib, matplotlib.pyplot, numpy, pandas, gurobipy:GRB, run_nora_matching_forecast_horizons, run_best_forecast_dispatch_search:PRICE_CLIP,candidate_summary,cove_reduction_from_revenues`

## oracle upper bound

Runs the perfect-future ceiling. Gurobi sees actual future wind and actual future price, so this is not deployable but shows the upper bound under the same storage constraints.

Main command: `cd "Summer 2026 REU/oracle upper bound" && ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py`

### oracle upper bound/EXPERIMENT_KNOBS.py

| Question | Answer |
| --- | --- |
| Purpose | The one place to change Step 4 perfect-future oracle settings. |
| When to run | Do not run directly. Edit it, then run RUN_4_ORACLE_UPPER_BOUND.py. |
| Reads | Defines data path, config, storage settings, SoC fractions, oracle horizon list, and output folder. |
| Writes | No output by itself. |
| Line count | 36 |

Top docstring: One place to change Step 4 oracle upper-bound settings. Edit this file, then run: ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py

Code flow:

- Sets the same 100 MW / 10 h storage setup as Step 2.
- Sets oracle horizon list.
- The Step 4 wrapper passes these values to the oracle-only runner.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| REPO_ROOT | HERE.parents[1] |
| OUTPUT_DIR | HERE / 'results' / 'current_run_from_knobs' |
| DATA | REPO_ROOT / 'data' / 'processed' / 'dataset_1980-2023_withloads_fix.csv' |
| CONFIG | REPO_ROOT / 'strategy_model' / 'test' / 'run_016' / 'config_run_016.yaml' |
| TRAIN_END | '2014-01-01' |
| TEST_END | None |
| ALPHA | 10.0 |
| TRAIN_ORIGIN_STRIDE | 24 |
| STORAGE_POWER_MW | 100.0 |
| STORAGE_DURATION_H | 10.0 |
| GRID_CAP_MW | 249.0 |
| MIN_SOC_FRAC | 0.2 |
| MAX_SOC_FRAC | 1.0 |
| INITIAL_SOC_MWH | None |
| HORIZONS | [24, 48, 72, 168] |
| MIP_GAP | 0.0 |

Important imports: `pathlib:Path`

### oracle upper bound/RUN_4_ORACLE_UPPER_BOUND.py

| Question | Answer |
| --- | --- |
| Purpose | Main Step 4 command. It reruns the perfect-future oracle upper-bound backtest from the knobs file, filters oracle rows, prints results, and regenerates figures. |
| When to run | ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py |
| Reads | EXPERIMENT_KNOBS.py and code/forecast_backtest_rolling_horizons.py in oracle-only mode. |
| Writes | results/current_run_from_knobs/oracle_upper_bound_summary.csv, oracle_dispatch_*h.csv hourly outputs, and figures/step4_*.png. |
| Line count | 205 |

Top docstring: Step 4: perfect-future oracle upper bound. Run from this folder: ../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py This is not a realistic controller. It shows the best possible Gurobi result when the optimizer is allowed to know future wind and future price perfectly.

Code flow:

- Builds the oracle-only command from EXPERIMENT_KNOBS.py.
- Runs forecast_backtest_rolling_horizons.py with --oracle-only.
- Keeps only oracle rows.
- Prints the upper-bound table.
- Plots oracle gain, COVE, runtime/value, and 3D ceiling figures.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parent |
| RESULTS | Path(knobs.OUTPUT_DIR) |
| FIGURES | HERE / 'figures' |
| SUMMARY_FILE | RESULTS / 'forecast_dispatch_summary.csv' |
| ORACLE_ONLY_FILE | RESULTS / 'oracle_upper_bound_summary.csv' |
| RUNNER | HERE / 'code' / 'forecast_backtest_rolling_horizons.py' |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| load_rows | 41 | path | Reads a CSV file into a list of dictionaries so the wrapper can print and plot results. |
| add_optional | 48 | cmd, flag, value | Adds a command-line flag only when the knob value is not None. |
| rerun_from_knobs | 53 | - | Builds the real command from EXPERIMENT_KNOBS.py and runs it as a subprocess. |
| main | 92 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, csv, os, subprocess, sys, tempfile, pathlib:Path, matplotlib, matplotlib.pyplot, mpl_toolkits.mplot3d:Axes3D, EXPERIMENT_KNOBS`

### oracle upper bound/code/build_oracle_summary.py

| Question | Answer |
| --- | --- |
| Purpose | Small post-processing helper that extracts oracle rows from a combined forecast/oracle summary table. |
| When to run | Use when a combined forecast_dispatch_summary.csv already exists and you only want oracle_upper_bound_summary.csv. |
| Reads | forecast_dispatch_summary.csv. |
| Writes | oracle_upper_bound_summary.csv. |
| Line count | 66 |

Top docstring: Build the oracle upper-bound summary from the rolling-horizon result table. Oracle means Gurobi receives the realized future wind and realized future price. That is not deployable in real life, but it is useful because it shows the best possible value for the same storage constraints and horizons.

Code flow:

- Reads the combined summary.
- Filters rows where method is oracle.
- Sorts by horizon.
- Writes the oracle-only summary.

| Constant / knob | Value or expression |
| --- | --- |
| HERE | Path(__file__).resolve().parents[1] |
| DEFAULT_SOURCE | HERE.parents[0] / 'rolling horizon' / 'results' / 'causal_ridge_rolling_horizon_summary.csv' |
| DEFAULT_OUTPUT | HERE / 'results' / 'oracle_upper_bound_summary.csv' |

| Line | Command-line argument |
| --- | --- |
| 29 | --source |
| 30 | --output |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| main | 27 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, pathlib:Path, pandas`

### oracle upper bound/code/dataset.py

| Question | Answer |
| --- | --- |
| Purpose | Tiny PyTorch Dataset wrappers copied from the original power-model code. They let tensors be indexed by PyTorch DataLoader. |
| When to run | Not run directly. |
| Reads | In-memory tensors/arrays. |
| Writes | Dataset objects used by model/data-loading utilities. |
| Line count | 44 |

Code flow:

- VF2Dataset returns two-input examples.
- VFDataset returns regular feature/target examples.
- These are support classes for old neural-network utilities, not the main Gurobi result.

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| VF2Dataset | 4 | Dataset | PyTorch Dataset wrapper returning examples with two feature inputs. |
| VFDataset | 27 | Dataset | PyTorch Dataset wrapper returning feature/target examples. |

Important imports: `torch.utils.data:Dataset`

### oracle upper bound/code/forecast_backtest_rolling_horizons.py

| Question | Answer |
| --- | --- |
| Purpose | Copied deterministic/oracle backtest engine used by the oracle folder. In Step 4 it is called with --oracle-only, so it writes only perfect-future oracle rows and hourly CSVs. |
| When to run | Usually called by RUN_2_ROLLING_HORIZON.py or RUN_4_ORACLE_UPPER_BOUND.py. Direct flags control data, config, train/test split, storage, horizons, direct reserve, and oracle-only mode. |
| Reads | data/processed/dataset_1980-2023_withloads_fix.csv, strategy_model/test/run_016/config_run_016.yaml, and helper modules. |
| Writes | forecast_dispatch_summary.csv, forecast_accuracy_by_lead.csv, forecast_dispatch_*h.csv, oracle_dispatch_*h.csv, figures, and metadata. |
| Line count | 1016 |

Top docstring: Backtest rolling-horizon Gurobi dispatch with causal forecasts. The forecasting models are trained on an early chronological period and frozen. During the later backtest, every daily forecast uses only values observed before that forecast was issued. Gurobi plans from forecast wind generation and price, but only the first 24 hours are executed and scored against actual outcomes.

Code flow:

- Builds lag/calendar features for generation and price forecasts.
- Creates forecast matrices for every rolling origin.
- Optionally creates actual-future matrices for oracle runs.
- Calls solve_window() from rolling_horizon_gurobi_dispatch.py.
- Executes planned actions against actual wind/price with recourse.
- Applies direct reserve to avoid blindly curtailing forecast underprediction.
- Checks realized constraints and summarizes revenue/COVE.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| SUMMER_STEP_DIR | Path(__file__).resolve().parents[1] |
| STRATEGY_SRC | REPO_ROOT / 'strategy_model' / 'src' |
| OPTIMIZATION_DIR | REPO_ROOT / 'strategy_model' / 'optimization' |
| PAST_LAGS | (1, 2, 3, 6, 12, 24, 48, 168) |
| DEFAULT_HORIZONS | (24, 48, 72, 168) |

| Line | Command-line argument |
| --- | --- |
| 713 | --data |
| 722 | --config |
| 732 | --train-end |
| 733 | --test-end |
| 734 | --alpha |
| 735 | --train-origin-stride |
| 736 | --price-signal |
| 742 | --mip-gap |
| 743 | --storage-power-mw |
| 744 | --storage-duration-h |
| 745 | --grid-cap-mw |
| 746 | --initial-soc |
| 752 | --min-soc-frac |
| 753 | --max-soc-frac |
| 754 | --direct-reserve-mw |
| 764 | --horizons |
| 771 | --oracle-only |
| 776 | --skip-oracle |
| 777 | --out-dir |

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| DirectForecastModel | 51 | - | Small container for direct multi-step forecast model coefficients and normalization statistics. |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| calendar_features | 64 | timestamps | Creates hour/day/month cyclical features. |
| origin_features | 81 | values, origins | Builds forecast features for many rolling origins. |
| single_origin_features | 96 | values, origin | Builds forecast features for one origin and one future lead. |
| fit_direct_models | 112 | values, datetimes, train_end, max_horizon, target_min, target_max, alpha, origin_stride, known_future_values | Fits direct multi-step forecast models for wind generation and price. |
| make_forecast_matrix | 166 | values, datetimes, origins, models, known_future_values | Creates a matrix of forecasts, one row per origin and one column per lead hour. |
| make_known_future_matrix | 191 | values, origins, max_horizon | Creates an oracle matrix using actual future values instead of forecasts. |
| forecast_metrics | 202 | actual, origins, forecasts, name | Calculates forecast error by lead-time block. |
| execute_plan_against_actual | 235 | planned, actual_generation, initial_soc, config, min_soc_frac, max_soc_frac | Converts a forecast plan into realized feasible operation using actual wind and price. |
| check_realized_constraints | 299 | labels, config, min_soc_frac, max_soc_frac | Checks realized hourly dispatch for constraint violations. |
| apply_direct_reserve | 355 | solution, config, direct_reserve_mw | Adds planned direct-wind reserve for causal forecast execution. |
| run_horizon | 382 | df, test_start, origins, generation_forecasts, price_forecasts, horizon, config, initial_soc, min_soc_frac, max_soc_frac, mip_gap, perfect_information, direct_reserve_mw | Runs one horizon length through the rolling-horizon backtest. |
| style_axis | 525 | axis | Applies consistent plotting style. |
| save_figures | 532 | summary, metrics, labels_by_horizon, output_dir, horizons | Writes summary figures to disk. |
| main | 709 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, json, math, os, sys, time, dataclasses:dataclass, pathlib:Path, matplotlib, matplotlib.pyplot, numpy, pandas, util, rolling_horizon_gurobi_dispatch:continuous_baseload,cove_value,fixed_costs,solve_window`

### oracle upper bound/code/model.py

| Question | Answer |
| --- | --- |
| Purpose | Original neural-network model definitions copied into the folder so old model-loading utilities still work locally. |
| When to run | Not run directly. |
| Reads | PyTorch tensors. |
| Writes | Predicted model outputs from neural-network forward passes. |
| Line count | 190 |

Code flow:

- VFNN_2 and VFNN define feed-forward neural networks.
- PLinear defines a positive/parameterized linear layer style helper.
- These files support original NQF/power-model utilities but are not the main Summer ladder command.

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| VFNN_2 | 8 | nn.Module | Original feed-forward neural network that accepts two input branches. |
| VFNN | 109 | nn.Module | Original feed-forward neural network for value/power forecasting. |
| PLinear | 176 | nn.Module | Original custom linear layer helper used by neural-network code. |

Important imports: `torch, torch.nn, torch.nn.functional, util, numpy`

### oracle upper bound/code/rolling_horizon_gurobi_dispatch.py

| Question | Answer |
| --- | --- |
| Purpose | Copied lower-level Gurobi MILP dispatch engine used by the oracle folder. Same constraints as the rolling-horizon folder. |
| When to run | Used as a helper by forecast_backtest_rolling_horizons.py, but can also be run directly for rolling-horizon optimization. |
| Reads | Forecast or actual generation/price arrays plus storage config. |
| Writes | Hourly labels, summary metrics, constraint checks, and optional progress files. |
| Line count | 496 |

Top docstring: Rolling-horizon Gurobi dispatch with Nora's MILP constraints. This experiment uses Gurobi as the mixed-integer teacher for COVE-DV. Summary: - At each time step, Gurobi looks ahead a fixed number of hours. - It chooses charge, discharge, hold, direct-to-grid, delivered power, and storage. - Only the first part of that plan is executed. - Then the battery state carries forward chronologically and the window rolls. The default model includes Nora's operational constraints: - storage capacity limits, - charging/discharging power limits, - one binary charge/discharge mode per hour, - available-energy discharge limit, - wind-only charging, - delivered power definition, - grid export limit, - storage state update, - end-of-horizon SoC_initial = SoC_final.

Code flow:

- Defines the MILP variables P_dir, P_ch, P_dis, P_delivered, SoC, and charge/discharge mode.
- Adds wind-only charging, grid cap, no simultaneous charge/discharge, and SoC update constraints.
- Maximizes price times delivered power.
- Runs windows chronologically and carries SoC forward.
- Summarizes revenue, COVE, curtailment, runtime, and violations.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| STRATEGY_SRC | REPO_ROOT / 'strategy_model' / 'src' |

| Line | Command-line argument |
| --- | --- |
| 415 | --data |
| 416 | --config |
| 417 | --out-dir |
| 418 | --hours |
| 419 | --offset |
| 420 | --horizon-hours |
| 421 | --step-hours |
| 422 | --terminal-policy |
| 423 | --initial-soc |
| 424 | --min-soc-frac |
| 425 | --max-soc-frac |
| 426 | --mip-gap |
| 427 | --time-limit |
| 428 | --max-windows |
| 429 | --progress-every |
| 430 | --storage-type |
| 431 | --storage-rating |
| 432 | --storage-duration |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| load_data | 44 | data_path, config, offset, hours | Loads generation and price data for rolling-horizon dispatch. |
| cove_value | 52 | power, price, config | Computes COVE value for a given revenue and storage setup. |
| continuous_baseload | 66 | power, config, initial_soc | Computes the baseload reference for comparison. |
| fixed_costs | 90 | config | Computes annualized wind/storage cost used in COVE. |
| solve_window | 101 | generation, price, config, initial_soc, terminal_policy, min_soc_frac, max_soc_frac, mip_gap, time_limit | Builds and solves one Gurobi MILP dispatch window. |
| check_constraints | 193 | labels, config, min_soc_frac, max_soc_frac | Checks Gurobi output for constraint violations. |
| write_progress | 223 | path, rows | Writes progress checkpoints during long rolling runs. |
| run_rolling | 234 | df, config, horizon_hours, step_hours, terminal_policy, initial_soc, min_soc_frac, max_soc_frac, mip_gap, time_limit, max_windows, progress_every, checkpoint_path | Runs the low-level rolling-horizon loop across many windows. |
| add_compatibility_columns | 340 | labels, config | Adds older column names so old analysis scripts still work. |
| summarize | 362 | labels, window_rows, config, args | Creates summary metrics from hourly dispatch labels. |
| main | 413 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, csv, json, math, sys, time, pathlib:Path, numpy, pandas, util`

### oracle upper bound/code/storage.py

| Question | Answer |
| --- | --- |
| Purpose | Storage technology definitions: lithium-ion, CAES, hydro, lead-acid, flow battery, zinc, hydrogen, gravitational, and thermal. |
| When to run | Not run directly. |
| Reads | No data files. |
| Writes | Storage objects with capital cost, operating cost, duration, and efficiency values. |
| Line count | 159 |

Code flow:

- Base Storage stores cost/performance fields.
- Each child class fills in values for one storage technology.
- Util functions use these classes for RTE, cost, and COVE calculations.

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| Storage | 4 | - | Base storage technology object containing efficiency/cost/duration fields. |
| BatteryLI | 26 | Storage | Lithium-ion storage parameter class. |
| CAES | 45 | Storage | Compressed-air energy storage parameter class. |
| Hydro | 58 | Storage | Hydropower/pumped-storage style parameter class. |
| BatteryLA | 71 | Storage | Lead-acid battery parameter class. |
| BatteryVRF | 90 | Storage | Vanadium redox flow battery parameter class. |
| Zinc | 109 | Storage | Zinc storage parameter class. |
| Hydrogen | 122 | Storage | Hydrogen storage parameter class. |
| Gravitational | 135 | Storage | Gravitational storage parameter class. |
| Thermal | 148 | Storage | Thermal storage parameter class. |

Important imports: `numpy`

### oracle upper bound/code/util.py

| Question | Answer |
| --- | --- |
| Purpose | Original utility module for storage lookup, COVE/revenue math, price normalization, config loading, model loading, dataset loading, and plotting losses. |
| When to run | Not run directly. |
| Reads | Config YAML, CSV data, PyTorch model checkpoints, and storage names. |
| Writes | Loaded models/datasets, normalized prices, revenue/COVE calculations, and plots. |
| Line count | 368 |

Code flow:

- Maps storage names to storage objects.
- Computes revenue, value factor, and COVE.
- Normalizes price columns.
- Loads YAML configs and saved PyTorch models.
- Builds train/validation/test datasets.

| Constant / knob | Value or expression |
| --- | --- |
| STORAGE_TYPES | np.array(['battery-li', 'caes', 'hydro', 'battery-la', 'battery-vrf', 'hydrogen', 'zinc', 'grav', 'thermal']) |
| STORAGE_OBJECTS | np.array([BatteryLI(), CAES(), Hydro(), BatteryLA(), BatteryVRF(), Hydrogen(), Zinc(), Gravitational(), Thermal()]) |
| FCR | 0.065 |
| WF_CAPEX | 1968 |
| WF_OPEX | 43 |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| get_storage_object | 19 | type | Returns the storage object for a storage name. |
| get_rte | 23 | type, rating, duration | Returns storage round-trip efficiency. |
| get_storage_specs | 27 | type, rating, duration | Returns storage cost/performance parameters. |
| cove | 37 | power, price, storage_type, storage_rating, storage_duration, wf_rating, num_modules | Computes cost of valued energy in the older utility style. |
| revenue | 48 | power, price, range | Computes revenue from price and delivered/generated power. |
| value_factor | 56 | power, price | Computes the value factor of generation relative to price. |
| batchwise_revenue | 61 | batch_power, batch_price | Computes revenue over batches/tensors. |
| batchwise_value_factor | 65 | batch_power, batch_price | Computes value factor over batches/tensors. |
| batchwise_cove | 71 | batch_power, batch_price, epsilon, storage_type, storage_rating, storage_duration, wf_rating, num_modules | Computes COVE over batches/tensors. |
| normalize_price | 89 | prices, config | Normalizes price data for model training. |
| load_config | 101 | file_path | Loads YAML experiment configuration. |
| save_config | 106 | config, file_path | Writes YAML experiment configuration. |
| load_model | 110 | model_path, config_path, with_loads | Loads a saved PyTorch model. |
| load_model_with_loads | 118 | model_path, config_path | Loads a saved PyTorch model that includes load features. |
| load_dataset_no_split | 131 | csv_path, config, with_loads, cf | Loads a dataset without train/test splitting. |
| load_dataset_split_as_tensors | 150 | csv_path, config | Loads dataset splits as tensors. |
| load_dataset_no_split_with_loads | 194 | csv_path, config, cf | Loads dataset with load features and no split. |
| load_dataset | 214 | csv_path, config, with_loads, no_shuffle, cf | Loads train/validation/test datasets. |
| load_dataset_with_loads | 274 | csv_path, config | Loads datasets that include load features. |
| load_experiment | 331 | folder_name, dataset_path, with_loads, cf, no_split, no_shuffle | Loads a saved experiment folder. |
| plot_losses | 343 | train_losses, val_losses, fname | Plots training and validation losses. |
| format_num | 362 | num | Formats numbers for display. |

Important imports: `numpy, yaml, matplotlib.pyplot, torch, os, model:VFNN,VFNN_2, pandas, dataset:VFDataset,VF2Dataset, torch.utils.data:Dataset,DataLoader, storage:*`

## b6 verification

Contains the separate B6 frozen 2020 validation packet requested by Chris. It reruns exactly six A/B/C oracle/causal cases and validates the hourly outputs.

Main command: `cd "Summer 2026 REU/b6 verification" and run the B6 runner/validator from code/ when Chris asks for the frozen B6 package.`

### b6 verification/code/B6_CANONICAL_RUNNER.py

| Question | Answer |
| --- | --- |
| Purpose | The full frozen B6 package runner. It runs exactly six 2020 cases: architectures A, B, C crossed with Oracle and Causal. |
| When to run | Run only when rebuilding the B6 package Chris requested. |
| Reads | Complete 2020 Pyron wind and raw PYR_PYRON1 LMP files. |
| Writes | Six hourly CSVs, run summary, QA files, configs, logs, and metadata. |
| Line count | 767 |

Code flow:

- Loads complete 8,784-hour 2020 data.
- Builds causal forecasts for causal cases.
- Uses actual future values for oracle cases.
- Solves Gurobi MILP windows.
- Executes planned actions with corrected direct/curtailment recourse.
- Enforces annual 20% SoC rule.
- Writes all package deliverables.

| Constant / knob | Value or expression |
| --- | --- |
| PAST_LAGS | (1, 2, 3, 6, 12, 24, 48, 168) |
| ARCHITECTURES | {'A': {'power_mw': 100.0, 'duration_h': 6.0}, 'B': {'power_mw': 200.0, 'duration_h': 3.0}, 'C': {'power_mw': 100.0, 'dur |

| Line | Command-line argument |
| --- | --- |
| 659 | --repo |
| 660 | --out |

| Class | Line | Base | Meaning |
| --- | --- | --- | --- |
| ForecastModel | 27 | - | Small container for fitted forecast coefficients, feature means/scales, and feature names in the B6 runner. |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| git_value | 40 | repo | Runs a Git command and returns the result for metadata/reproducibility. |
| parse_power_file | 44 | path | Parses the Pyron power CSV into timestamps and MW generation. |
| parse_raw_lmp_file | 53 | path | Parses the raw ERCOT LMP file used in B6. |
| load_b6_data | 67 | repo | Loads and aligns the complete B6 2020 wind and price data. |
| calendar_features | 142 | timestamps | Creates hour/day/month cyclical features. |
| origin_features | 159 | values, origins | Builds forecast features for many rolling origins. |
| single_origin_features | 174 | values, origin | Builds forecast features for one origin and one future lead. |
| fit_direct_models | 189 | values, timestamps, train_end, max_horizon, alpha | Fits direct multi-step forecast models for wind generation and price. |
| make_forecasts | 221 | values, timestamps, origins, models | Creates B6 forecast values from trained direct models. |
| prepare_forecast_frame | 239 | repo, b6_2020, horizon | Builds the feature/forecast frame for B6 causal dispatch. |
| solve_dispatch_window | 290 | generation, price, power_mw, capacity_mwh, grid_cap_mw, rte, min_soc_frac, max_soc_frac, initial_soc, terminal_equal_initial, terminal_soc_value, mip_gap, time_limit | Helper function used by this script. |
| execute_plan | 371 | solution, actual_generation, initial_soc, power_mw, capacity_mwh, grid_cap_mw, rte, min_soc_frac, max_soc_frac | Helper function used by this script. |
| qa_checks | 421 | labels, power_mw, capacity_mwh, grid_cap_mw, rte, min_soc_frac, max_soc_frac, annual_terminal_soc_mwh | Helper function used by this script. |
| discharge_loss | 462 | discharge_mwh, rte | Converts discharge-side efficiency into storage energy loss accounting. |
| run_oracle | 467 | df, arch_id, cfg | Runs the B6 oracle workflow. |
| run_causal | 505 | df, forecasts, arch_id, cfg | Runs the B6 causal workflow. |
| summarize | 582 | labels, arch_id, workflow, cfg, runtime, solver_status, mip_gap | Creates summary metrics from hourly dispatch labels. |
| write_hourly | 634 | labels, output_path | Writes hourly labels to CSV with clean timestamps. |
| main | 656 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, json, platform, subprocess, sys, time, dataclasses:dataclass, pathlib:Path, gurobipy, numpy, pandas, gurobipy:GRB`

### b6 verification/code/B6_FINAL_VALIDATE.py

| Question | Answer |
| --- | --- |
| Purpose | QA validator for the B6 final package. |
| When to run | Run after B6_CANONICAL_RUNNER.py to confirm the package passes the checks Chris asked for. |
| Reads | B6 final results folder with six hourly CSVs and summary files. |
| Writes | Printed validation result and optional validation artifacts. |
| Line count | 113 |

Top docstring: Validate the canonical B6 result folder. This checks the things Chris specifically cared about: - exactly six runs, - 8784 rows in every hourly CSV, - raw revenue equals delivered power times raw realized LMP, - zero physical constraint violations, - final realized SoC equals the annual 20% target.

Code flow:

- Checks exactly six runs.
- Checks 8,784 rows per hourly file.
- Recomputes raw realized revenue from delivered power times raw LMP.
- Checks zero physical constraint violations.
- Checks final realized annual SoC equals 20% of energy capacity.

| Constant / knob | Value or expression |
| --- | --- |
| REPO_ROOT | Path(__file__).resolve().parents[3] |
| DEFAULT_RESULTS | REPO_ROOT / 'strategy_model' / 'optimization' / 'b6_final_results' |
| EXPECTED_RUNS | {'A_ORACLE', 'A_CAUSAL', 'B_ORACLE', 'B_CAUSAL', 'C_ORACLE', 'C_CAUSAL'} |

| Line | Command-line argument |
| --- | --- |
| 106 | --results-dir |

| Function | Line | Arguments | What it does |
| --- | --- | --- | --- |
| validate | 33 | results_dir | Runs B6 validation checks and reports failures. |
| main | 104 | - | Entry point. Parses arguments or orchestrates the script when run from the terminal. |

Important imports: `__future__:annotations, argparse, json, pathlib:Path, numpy, pandas`

## Glossary

| Term | Meaning |
| --- | --- |
| Baseload | Reference behavior. In this repo it is the thing every improvement is compared to. The 100 MW baseload tries to deliver 100 MW every hour using wind plus storage. |
| Causal forecast | A forecast that only uses information available before the decision time. This is realistic. |
| Oracle | Perfect-future case where Gurobi sees actual future wind and price. Not realistic; used as an upper bound. |
| Rolling horizon | Solve a future-looking optimization, execute only the first part, update SoC, then solve again. |
| Scenario dispatch | Run optimization with several possible forecast futures instead of one future. |
| SoC | State of charge: energy currently stored in the battery/CAES system, measured in MWh. |
| Direct wind | Wind sent straight to the grid instead of storage. |
| Charge | Wind energy sent into storage. |
| Discharge | Stored energy released back to the grid. |
| Curtailment | Wind that could have been produced but is not delivered or stored. It is effectively unused. |
| Grid cap | Maximum delivered power allowed to the grid, 249 MW in the main setup. |
