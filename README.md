# Forecast-Aware Wind-Storage Dispatch

This repository contains the frozen Summer 2026 REU experiment for causal
wind-power forecasting and constrained rolling-horizon dispatch. The
paper-facing package is [`Summer 2026 REU/`](Summer%202026%20REU/).

## Frozen Experiment

All dispatch cases use one common configuration:

| Setting | Frozen value |
| --- | ---: |
| Evaluation period | 2014-01-01 00:00 through 2023-12-23 05:00 |
| Evaluated hours | 87,417 |
| Storage | 100 MW / 10 h CAES-equivalent system |
| Capacity and SoC bounds | 1,000 MWh; 200-1,000 MWh |
| Initial, completed year-end, and final SoC | 600 MWh |
| Efficiency | 0.55, applied on discharge |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |
| Realized execution and replanning | 1 hour / 1 hour |
| Primary benchmark | 100-MW Constant-Output Baseload Benchmark |

The SoC is chronological. Year-end targets are reached physically; the code
does not reset the battery or create energy between years.

## Step 0-4 Ladder

| Step | Experiment | Frozen conclusion |
| ---: | --- | --- |
| 0 | 100 MW constant-output benchmark | Revenue metric 5,962,774.41; COVE 8.622953 |
| 1 | Forecast comparison | Causal lag/ridge wins with 21.24 MW RMSE |
| 2 | Deterministic horizon sweep | 168 h wins with 35.37% COVE reduction |
| 3 | Scenario-count sweep | One forecast wins; best multi-scenario case is 10 futures at 34.60% |
| 4 | Rolling-window Oracle | 168 h ceiling gives 40.84% COVE reduction |

The Step 2 168-hour result and Step 3 one-forecast result are exactly equal.
That controlled equality proves the scenario experiment changes scenario count
without silently changing the forecast, controller, or execution protocol.

## Run

Each step has one runner and one `EXPERIMENT_KNOBS.py` file:

```bash
cd "Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py

cd "../causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py

cd "../rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py

cd "../different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py

cd "../oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

The committed knobs already set `RERUN_FROM_SOURCE = False`, so these commands
display the frozen CSVs and regenerate every current figure without solving the
experiments again. Set it to `True` only for an intentional full reproduction.

## Verification

```bash
./venv/bin/python "Summer 2026 REU/common/validate_controlled_ladder.py"
cd "Summer 2026 REU"
../venv/bin/python AUDIT_DATA_CONFIG.py
```

The final validation status is `PASS`: 14/14 controlled hourly files satisfy
the common storage configuration, every dispatch row has zero physical QA
violations, and all annual/final SoC checks pass at 600 MWh.

Canonical values and source files are listed in
[`PAPER_RESULT_FILE_MAP.md`](Summer%202026%20REU/PAPER_RESULT_FILE_MAP.md).
Exact commands are listed in
[`RUN_COMMANDS.md`](Summer%202026%20REU/RUN_COMMANDS.md).

The paper-facing package includes 34 regenerated figures in a consistent,
restrained visual style. The complete chart list and meaning of each figure are
in [`FIGURE_INDEX.md`](Summer%202026%20REU/FIGURE_INDEX.md). To rebuild all
figures from the frozen CSVs without rerunning Gurobi:

```bash
./venv/bin/python "Summer 2026 REU/common/regenerate_all_figures.py" --step all
```
