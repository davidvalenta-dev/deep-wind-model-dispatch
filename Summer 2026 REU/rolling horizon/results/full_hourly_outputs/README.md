# Full Hourly Rolling-Horizon Outputs

Each CSV contains one row per executed hour for the 2014-2023 causal ridge +
Gurobi rolling-horizon backtest.

| File | Meaning |
| --- | --- |
| `forecast_dispatch_24h.csv` | Causal forecast dispatch with a 24-hour planning horizon. |
| `forecast_dispatch_48h.csv` | Causal forecast dispatch with a 48-hour planning horizon. |
| `forecast_dispatch_72h.csv` | Causal forecast dispatch with a 72-hour planning horizon. |
| `forecast_dispatch_168h.csv` | Causal forecast dispatch with a 168-hour planning horizon. |

The summary table for these files is:

```text
../causal_ridge_rolling_horizon_summary.csv
```

To regenerate these full hourly CSVs:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --direct-reserve-mw 75 --horizons 24 48 72 168 --out-dir "results/full_rebuild_forecast_backtest_2014_2023"
```
