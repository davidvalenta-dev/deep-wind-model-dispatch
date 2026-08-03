# Oracle Upper-Bound Code

This folder contains the code for the perfect-information upper-bound step.

| File | Purpose |
| --- | --- |
| `build_oracle_summary.py` | Extracts the oracle rows from the Step 2 rolling-horizon result table and writes the oracle-only summary. |
| `forecast_backtest_rolling_horizons.py` | Full configurable Gurobi runner. Use `--oracle-only` to write oracle hourly CSVs for any horizon list. |
| `rolling_horizon_gurobi_dispatch.py` | Lower-level Gurobi/MILP dispatch model with storage constraints. |
| `dataset.py`, `model.py`, `storage.py`, `util.py` | Local helper modules needed by the copied Gurobi/storage code. |

The main quick reproduction command is run from the parent folder:

```bash
cd ..
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

For normal reruns, change `../EXPERIMENT_KNOBS.py` first. That file is the
one place for oracle horizons, storage power, storage duration, grid cap,
initial SoC, min/max SoC, solver gap, and output folder.

The full oracle rebuild command is:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --oracle-only --horizons 24 48 72 168 --storage-power-mw 100 --storage-duration-h 10 --grid-cap-mw 249 --out-dir "results/full_rebuild_oracle_2014_2023"
```

That command writes full hourly outputs such as:

```text
results/full_rebuild_oracle_2014_2023/oracle_dispatch_24h.csv
results/full_rebuild_oracle_2014_2023/oracle_dispatch_48h.csv
results/full_rebuild_oracle_2014_2023/oracle_dispatch_72h.csv
results/full_rebuild_oracle_2014_2023/oracle_dispatch_168h.csv
```

To test a different oracle horizon without using the knobs file:

```bash
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --oracle-only --horizons 248 --out-dir "results/oracle_248h"
```

In oracle mode, the script uses realized future wind and realized future price
inside each planning horizon. That is why the oracle result is not realistic:
it is a benchmark showing the highest possible improvement under the same
storage constraints.
