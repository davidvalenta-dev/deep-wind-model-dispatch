# Causal Ridge Regression

This folder answers the first question:

> Which forecast method should feed the dispatch optimizer?

Run:

```bash
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

Before running, change all experiment settings in:

```text
EXPERIMENT_KNOBS.py
```

That file controls the forecast dataset, ridge alpha, comparison forecast file,
and output folder.

The script compares forecast methods using RMSE, MAE, and bias. Lower RMSE means the predicted power was closer to the actual measured power.

That one command rebuilds the causal lag/ridge forecast from
`EXPERIMENT_KNOBS.py`, recomputes the RMSE comparison table, and regenerates
the figures. Frozen rerun outputs go to `results/frozen_controlled/` by
default.

Main result:

```text
Causal lag / ridge-style forecast RMSE = 21.24 MW
Lag-1 persistence RMSE = 23.60 MW
Speed-to-power curve RMSE = 41.86 MW
RNN RMSE = 46.21 MW
```

This step does not have COVE improvement because no energy dispatch happens yet. It only chooses the forecast signal used by the Gurobi dispatch steps.

Generated figures:

```text
figures/step1_forecast_rmse_comparison.png
figures/step1_rmse_mae_tradeoff.png
figures/step1_example_forecast_week.png
figures/step1_causal_error_distribution.png
figures/step1_actual_vs_predicted_density.png
figures/step1_error_by_power_bin.png
figures/step1_dispatch_forecast_accuracy_by_lead.png
figures/step1_split_stability.png
```

Together these show model ranking, RMSE/MAE tradeoffs, a representative week,
the complete error distribution, actual-versus-predicted density, error by
power range, accuracy by forecast lead, and stability across data splits.

## Code In This Folder

| File | What it does |
| --- | --- |
| `RUN_1_FORECAST_RMSE.py` | Main command for Step 1. Rebuilds the forecast comparison, prints the table, and makes figures. |
| `code/causal_lag_forecast.py` | Trains the causal lag/ridge forecast from wind speed, lagged power, and calendar features. |
| `code/compare_forecast_rmse.py` | Compares the causal lag/ridge forecast against persistence, speed curve, RNN, physics, and probabilistic outputs. |

There is no Gurobi or dispatch code in this folder. This folder is only for choosing the forecast model.
