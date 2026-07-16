# Run Commands For Paper Results

Run these from the repository root:

```bash
cd /Users/davidvalenta/deep-wind-model-dispatch
```

## Causal Ridge Regression + Oracle Upper Bound

This reproduces the reserve-adjusted causal forecast horizons and the oracle
upper-bound horizons. The `--direct-reserve-mw 75` option is the explicit
robustness buffer used to prevent wind forecast underprediction from causing
unnecessary realized curtailment under the strict planned-direct execution rule.

```bash
./venv/bin/python strategy_model/optimization/forecast_backtest_rolling_horizons.py \
  --direct-reserve-mw 75
```

Main outputs:

```text
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_summary.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_24h.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_48h.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_72h.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/forecast_dispatch_168h.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/oracle_dispatch_24h.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/oracle_dispatch_48h.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/oracle_dispatch_72h.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_2014_2023/oracle_dispatch_168h.csv
```

## Robustness And Statistics

This reproduces the year-by-year horizon comparisons and statistical checks.

```bash
./venv/bin/python strategy_model/optimization/analyze_forecast_backtest_robustness.py
```

Main outputs:

```text
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/yearly_horizon_results.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/yearly_win_counts.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/paired_statistical_tests.csv
strategy_model/optimization/rolling_horizon_gurobi_results/forecast_backtest_robustness/forecast_model_comparison.csv
```

## Rolling-Horizon Gurobi

The main Gurobi/MILP solver is:

```text
strategy_model/optimization/rolling_horizon_gurobi_dispatch.py
```

The full-dataset horizon result files are:

```text
strategy_model/optimization/rolling_horizon_gurobi_results/full_dataset_rolling_horizon_comparison.csv
strategy_model/optimization/rolling_horizon_gurobi_results/horizon_comparison_full_43y/rolling_horizon_comparison.csv
strategy_model/optimization/rolling_horizon_gurobi_results/paper_ready_key_results.csv
```

## Different Scenarios

This reproduces the uncertainty-aware scenario dispatch experiment.

```bash
./venv/bin/python strategy_model/optimization/run_uncertainty_aware_dispatch.py \
  --variants single_recourse three_scenario_expected five_scenario_expected seven_scenario_expected ten_scenario_expected \
  --nowcast-first-hour \
  --gate-margin 0.0 \
  --out-dir strategy_model/optimization/uncertainty_aware_dispatch_results
```

Main outputs:

```text
strategy_model/optimization/uncertainty_aware_dispatch_results/uncertainty_aware_summary.csv
strategy_model/optimization/uncertainty_aware_dispatch_results/final_breakthrough_summary.csv
```

## B6 Verification

B6 is not the main paper result. It is the 2020 verification package requested by Chris.

```bash
./venv/bin/python strategy_model/optimization/B6_CANONICAL_RUNNER.py
./venv/bin/python strategy_model/optimization/B6_FINAL_VALIDATE.py
```

Main outputs:

```text
strategy_model/optimization/b6_final_results/David_B6_run_summary.csv
strategy_model/optimization/b6_final_results/David_B6_QA_summary.csv
strategy_model/optimization/b6_final_results/David_B6_frozen_config.json
```
