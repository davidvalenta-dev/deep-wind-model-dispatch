# Power Model

This folder is Part 1 of the project: predicting wind farm power.

```text
past wind / weather / power information -> forecast model -> predicted power in MW
```

## Main Files

| File or folder | Purpose |
| --- | --- |
| `src/main.py` | Original neural-network training entry point |
| `src/model.py` | Neural network model definition |
| `src/train.py` | Training loop and loss calculation |
| `src/dataset.py` | Loads and splits the data |
| `src/causal_lag_forecast.py` | New causal lag/ridge-style operational power forecast |
| `evaluation/` | Saved metrics and prediction CSVs |
| `test/` | Generated training runs and checkpoints |
| `probabilistic/` | Older probabilistic/RNN power-model work |

## Best Current Operational Result

The best simple operational model tested here is `causal_lag_ridge`.

| Model | Test RMSE | Test MAE |
| --- | ---: | ---: |
| Causal lag ridge | 22.84 MW | 14.46 MW |
| Lag-1 persistence | 25.26 MW | 15.69 MW |
| Speed-only power curve | 43.85 MW | 31.38 MW |

## Why Speed Squared And Cubed Help

Wind power is not linear in wind speed. A small increase in wind speed can create a much larger increase in available wind power. That is why the forecast includes features like speed squared and speed cubed.

## How To Run

From the repo root:

```bash
cd power_model/src
../../venv/bin/python causal_lag_forecast.py
```

Outputs are written to `power_model/evaluation/`.
