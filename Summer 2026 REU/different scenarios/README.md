# Different Scenarios

This folder answers the third question:

> Does dispatch improve if Gurobi sees several possible forecast futures instead of one?

Run:

```bash
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

Before running, change all experiment settings in:

```text
EXPERIMENT_KNOBS.py
```

That file controls horizon length, scenario variants, storage power, storage
duration, RTE, DoD, initial SoC, grid cap, calibration mode, and output folder.
Leave `MAX_ORIGINS = None` for the full 2014-2023 run, or set it to something
small like `168` for a quick test.

The script compares baseload, single-forecast dispatch, and 3/5/7/10 scenario dispatch. This is the third step of the ladder: it keeps the causal ridge forecast and 48-hour Gurobi lookahead, then adds multiple possible futures and hourly replanning.

Main result:

```text
Single forecast: 19.40% COVE reduction vs baseload
3 scenarios:     23.19% COVE reduction vs baseload
5 scenarios:     23.01% COVE reduction vs baseload
7 scenarios:     23.03% COVE reduction vs baseload
10 scenarios:    20.47% COVE reduction vs baseload
```

The best case is three scenarios. Five and seven scenarios are very close, while ten scenarios performed worse because it became too conservative.

Generated figures:

```text
figures/step3_scenario_cove_improvement.png
figures/step3_scenario_revenue_gain.png
figures/step3_revenue_cove_tradeoff.png
figures/step3_ladder_revenue_progression.png
figures/step3_3d_scenario_revenue_cove.png
```

Fresh rerun outputs go here:

```text
results/current_run_from_knobs/
```

Official hourly outputs from the frozen result are stored here:

```text
results/scenario_48h_full_ladder/single_forecast_recourse_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/three_scenario_expected_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/five_scenario_expected_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/seven_scenario_expected_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/ten_scenario_expected_nowcast_gated_labels.csv
```

## Code In This Folder

| File | What it does |
| --- | --- |
| `RUN_3_SCENARIO_COMPARISON.py` | Main command for Step 3. Reruns scenario Gurobi dispatch from `EXPERIMENT_KNOBS.py`, prints the table, and regenerates figures. |
| `code/run_uncertainty_aware_dispatch.py` | Full scenario experiment runner. Defaults to the official 48-hour, nowcast-first-hour, 1/3/5/7/10 scenario setup. |
| `code/run_nora_matching_forecast_horizons.py` | Shared forecast and Nora/Chris storage-constraint helper used by the scenario runner. |
| `code/run_best_forecast_dispatch_search.py` | Helper functions for revenue/COVE summaries and forecast candidate accounting. |

You usually do not need a long terminal command anymore. Prefer changing
`EXPERIMENT_KNOBS.py`, then running `RUN_3_SCENARIO_COMPARISON.py`.

Full direct rebuild command, if you want to bypass the knobs file:

```bash
../../venv/bin/python code/run_uncertainty_aware_dispatch.py
```

Example custom reruns:

```bash
../../venv/bin/python code/run_uncertainty_aware_dispatch.py --variants seven_scenario_expected --out-dir "results/test_7_scenarios"
../../venv/bin/python code/run_uncertainty_aware_dispatch.py --horizon-hours 72 --variants single_recourse three_scenario_expected five_scenario_expected --out-dir "results/test_72h_scenarios"
../../venv/bin/python code/run_uncertainty_aware_dispatch.py --storage-power-mw 100 --storage-duration-h 10 --rte 0.55 --grid-cap-mw 249 --out-dir "results/test_100mw_10h_scenarios"
```

`RUN_3_SCENARIO_COMPARISON.py` now performs the full rebuild itself. It can be slow because it reruns Gurobi for all hourly scenario decisions.
