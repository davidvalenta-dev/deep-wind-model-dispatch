# Optimization Experiments

This folder contains the dispatch optimization code and results.

For the final paper-facing organization, start here:

```text
../../Summer 2026 REU/
```

## Current Main Scripts

| Script | Purpose |
| --- | --- |
| `forecast_backtest_rolling_horizons.py` | causal ridge/lag forecast dispatch plus oracle upper-bound horizon test |
| `analyze_forecast_backtest_robustness.py` | year-by-year results, confidence intervals, forecast comparisons, sensitivity checks |
| `rolling_horizon_gurobi_dispatch.py` | main Gurobi/MILP rolling-horizon storage dispatch solver |
| `run_uncertainty_aware_dispatch.py` | scenario-based uncertainty-aware dispatch |
| `run_best_forecast_dispatch_search.py` | supporting forecast search code for scenario experiments |
| `run_nora_matching_forecast_horizons.py` | supporting Nora-style forecast/horizon code |
| `B6_CANONICAL_RUNNER.py` | final frozen 2020 B6 benchmark runner |
| `B6_FINAL_VALIDATE.py` | final B6 validation checks |

## Current Main Result Folders

| Folder | Meaning |
| --- | --- |
| `rolling_horizon_gurobi_results/forecast_backtest_2014_2023/` | causal forecast and oracle upper-bound dispatch results |
| `rolling_horizon_gurobi_results/forecast_backtest_robustness/` | yearly robustness and statistical checks |
| `rolling_horizon_gurobi_results/horizon_comparison_full_43y/` | rolling-horizon comparison outputs |
| `uncertainty_aware_dispatch_results/` | scenario dispatch result |
| `b6_final_results/` | frozen 2020 B6 verification package |
| `archive/cove_dv_exploratory/` | older COVE-DV and teacher-student exploratory work |

## Constraint Summary

The main Gurobi model includes storage bounds, charge/discharge limits, no simultaneous charge/discharge, wind-only charging, grid export cap, delivered-power balance, chronological SoC carryover, and N+1 SoC indexing where applicable.

