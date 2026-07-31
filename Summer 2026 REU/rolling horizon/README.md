# Rolling Horizon

This folder answers:

> Once the forecast is selected, how far should Gurobi look ahead?

Primary benchmark: **100-MW Constant-Output Baseload Benchmark**.
Secondary reference: wind-only/no-storage.

Run:

```bash
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

Change settings in:

```text
EXPERIMENT_KNOBS.py
```

Current common setup:

```text
100 MW storage power
10 h duration
1,000 MWh capacity
200-1,000 MWh SoC bounds
600 MWh initial SoC
249 MW grid export cap
75 MW direct reserve
```

Current result versus the 100 MW benchmark:

| Horizon | COVE | COVE gain | Revenue metric | Raw revenue gain |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 6.966281 | 18.95% | 7,380,799.56 | 22.16% |
| 48 h | 6.822045 | 20.63% | 7,536,849.56 | 26.08% |
| 72 h | 6.830033 | 20.54% | 7,528,034.19 | 25.80% |
| 168 h | 6.847708 | 20.33% | 7,508,603.24 | 25.35% |

Best deterministic case: **48 h**.

Wind-only is printed at the bottom of the command output only as secondary
reference.

Important files:

| File | Purpose |
| --- | --- |
| `RUN_2_ROLLING_HORIZON.py` | Main Step 2 command |
| `EXPERIMENT_KNOBS.py` | One place to change horizons/storage/output settings |
| `code/forecast_backtest_rolling_horizons.py` | Builds forecasts, calls Gurobi, writes hourly CSVs |
| `code/rolling_horizon_gurobi_dispatch.py` | Lower-level Gurobi/MILP dispatch engine |
| `results/current_run_from_knobs/forecast_dispatch_summary.csv` | Current summary |
| `results/current_run_from_knobs/forecast_dispatch_48h.csv` | Best deterministic hourly CSV |

Figures:

```text
figures/step2_causal_horizon_improvement.png
figures/step2_causal_horizon_cove.png
figures/step2_revenue_by_horizon.png
```
