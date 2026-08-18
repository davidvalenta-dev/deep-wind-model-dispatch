# Full Hourly Oracle Outputs

Each CSV contains one row per executed hour for the 2014-2023 perfect-information
oracle dispatch check.

| File | Meaning |
| --- | --- |
| `oracle_dispatch_24h.csv` | Oracle dispatch with 24 hours of perfect information. |
| `oracle_dispatch_48h.csv` | Oracle dispatch with 48 hours of perfect information. |
| `oracle_dispatch_72h.csv` | Oracle dispatch with 72 hours of perfect information. |
| `oracle_dispatch_168h.csv` | Oracle dispatch with 168 hours of perfect information. |

To regenerate these full hourly CSVs with the frozen controller protocol:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
# Set RERUN_FROM_SOURCE = True in EXPERIMENT_KNOBS.py, then run:
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```
