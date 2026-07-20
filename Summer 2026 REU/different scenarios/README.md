# Different Scenarios

This folder answers the third question:

> Does dispatch improve if Gurobi sees several possible forecast futures instead of one?

Run:

```bash
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

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
```
