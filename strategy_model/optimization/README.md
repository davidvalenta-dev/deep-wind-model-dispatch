# Optimization Experiments

This folder contains the new dispatch research work from June 2026.

## What This Folder Does

The optimization code answers:

```text
Given wind generation, electricity price, and storage limits, what should the battery do each hour?
```

The main answer is produced by Gurobi mixed-integer optimization. COVE-DV is the neural-network student trained from Gurobi/MILP teacher decisions.

## Important Scripts

| Script | Purpose |
| --- | --- |
| `rolling_horizon_gurobi_dispatch.py` | Main constrained chronological Gurobi rolling-horizon dispatch model |
| `compare_rolling_horizons.py` | Compares 24/48/72/168-hour perfect-information horizons |
| `forecast_backtest_rolling_horizons.py` | Tests forecast-driven rolling-horizon dispatch on unseen years |
| `analyze_forecast_backtest_robustness.py` | Builds yearly stats, confidence intervals, and sensitivity checks |
| `train_cove_dv_chronological.py` | Trains the COVE-DV neural student on chronological teacher labels |
| `milp_teacher_dispatch.py` | Earlier MILP teacher label experiment |

## Result Folders

| Folder | Meaning |
| --- | --- |
| `nora_weekly_comparison_2020_jan06_caes100mw10h_raw_lmp/` | One-week Nora/MATLAB comparison figures and tables |
| `rolling_horizon_gurobi_results/` | Full-data Gurobi and forecast-driven horizon results |
| `uncertainty_aware_dispatch_results/` | Scenario-based uncertainty-aware dispatch result |
| `proxy_validation_results/` | New public proxy data validation result |
| `cove_dv_results/` | COVE-DV teacher-student result table |
| `cove_dv_figures/` | COVE-DV figures |
| `cove_dv_nora_chronological_figures/` | Chronological COVE-DV figures using Nora-style constraints |

## Constraint Summary

The main Gurobi model includes storage bounds, charge/discharge limits, no simultaneous charge/discharge, wind-only charging, grid export cap, delivered-power balance, chronological SoC carryover, and N+1 SoC indexing where the terminal state is after the last optimized hour.
