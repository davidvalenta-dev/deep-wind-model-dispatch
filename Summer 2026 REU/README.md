# Summer 2026 REU

This folder is the clean reproduction ladder for the Summer 2026 hybrid
wind-storage dispatch work. Each major result has its own folder, its own
`EXPERIMENT_KNOBS.py` settings file, and one front-door `RUN_*.py` command.

The primary benchmark is now the **100-MW Constant-Output Baseload Benchmark**.
That means every Step 2, Step 3, and Step 4 table reports COVE gain and revenue
gain against the rule-based 100 MW wind-storage benchmark first. The wind-only
case is still printed, but only as secondary reference information.

## Common Storage Configuration

All paper-facing Summer 2026 runs use the same CAES-equivalent setup:

| Setting | Value |
| --- | ---: |
| Storage power | 100 MW charge / 100 MW discharge |
| Storage duration | 10 h |
| Energy capacity | 1,000 MWh |
| Minimum SoC | 200 MWh |
| Maximum SoC | 1,000 MWh |
| Initial SoC | 600 MWh |
| RTE convention | 55%, applied on discharge |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |

## Folder Map

| Step | Folder | Purpose | Command |
| ---: | --- | --- | --- |
| 0 | `100 MW baseload` | Build the primary 100 MW benchmark and same-year oracle checks | `../../venv/bin/python RUN_0_100MW_BASELOAD.py` |
| 1 | `causal ridge regression` | Compare forecast models by RMSE | `../../venv/bin/python RUN_1_FORECAST_RMSE.py` |
| 2 | `rolling horizon` | Deterministic Forecast-Driven Rolling-Horizon MILP | `../../venv/bin/python RUN_2_ROLLING_HORIZON.py` |
| 3 | `different scenarios` | Scenario-Based Rolling-Horizon MILP | `../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py` |
| 4 | `oracle upper bound` | Perfect-Information Oracle Rolling-Horizon MILP | `../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py` |
| QA | `audit` | Data/config audit written by `AUDIT_DATA_CONFIG.py` | `../venv/bin/python AUDIT_DATA_CONFIG.py` |

## How To Change A Run

Use the same pattern in every folder:

```text
1. Open EXPERIMENT_KNOBS.py.
2. Change the setting you care about.
3. Run that folder's RUN_*.py script.
4. Read the new output in results/current_run_from_knobs/.
```

Examples:

| Change you want | Folder | Knob |
| --- | --- | --- |
| Test a 35-hour deterministic horizon | `rolling horizon` | `HORIZONS = [35]` |
| Test a 35-hour oracle horizon | `oracle upper bound` | `HORIZONS = [35]` |
| Change starting SoC | dispatch folders | `INITIAL_SOC_MWH = ...` |
| Change storage duration | dispatch folders | `STORAGE_DURATION_H = ...` |
| Quick scenario test | `different scenarios` | `MAX_ORIGINS = 168` |

Leave `MAX_ORIGINS = None` for the full scenario run.

## Current Results

These are the current rerun outputs using the common 100 MW / 10 h CAES setup.

| Step | Main result |
| --- | --- |
| Step 0 | 100 MW benchmark, 2014-2023 normalized revenue metric `5,981,942.95`; COVE `8.595322` for the Step 2/4 daily period |
| Step 1 | Best forecast: causal lag/ridge forecast, RMSE `21.24 MW` |
| Step 2 | Best deterministic case: 48 h horizon, `20.63%` COVE gain vs 100 MW benchmark |
| Step 3 | Best scenario case: 3 scenarios, `40.18%` COVE gain and `67.16%` revenue gain vs 100 MW benchmark |
| Step 4 daily oracle | Best daily-replan oracle: 168 h, `40.87%` COVE gain vs 100 MW benchmark |
| Step 4 hourly oracle | Separate 168 h hourly-replan oracle ceiling: `40.85%` COVE gain vs 100 MW benchmark |

Wind-only is still shown at the bottom of Step 2, Step 3, and Step 4 output.
It is useful context, but it is not the primary benchmark anymore.

## Terminology

| New term | Meaning |
| --- | --- |
| 100-MW Constant-Output Baseload Benchmark | Rule-based storage benchmark that tries to deliver 100 MW each hour |
| Wind-only baseline | No storage; actual wind goes directly to grid up to the 249 MW cap |
| Deterministic Forecast-Driven Rolling-Horizon MILP | One forecast path goes into Gurobi |
| Scenario-Based Rolling-Horizon MILP | Multiple plausible futures go into Gurobi with shared first action |
| H-hour Perfect-Information Oracle Rolling-Horizon MILP | Gurobi sees actual future wind and price for H hours |
| Full-Horizon Oracle MILP | Perfect-future full-period reference, used only as a theoretical ceiling if reported |

## QA

Run this from inside `Summer 2026 REU`:

```bash
../venv/bin/python AUDIT_DATA_CONFIG.py
```

Current audit result:

```text
Audited hourly files: 16
Passed common 100 MW / 10 h checks: 16/16
```

The audit CSV is:

```text
audit/summer_2026_reu_data_config_audit.csv
```

See `RUN_COMMANDS.md` for exact commands and output locations.
