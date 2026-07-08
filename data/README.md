# Data

This folder contains historical data used by the power and dispatch models.

## Main Data Areas

| Folder or file | Purpose |
| --- | --- |
| `processed/` | Cleaned wind, price, power, and load data used by the project |
| `processed/dataset_1980-2023_withloads_fix.csv` | Long historical dispatch dataset |
| `processed/dataset_14-23.csv` | 2014-2023 testing-style dataset |
| `newest_pyron_shaped/` | New public proxy datasets built to match the same column format |
| `raw/` | Raw downloaded files that were preserved |

## Proxy Data Warning

The newest public dataset is useful for testing the pipeline on newer dates, but it is not verified plant-level Pyron production. Its `power` column is a proxy.
