# Full Hourly 2020 Baseload and Oracle Outputs

Each CSV contains one row per hour for the 2020 canonical benchmark.

| File | Meaning |
| --- | --- |
| `constant_output_baseload_100mw_2020_hourly.csv` | 100-MW constant-output baseload benchmark. |
| `oracle_rh_milp_24h_2020_hourly.csv` | 24-hour perfect-information oracle benchmark. |
| `oracle_rh_milp_48h_2020_hourly.csv` | 48-hour perfect-information oracle benchmark. |
| `oracle_rh_milp_168h_2020_hourly.csv` | 168-hour perfect-information oracle benchmark. |

To regenerate these full hourly CSVs:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python code/canonical_benchmark_oracle_runner.py --horizons 24 48 168
```
