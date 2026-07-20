# Step 3 Scenario Code

This folder contains the code for uncertainty-aware scenario dispatch.

| File | Purpose |
| --- | --- |
| `run_uncertainty_aware_dispatch.py` | Full scenario Gurobi runner. Defaults to the official 48-hour, current-hour nowcast, 1/3/5/7/10 scenario setup. |
| `run_nora_matching_forecast_horizons.py` | Shared forecast and Nora/Chris storage-constraint helper. |
| `run_best_forecast_dispatch_search.py` | Shared revenue/COVE summary helper. |

The main quick reproduction command is:

```bash
../RUN_3_SCENARIO_COMPARISON.py
```

The full Gurobi rebuild command is:

```bash
../../venv/bin/python code/run_uncertainty_aware_dispatch.py
```

The full rebuild is slower because it reruns Gurobi for every hourly scenario decision.
