# Oracle Upper Bound

This folder answers:

> How good could dispatch be if Gurobi knew the future perfectly?

Primary benchmark: **100-MW Constant-Output Baseload Benchmark**.
Secondary reference: wind-only/no-storage.

Run:

```bash
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

Change settings in:

```text
EXPERIMENT_KNOBS.py
```

The command prints two oracle views:

1. Daily-replan oracle: solve H hours, execute 24 hours, then replan.
2. Hourly-replan oracle ceiling: solve 168 hours, execute 1 hour, then replan.

Current daily-replan oracle result versus the 100 MW benchmark:

| Horizon | COVE | COVE gain | Revenue metric | Raw revenue gain |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 5.236266 | 39.08% | 9,819,350.07 | 64.23% |
| 48 h | 5.104091 | 40.62% | 10,073,630.57 | 71.58% |
| 72 h | 5.084378 | 40.85% | 10,112,687.75 | 70.82% |
| 168 h | 5.082358 | 40.87% | 10,116,705.90 | 72.07% |

Separate hourly-replan oracle ceiling:

| Horizon | COVE | COVE gain | Revenue metric | Raw revenue gain |
| ---: | ---: | ---: | ---: | ---: |
| 168 h | 5.076786 | 40.85% | 10,127,810.67 | 71.94% |

Wind-only is printed at the bottom of each command block only as secondary
reference.

Important files:

| File | Purpose |
| --- | --- |
| `RUN_4_ORACLE_UPPER_BOUND.py` | Main Step 4 command |
| `EXPERIMENT_KNOBS.py` | One place to change oracle horizons/storage/output settings |
| `code/forecast_backtest_rolling_horizons.py` | Oracle/forecast Gurobi runner |
| `results/current_run_from_knobs/oracle_upper_bound_summary.csv` | Current daily oracle summary |
| `results/current_run_from_knobs/oracle_dispatch_168h.csv` | Daily 168 h oracle hourly CSV |
| `results/hourly_168h_oracle_ceiling/oracle_dispatch_168h.csv` | Hourly 168 h oracle ceiling hourly CSV |

Figures:

```text
figures/step4_oracle_improvement_by_horizon.png
figures/step4_oracle_cove_by_horizon.png
figures/step4_oracle_runtime_value_tradeoff.png
figures/step4_daily_vs_hourly_oracle_gain.png
figures/step4_oracle_daily_hourly_revenue_cove.png
```
