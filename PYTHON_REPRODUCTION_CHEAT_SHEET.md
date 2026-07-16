# Python Reproduction Cheat Sheet

Start with the clean paper folder:

```text
Summer 2026 REU/
```

That folder contains the paper-facing scripts, result CSVs, figures, metadata, baseload references, oracle upper-bound files, and B6 verification outputs. Raw input data is intentionally not copied into that folder.

## Main Paper Folders

| Folder | What it reproduces |
| --- | --- |
| `Summer 2026 REU/causal ridge regression/` | causal ridge/lag forecast dispatch, oracle upper bound, forecast accuracy, horizon results |
| `Summer 2026 REU/rolling horizon/` | rolling-horizon Gurobi solver, horizon comparison, B6 verification |
| `Summer 2026 REU/different scenarios/` | scenario-based uncertainty-aware dispatch result |

## Main Paper Scripts

| Topic | Real script |
| --- | --- |
| Causal ridge forecast backtest | `strategy_model/optimization/forecast_backtest_rolling_horizons.py` |
| Oracle upper bound | `strategy_model/optimization/forecast_backtest_rolling_horizons.py` |
| Robustness/statistics | `strategy_model/optimization/analyze_forecast_backtest_robustness.py` |
| Rolling-horizon Gurobi solver | `strategy_model/optimization/rolling_horizon_gurobi_dispatch.py` |
| Scenario dispatch | `strategy_model/optimization/run_uncertainty_aware_dispatch.py` |
| B6 verification runner | `strategy_model/optimization/B6_CANONICAL_RUNNER.py` |
| B6 validator | `strategy_model/optimization/B6_FINAL_VALIDATE.py` |

## Main Paper Result Files

| Result | File |
| --- | --- |
| Scenario final table | `Summer 2026 REU/different scenarios/results/final_breakthrough_summary.csv` |
| Scenario summary | `Summer 2026 REU/different scenarios/results/uncertainty_aware_summary.csv` |
| Causal/oracle horizon summary | `Summer 2026 REU/causal ridge regression/results/forecast_backtest_2014_2023/forecast_dispatch_summary.csv` |
| Forecast accuracy | `Summer 2026 REU/causal ridge regression/results/forecast_backtest_2014_2023/forecast_accuracy_by_lead.csv` |
| Robustness tests | `Summer 2026 REU/causal ridge regression/results/forecast_backtest_robustness/` |
| Rolling-horizon comparison | `Summer 2026 REU/rolling horizon/results/rolling_horizon_comparison.csv` |
| Full-dataset comparison | `Summer 2026 REU/rolling horizon/results/full_dataset_rolling_horizon_comparison.csv` |
| B6 final summary | `Summer 2026 REU/rolling horizon/b6 verification/b6_final_results/David_B6_run_summary.csv` |
| B6 QA summary | `Summer 2026 REU/rolling horizon/b6 verification/b6_final_results/David_B6_QA_summary.csv` |

## Commands

Run from the repository root:

```bash
cd /Users/davidvalenta/deep-wind-model-dispatch
```

Causal ridge forecast and oracle upper bound:

```bash
./venv/bin/python strategy_model/optimization/forecast_backtest_rolling_horizons.py
```

Robustness/statistics:

```bash
./venv/bin/python strategy_model/optimization/analyze_forecast_backtest_robustness.py
```

Scenario dispatch:

```bash
./venv/bin/python strategy_model/optimization/run_uncertainty_aware_dispatch.py \
  --variants single_recourse three_scenario_expected five_scenario_expected seven_scenario_expected ten_scenario_expected \
  --nowcast-first-hour \
  --gate-margin 0.0 \
  --out-dir strategy_model/optimization/uncertainty_aware_dispatch_results
```

B6 verification:

```bash
./venv/bin/python strategy_model/optimization/B6_CANONICAL_RUNNER.py
./venv/bin/python strategy_model/optimization/B6_FINAL_VALIDATE.py
```

## Important Warning

The scenario result, causal forecast backtest, rolling-horizon full-dataset comparison, and B6 verification are separate result sets. Do not mix their numbers unless the paper clearly states which experiment produced each value.

The archived COVE-DV/teacher-student exploratory work now lives in:

```text
strategy_model/optimization/archive/cove_dv_exploratory/
```

