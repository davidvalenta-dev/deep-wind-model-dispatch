# Rolling Horizon

This folder answers the second question:

> Once we have causal forecasts, how far should Gurobi look ahead?

Run:

```bash
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

The script compares 24, 48, 72, and 168-hour causal forecast horizons against baseload.

Main result:

```text
24 h:  3.31% COVE improvement
48 h:  6.25% COVE improvement
72 h:  6.06% COVE improvement
168 h: 5.44% COVE improvement
```

The best realistic case is the 48-hour planning horizon. In this setup, ridge predicts the next 48 hours, Gurobi optimizes those 48 hours, only the first 24 hours are executed, and then the process repeats.

Generated figures:

```text
figures/step2_causal_horizon_improvement.png
figures/step2_causal_horizon_cove.png
```

