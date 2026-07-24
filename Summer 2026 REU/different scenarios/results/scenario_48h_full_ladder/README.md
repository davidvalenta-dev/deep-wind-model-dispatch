# Full Hourly Scenario Outputs

Each labels CSV contains one row per executed hour for the 2014-2023 scenario
dispatch backtest.

| File | Meaning |
| --- | --- |
| `single_forecast_recourse_nowcast_gated_labels.csv` | One forecast future, 48-hour horizon, hourly replanning. |
| `three_scenario_expected_nowcast_gated_labels.csv` | Three forecast futures, 48-hour horizon, hourly replanning. |
| `five_scenario_expected_nowcast_gated_labels.csv` | Five forecast futures, 48-hour horizon, hourly replanning. |
| `seven_scenario_expected_nowcast_gated_labels.csv` | Seven forecast futures, 48-hour horizon, hourly replanning. |
| `ten_scenario_expected_nowcast_gated_labels.csv` | Ten forecast futures, 48-hour horizon, hourly replanning. |

The summary table for these files is:

```text
uncertainty_aware_summary.csv
```

To regenerate these full hourly CSVs:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python code/run_uncertainty_aware_dispatch.py
```
