# Step 3 Scenario Code

This folder contains the code for uncertainty-aware scenario dispatch.

| File | Purpose |
| --- | --- |
| `run_uncertainty_aware_dispatch.py` | Full scenario Gurobi runner. Defaults to the official 48-hour, current-hour nowcast, 1/3/5/7/10 scenario setup and writes one hourly label CSV per scenario method. |
| `run_nora_matching_forecast_horizons.py` | Shared forecast and Nora/Chris storage-constraint helper. |
| `run_best_forecast_dispatch_search.py` | Shared revenue/COVE summary helper. |

The main quick reproduction command is run from the parent folder:

```bash
cd ..
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

For normal reruns, change `../EXPERIMENT_KNOBS.py` first. That file is the
one place for horizon length, scenario variants, storage power, storage
duration, RTE, DoD, initial SoC, grid cap, calibration mode, quick-run limit,
and output folder.

The full Gurobi rebuild command is:

```bash
../../venv/bin/python code/run_uncertainty_aware_dispatch.py
```

That command writes full hourly outputs such as:

```text
results/scenario_48h_full_ladder/single_forecast_recourse_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/three_scenario_expected_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/five_scenario_expected_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/seven_scenario_expected_nowcast_gated_labels.csv
results/scenario_48h_full_ladder/ten_scenario_expected_nowcast_gated_labels.csv
```

To test only one scenario count without using the knobs file:

```bash
../../venv/bin/python code/run_uncertainty_aware_dispatch.py --variants seven_scenario_expected --out-dir "results/test_7_scenarios"
```

To test a different horizon:

```bash
../../venv/bin/python code/run_uncertainty_aware_dispatch.py --horizon-hours 72 --variants single_recourse three_scenario_expected five_scenario_expected --out-dir "results/test_72h_scenarios"
```

To test a different storage setup:

```bash
../../venv/bin/python code/run_uncertainty_aware_dispatch.py --storage-power-mw 100 --storage-duration-h 10 --rte 0.55 --grid-cap-mw 249 --out-dir "results/test_100mw_10h_scenarios"
```

The full rebuild is slower because it reruns Gurobi for every hourly scenario decision.
