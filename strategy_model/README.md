# Strategy Model

This folder is Part 2 of the project: deciding how the wind farm and storage system should dispatch energy.

```text
wind generation + price + battery state -> charge, hold, or discharge
```

## Main Areas

| Folder | Purpose |
| --- | --- |
| `src/` | Original dispatch neural-network code |
| `evaluation/` | Saved COVE summaries |
| `optimization/` | New Gurobi/MILP, COVE-DV, rolling-horizon, and scenario experiments |
| `hp_search_results/` | Hyperparameter search outputs |

Most June 2026 work is under `optimization/`.
