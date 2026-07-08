# Power Model Evaluation

This folder stores prediction metrics and forecast outputs.

## Current Files

| File | Meaning |
| --- | --- |
| `causal_lag_forecast_metrics.csv` | Train/validation/test RMSE and MAE for the causal lag forecast and baselines |
| `causal_lag_forecast_predictions.csv` | Hourly predictions from the causal lag forecast |
| `palouse_results.csv` | Older Palouse evaluation table data |
| `pyron_model_results.csv` | Pyron evaluation data |
| `rnn_models.csv` | RNN comparison data |

## Current Best Metric

The strongest simple operational forecast is `causal_lag_ridge` with test RMSE `22.84 MW`.
