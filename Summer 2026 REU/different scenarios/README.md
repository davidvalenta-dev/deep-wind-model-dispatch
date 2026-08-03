# Different Scenarios

This folder answers:

> Does dispatch improve if Gurobi sees several possible forecast futures instead of one?

Primary benchmark: **100-MW Constant-Output Baseload Benchmark**.
Secondary reference: wind-only/no-storage.

Run:

```bash
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

Change settings in:

```text
EXPERIMENT_KNOBS.py
```

Current scenario setup:

```text
48 h lookahead
100 MW / 10 h CAES
1,000 MWh capacity
200-1,000 MWh SoC bounds
249 MW grid export cap
1, 3, 5, 7, and 10 forecast futures
```

Current result versus the 100 MW benchmark:

| Method | Revenue | Revenue gain | COVE | COVE reduction |
| --- | ---: | ---: | ---: | ---: |
| 1 forecast | $337,322,348.04 | 59.31% | 0.173884 | 37.23% |
| 3 scenarios | $353,949,333.45 | 67.16% | 0.165716 | 40.18% |
| 5 scenarios | $353,117,910.43 | 66.77% | 0.166106 | 40.04% |
| 7 scenarios | $353,220,656.50 | 66.82% | 0.166058 | 40.05% |
| 10 scenarios | $341,858,797.71 | 61.45% | 0.171577 | 38.06% |

Highest reported scenario case: **3 scenarios**. The 3-, 5-, and 7-scenario
cases are very close, so this should be described as the highest reported
case in the current QA-updated run, not as a universal best scenario count.

Important: the `1 forecast` row here is the fair point-forecast reference for
the scenario experiment. It is not the same as the Step 2 `48 h` deterministic
result. Step 3 uses current-hour nowcast, nowcast-gated recourse, and
first-action execution logic inside the scenario runner.

Wind-only is printed at the bottom of the command output only as secondary
reference.

Important files:

| File | Purpose |
| --- | --- |
| `RUN_3_SCENARIO_COMPARISON.py` | Main Step 3 command |
| `EXPERIMENT_KNOBS.py` | One place to change scenario count/horizon/storage/output settings |
| `code/run_uncertainty_aware_dispatch.py` | Full scenario Gurobi runner |
| `results/current_run_from_knobs/scenario_summary_vs_wind_only_and_100mw.csv` | Current enriched summary |
| `results/current_run_from_knobs/three_scenario_expected_nowcast_gated_labels.csv` | Best scenario hourly CSV |

Figures:

```text
figures/step3_scenario_cove_improvement.png
figures/step3_scenario_revenue_gain.png
figures/step3_revenue_cove_tradeoff.png
figures/step3_ladder_revenue_progression.png
figures/step3_3d_scenario_revenue_cove.png
```
