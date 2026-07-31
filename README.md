# Deep Wind Model Dispatch

This repository contains Summer 2026 REU work on forecast-aware dispatch for a
hybrid wind farm with compressed-air-energy-storage-like constraints. The clean
paper-facing reproduction package is organized here:

[`Summer 2026 REU/`](Summer%202026%20REU/)

The project is now organized around one primary benchmark:

```text
100-MW Constant-Output Baseload Benchmark
```

Wind-only/no-storage output is still reported, but only as secondary reference
information. The 100 MW benchmark uses the same 100 MW / 10 h / 1,000 MWh CAES
configuration as the dispatch experiments.

## Reproduction Ladder

Run one command in each folder:

| Step | Folder | What it proves |
| ---: | --- | --- |
| 0 | `Summer 2026 REU/100 MW baseload` | Builds the 100 MW benchmark and QA checks |
| 1 | `Summer 2026 REU/causal ridge regression` | Chooses the best power forecast by RMSE |
| 2 | `Summer 2026 REU/rolling horizon` | Tests deterministic Gurobi planning horizons |
| 3 | `Summer 2026 REU/different scenarios` | Tests 1/3/5/7/10 forecast scenarios |
| 4 | `Summer 2026 REU/oracle upper bound` | Reports daily and hourly perfect-future oracle ceilings |

Every folder has:

```text
EXPERIMENT_KNOBS.py
RUN_*.py
code/
results/
figures/
```

Change the knobs file, run the `RUN_*.py` command, then read
`results/current_run_from_knobs/`.

## Current Paper-Facing Results

| Result | Current value |
| --- | ---: |
| Best forecast model | causal lag/ridge forecast |
| Best forecast RMSE | 21.24 MW |
| Best deterministic rolling-horizon case | 48 h |
| Deterministic COVE gain vs 100 MW benchmark | 20.63% |
| Best scenario case | 3 scenarios |
| Scenario COVE gain vs 100 MW benchmark | 40.18% |
| Scenario revenue gain vs 100 MW benchmark | 67.16% |
| Daily-replan oracle ceiling | 168 h, 40.87% COVE gain |
| Hourly-replan oracle ceiling | 168 h, 40.85% COVE gain |

## Common Storage Setup

| Setting | Value |
| --- | ---: |
| Storage power | 100 MW |
| Duration | 10 h |
| Capacity | 1,000 MWh |
| SoC bounds | 200-1,000 MWh |
| Initial SoC | 600 MWh |
| RTE | 55%, discharge-side |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |

## Main Commands

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

Run the audit:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU"
../venv/bin/python AUDIT_DATA_CONFIG.py
```

Current audit result: `16/16` active hourly CSV files pass the common 100 MW /
10 h CAES checks.
