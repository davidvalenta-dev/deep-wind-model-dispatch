# Causal Ridge Regression

This folder answers the first question:

> Which forecast method should feed the dispatch optimizer?

Run:

```bash
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

The script compares forecast methods using RMSE, MAE, and bias. Lower RMSE means the predicted power was closer to the actual measured power.

Main result:

```text
Causal lag / ridge-style forecast RMSE = 21.24 MW
Lag-1 persistence RMSE = 23.60 MW
Speed-to-power curve RMSE = 41.86 MW
RNN RMSE = 46.21 MW
```

This step does not have COVE improvement because no energy dispatch happens yet. It only chooses the forecast signal used by the Gurobi dispatch steps.

Generated figure:

```text
figures/step1_forecast_rmse_comparison.png
```
