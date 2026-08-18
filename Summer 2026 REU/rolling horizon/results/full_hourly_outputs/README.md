# Full Hourly Rolling-Horizon Outputs

Each CSV contains one row per executed hour for the 2014-2023 causal ridge +
Gurobi rolling-horizon backtest.

| File | Meaning |
| --- | --- |
| `single_forecast_24h_hourly.csv` | Causal forecast dispatch with a 24-hour planning horizon. |
| `single_forecast_48h_hourly.csv` | Causal forecast dispatch with a 48-hour planning horizon. |
| `single_forecast_72h_hourly.csv` | Causal forecast dispatch with a 72-hour planning horizon. |
| `single_forecast_168h_hourly.csv` | Causal forecast dispatch with a 168-hour planning horizon. |

The summary table for these files is:

```text
../controlled_hourly_nowcast_from_knobs/controlled_single_forecast_horizon_summary.csv
```

To regenerate these full hourly CSVs:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
# Set RERUN_FROM_SOURCE = True in EXPERIMENT_KNOBS.py, then run:
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```
