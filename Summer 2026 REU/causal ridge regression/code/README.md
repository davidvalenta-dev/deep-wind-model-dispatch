# Part 1 Forecast Code

This folder contains the forecast/RMSE code for the first step of the Summer 2026 REU ladder.

| File | Purpose |
| --- | --- |
| `causal_lag_forecast.py` | Trains the causal lag/ridge-style power forecast from wind speed, lagged power, and calendar features. |
| `compare_forecast_rmse.py` | Recomputes the RMSE comparison against persistence, speed-curve, RNN, physics, and probabilistic forecasts. |

The main reproduction command is run from the parent folder:

```bash
cd ..
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

For normal reruns, change `../EXPERIMENT_KNOBS.py` first. That file is the
one place for the forecast dataset, ridge alpha, comparison forecast file,
forecast output folder, and RMSE output file.

Inputs:

| Source file | Why it is used |
| --- | --- |
| `data/processed/dataset_14-23.csv` | Wind speed and historical generated power used to rebuild the causal lag/ridge forecast. |
| `power_model/evaluation/pyron_model_results.csv` | Saved RNN, physics, and probabilistic forecast outputs used for comparison. |

Outputs:

| Output | Meaning |
| --- | --- |
| `../results/frozen_controlled/causal_lag_forecast_outputs/causal_lag_forecast_predictions.csv` | Hourly causal lag/ridge predictions. |
| `../results/frozen_controlled/causal_lag_forecast_outputs/causal_lag_forecast_metrics.csv` | Train/validation/test metrics for causal lag/ridge and simple baselines. |
| `../results/frozen_controlled/forecast_model_rmse_comparison.csv` | Final RMSE comparison table used by `RUN_1_FORECAST_RMSE.py`. |

This folder intentionally contains no Gurobi or dispatch code. Dispatch starts in the rolling-horizon folder.
