# Python Reproduction Cheat Sheet

Start here when someone asks where a result lives or how to reproduce it.

## First Rule: Use B6 As The Frozen Benchmark

The Chris-compatible reproduction path is the B6 final package:

```bash
cd /Users/davidvalenta/deep-wind-model-dispatch
./venv/bin/python strategy_model/optimization/B6_CANONICAL_RUNNER.py
./venv/bin/python strategy_model/optimization/B6_FINAL_VALIDATE.py
./venv/bin/python strategy_model/optimization/REPO_REVIEWER_AUDIT.py
```

That path freezes one consistent benchmark setup:

- 2020 only.
- A/B/C architectures only.
- Oracle and Causal workflows only.
- Raw realized PYR_PYRON1 LMP in USD/MWh.
- 249 MW grid export cap.
- CAES-equivalent RTE = 0.55.
- Wind-only charging and no grid charging.
- 48-hour causal planning and 24-hour execution.
- Minimum SoC, initial SoC, and final realized annual SoC all equal 20% of capacity.
- Causal execution keeps planned direct wind and curtails remaining wind.

The B6 result folder is:

```text
strategy_model/optimization/b6_final_results/
```

The older long-run and scenario folders are research history unless they are
explicitly rerun under the B6 rules.

## The Ladder

| Level | Meaning | Main Python File | Main Output Folder |
| --- | --- | --- | --- |
| Frozen benchmark | Six B6 cases with one consistent Chris-approved setup. | `strategy_model/optimization/B6_CANONICAL_RUNNER.py` | `strategy_model/optimization/b6_final_results/` |
| Frozen QA | Checks all B6 rows, revenue, SoC, and constraints. | `strategy_model/optimization/B6_FINAL_VALIDATE.py` | `strategy_model/optimization/b6_final_results/` |
| Repo audit | Checks that Chris/reviewer files exist and B6 validates. | `strategy_model/optimization/REPO_REVIEWER_AUDIT.py` | printed PASS/FAIL |
| Chris memo map | Shows every memo item and where it lives. | `strategy_model/optimization/CHRIS_MEMO_CHECKLIST.py` | printed checklist |
| Constraint summary | Storage parameters and physical rules. | `strategy_model/optimization/NORA_PARAMETERS_AND_CONSTRAINTS.py` | printed summary |
| Research lower bound | Historical baseload reference, not the frozen B6 packet. | `strategy_model/optimization/LOWER_BOUND_BASELOAD.py` | `strategy_model/optimization/reviewer_reproduction/lower_bound_baseload/` |
| Research method 1 | Historical deterministic forecast rolling-horizon result. | `strategy_model/optimization/PROPOSED_METHOD_1_DETERMINISTIC_RH_MILP.py` | `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/` |
| Research method 2 | Historical scenario rolling-horizon result. | `strategy_model/optimization/PROPOSED_METHOD_2_SCENARIO_RH_MILP.py` | `strategy_model/optimization/uncertainty_aware_dispatch_results/` |
| Research upper bound | Historical oracle result. | `strategy_model/optimization/UPPER_BOUND_ORACLE.py` | `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/` |

## Chris Meeting Files

| Chris Asked For | Where To Open |
| --- | --- |
| Current frozen B6 runner | `strategy_model/optimization/B6_CANONICAL_RUNNER.py` |
| Current B6 validator | `strategy_model/optimization/B6_FINAL_VALIDATE.py` |
| Current B6 result folder | `strategy_model/optimization/b6_final_results/` |
| Current repo audit | `strategy_model/optimization/REPO_REVIEWER_AUDIT.py` |
| Current memo checklist | `strategy_model/optimization/CHRIS_MEMO_CHECKLIST.py` |
| Exact deterministic runner | `strategy_model/optimization/PROPOSED_METHOD_1_DETERMINISTIC_RH_MILP.py` |
| Scenario runner and objective | `strategy_model/optimization/PROPOSED_METHOD_2_SCENARIO_RH_MILP.py` and `strategy_model/optimization/run_uncertainty_aware_dispatch.py` |
| Lower bound / baseload | `strategy_model/optimization/LOWER_BOUND_BASELOAD.py` |
| Upper bound / oracle | `strategy_model/optimization/UPPER_BOUND_ORACLE.py` |
| Nora parameters and constraints | `strategy_model/optimization/NORA_PARAMETERS_AND_CONSTRAINTS.py` |
| Main Gurobi constraint implementation | `strategy_model/optimization/rolling_horizon_gurobi_dispatch.py` |
| Forecast-driven dispatch implementation | `strategy_model/optimization/forecast_backtest_rolling_horizons.py` |
| COVE-DV teacher-student map | `strategy_model/optimization/COVE_DV_TEACHER_STUDENT.py` |
| One-file command map | `strategy_model/optimization/REPRODUCE_REVIEWER_RESULTS.py` |

## Commands To Show First

Print the full map:

```bash
cd /Users/davidvalenta/deep-wind-model-dispatch
./venv/bin/python strategy_model/optimization/REPRODUCE_REVIEWER_RESULTS.py
```

Run and validate the frozen B6 packet:

```bash
./venv/bin/python strategy_model/optimization/B6_CANONICAL_RUNNER.py
./venv/bin/python strategy_model/optimization/B6_FINAL_VALIDATE.py
```

Print Nora/CAES constraints:

```bash
python strategy_model/optimization/NORA_PARAMETERS_AND_CONSTRAINTS.py
```

Print deterministic method command:

```bash
python strategy_model/optimization/PROPOSED_METHOD_1_DETERMINISTIC_RH_MILP.py
```

Print scenario method command:

```bash
python strategy_model/optimization/PROPOSED_METHOD_2_SCENARIO_RH_MILP.py
```

## What Each Result Means

Baseload is the comparison line. It answers: what happens if storage is used in a simple reference way instead of using forecast-aware Gurobi planning?

The deterministic rolling-horizon method is the realistic single-forecast case. It trains forecasts on past data, gives the forecast to Gurobi, executes only the first day, then repeats with the battery state carried forward.

The scenario method is the uncertainty-aware case. Instead of trusting one forecast, it gives Gurobi several possible futures and forces the first action to work across those futures.

The oracle is the upper bound. It lets Gurobi see the realized future, so it is not something a real operator can do. It tells us how much value is theoretically left if forecasts were perfect.

COVE-DV is the teacher-student neural experiment. Gurobi/MILP creates labels, and a neural network learns to imitate those dispatch decisions. It remains in the original optimization folder with the other dispatch work.

## Main Result Files

| Result | File |
| --- | --- |
| Power forecast metrics | `power_model/evaluation/causal_lag_forecast_metrics.csv` |
| Power forecast predictions | `power_model/evaluation/causal_lag_forecast_predictions.csv` |
| Nora matching weekly summary | `strategy_model/optimization/nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/rolling_horizon_gurobi_summary.csv` |
| Forecast horizon summary | `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_summary.csv` |
| Oracle dispatch hourly CSVs | `strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/oracle_dispatch_24h.csv` and matching horizon files |
| Scenario dispatch summary | `strategy_model/optimization/uncertainty_aware_dispatch_results/uncertainty_aware_summary.csv` |
| Scenario final table | `strategy_model/optimization/uncertainty_aware_dispatch_results/final_breakthrough_summary.csv` |
| COVE-DV key results | `strategy_model/optimization/cove_dv_results/cove_dv_key_results.csv` |
| New public proxy data | `data/newest_pyron_shaped/` |

## Important Numbers Currently Documented

| Result | Value |
| --- | ---: |
| Power forecast RMSE, causal lag ridge | 22.84 MW |
| Nora one-week Gurobi revenue | $500,809.95 |
| Nora one-week COVE reduction vs baseload | 13.56% |
| Perfect-information 168 h COVE reduction | 32.33% |
| Forecast-driven 48 h COVE reduction | 12.32% |
| Scenario seven-case revenue gain vs baseload | 17.41% |
| Scenario seven-case COVE reduction vs baseload | 14.83% |

## B6 Note

The B6 final email package is now represented in the repo as reproducible code,
validation logic, and generated result CSVs.
