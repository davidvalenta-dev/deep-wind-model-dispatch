# Full Hourly Oracle Outputs

Each CSV contains one row per executed hour for the 2014-2023 perfect-future
oracle dispatch check.

| File | Meaning |
| --- | --- |
| `oracle_dispatch_24h.csv` | Oracle dispatch with 24 hours of perfect future information. |
| `oracle_dispatch_48h.csv` | Oracle dispatch with 48 hours of perfect future information. |
| `oracle_dispatch_72h.csv` | Oracle dispatch with 72 hours of perfect future information. |
| `oracle_dispatch_168h.csv` | Oracle dispatch with 168 hours of perfect future information. |

To regenerate these full hourly CSVs:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python code/forecast_backtest_rolling_horizons.py --oracle-only --horizons 24 48 72 168 --out-dir "results/full_rebuild_oracle_2014_2023"
```
