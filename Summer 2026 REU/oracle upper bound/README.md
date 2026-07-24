# Oracle Upper Bound

This folder answers the ceiling question:

> How good could dispatch be if Gurobi knew the future perfectly?

Run:

```bash
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

Before running, change all experiment settings in:

```text
EXPERIMENT_KNOBS.py
```

That file controls oracle horizons, storage power, storage duration, grid cap,
initial SoC, min/max SoC fractions, and the output folder. For example, to test
a 35-hour oracle horizon, set `HORIZONS = [35]`.

The oracle case gives Gurobi realized future wind and realized future price. This is not a realistic controller because real operators do not know the future exactly. It is included as an upper bound for comparison.

Main result:

```text
24 h oracle:  23.97% COVE improvement
48 h oracle:  25.89% COVE improvement
72 h oracle:  26.18% COVE improvement
168 h oracle: 26.21% COVE improvement
```

The best oracle case is the 168-hour perfect-future horizon. It uses the same common 100 MW / 10-hour CAES setup as the rolling-horizon folder, so maximum SoC is 1000 MWh.

Generated figures:

```text
figures/step4_oracle_improvement_by_horizon.png
figures/step4_oracle_cove_by_horizon.png
figures/step4_oracle_runtime_value_tradeoff.png
figures/step4_3d_oracle_revenue_cove.png
```

Fresh rerun outputs go here:

```text
results/current_run_from_knobs/
```

Official hourly oracle outputs from the frozen result are stored here:

```text
results/full_hourly_outputs/oracle_dispatch_24h.csv
results/full_hourly_outputs/oracle_dispatch_48h.csv
results/full_hourly_outputs/oracle_dispatch_72h.csv
results/full_hourly_outputs/oracle_dispatch_168h.csv
```

## Code In This Folder

| File | What it does |
| --- | --- |
| `RUN_4_ORACLE_UPPER_BOUND.py` | Main command for the oracle upper-bound table and figures. Reruns the oracle Gurobi backtest from `EXPERIMENT_KNOBS.py`. |
| `code/build_oracle_summary.py` | Extracts the perfect-future oracle rows from the rolling-horizon result table. |
| `code/forecast_backtest_rolling_horizons.py` | Full configurable oracle/forecast Gurobi runner. Use `--oracle-only` to rebuild oracle hourly CSVs. |
| `code/rolling_horizon_gurobi_dispatch.py` | The actual lower-level Gurobi/MILP dispatch model and constraints. |

You usually do not need a long terminal command anymore. Prefer changing
`EXPERIMENT_KNOBS.py`, then running `RUN_4_ORACLE_UPPER_BOUND.py`.

Full direct oracle rebuild command, if you want to bypass the knobs file:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --oracle-only --horizons 24 48 72 168 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/full_rebuild_oracle_2014_2023"
```

Example custom oracle rerun:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --oracle-only --horizons 248 --out-dir "results/oracle_248h"
```

In oracle mode, that script gives each planning window the actual future wind
and price instead of forecasted values.
