# 100 MW Baseload Code

This folder contains the code for the 2020 100-MW constant-output baseload and
same-year perfect-information oracle checks.

| File | Purpose |
| --- | --- |
| `canonical_benchmark_oracle_runner.py` | Full rebuild runner. It rebuilds the 100-MW baseload hourly CSV and oracle hourly CSVs from the 2020 wind and raw RTM LMP files. |

The main quick reproduction command is run from the parent folder:

```bash
cd ..
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```

For normal reruns, change `../EXPERIMENT_KNOBS.py` first. That file is the
one place for storage power, storage duration, target output, RTE, SoC limits,
initial SoC, year-end SoC, horizons, solver gap, and output folder.

The full rebuild command is:

```bash
../../venv/bin/python code/canonical_benchmark_oracle_runner.py --horizons 24 48 168
```

That command writes full hourly outputs such as:

```text
results/full_rebuild_canonical_2020/constant_output_baseload_100mw_2020_hourly.csv
results/full_rebuild_canonical_2020/oracle_rh_milp_24h_2020_hourly.csv
results/full_rebuild_canonical_2020/oracle_rh_milp_48h_2020_hourly.csv
results/full_rebuild_canonical_2020/oracle_rh_milp_168h_2020_hourly.csv
```

To test a different oracle horizon without using the knobs file:

```bash
../../venv/bin/python code/canonical_benchmark_oracle_runner.py --horizons 248 --out "results/test_248h"
```

To test a different storage setup:

```bash
../../venv/bin/python code/canonical_benchmark_oracle_runner.py --storage-power-mw 100 --storage-duration-h 10 --rte 0.55 --target-output-mw 100 --grid-cap-mw 249 --horizons 48 --out "results/test_100mw_10h"
```

The defaults are the official 2020 benchmark:

```text
storage power = 100 MW
duration = 10 h
capacity = 1000 MWh
minimum SoC = 200 MWh
initial SoC = 600 MWh
RTE = 0.55
grid cap = 249 MW
target output = 100 MW
```
