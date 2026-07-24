# Summer 2026 REU

This folder is organized as a research ladder plus benchmark checks. Each
folder has one command to run and one obvious settings file named
`EXPERIMENT_KNOBS.py`. Edit that knobs file first, then run the folder's
`RUN_*.py` script to rerun the experiment with the new settings.

Each command produces its own printed table and figures.
Each dispatch folder also includes full hourly CSV outputs under `results/`,
so reviewers can inspect every charge, discharge, delivered-power, curtailment,
and SoC value rather than only reading the summary table.

## Folder Map

| Folder | Purpose | Command |
| --- | --- | --- |
| `100 MW baseload` | 2020 benchmark plus 2014-2023 paper-period 100 MW constant-output reference | `../../venv/bin/python RUN_0_100MW_BASELOAD.py` |
| `causal ridge regression` | Compare forecast models using RMSE | `../../venv/bin/python RUN_1_FORECAST_RMSE.py` |
| `rolling horizon` | Compare Gurobi horizons using the causal ridge forecast | `../../venv/bin/python RUN_2_ROLLING_HORIZON.py` |
| `different scenarios` | Compare single forecast vs 3/5/7/10 scenarios | `../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py` |
| `oracle upper bound` | Compare perfect-future Gurobi horizons | `../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py` |
| `b6 verification` | Separate 2020 frozen verification packet | See `b6 verification/code` |

## How To Change A Run

Use this same pattern in every folder:

```text
1. Open EXPERIMENT_KNOBS.py.
2. Change the setting you care about.
3. Run the folder's RUN_*.py script.
4. Read the new output in results/current_run_from_knobs/.
```

Examples:

| Change you want | Folder | Knob to edit |
| --- | --- | --- |
| Test a 35-hour rolling horizon | `rolling horizon` | `HORIZONS = [35]` |
| Test a 35-hour oracle horizon | `oracle upper bound` | `HORIZONS = [35]` |
| Change battery starting SoC | dispatch folders | `INITIAL_SOC_MWH = ...` |
| Change storage duration | dispatch folders | `STORAGE_DURATION_H = ...` |
| Quick scenario test | `different scenarios` | `MAX_ORIGINS = 168` |

Leave `MAX_ORIGINS = None` for the full scenario run.

## Main Story

The 100 MW baseload folder is the rule-based benchmark: try to deliver 100 MW
every hour using wind plus storage. It has two uses. First, it keeps the 2020
B6/canonical check. Second, it now builds a 2014-2023 100 MW paper-period
reference so rolling horizon, scenario dispatch, and oracle results can also be
compared against the same constant-output rule. After that, the causal ridge
forecast is checked against other prediction methods. Then that forecast is
used inside Gurobi with rolling-horizon dispatch. Scenario dispatch adds
several possible forecast futures so the controller is less dependent on one
predicted path. The oracle folder is separate: it shows the perfect-future
ceiling, not a deployable method.

## Best Results

| Step | Best result |
| --- | ---: |
| 100 MW baseload, 2020 | $9.09M revenue; COVE 5.655; 0 QA violations |
| 100 MW baseload, 2014-2023 | $211.77M raw revenue; normalized revenue metric 5.99M |
| B6 vs 100 MW baseload | C causal: -7.62% revenue; C oracle: +47.36% revenue |
| Forecast model | Causal lag / ridge-style forecast, 21.24 MW RMSE |
| Rolling horizon | 48-hour horizon, 0.95% COVE improvement vs baseload |
| Scenario dispatch | 3 scenarios, 23.19% COVE improvement vs baseload |
| Oracle upper bound | 168-hour perfect-information case, 26.21% COVE improvement vs baseload |

When comparing against the explicit 2014-2023 100 MW constant-output baseload,
the best rolling-horizon case has a 20.63% COVE reduction on the normalized
price metric, and the best scenario case has a 40.18% COVE reduction on the raw
LMP revenue metric. These are reported separately because the two result
families use different price scales.

See `RUN_COMMANDS.md` for exact commands and figure names.
