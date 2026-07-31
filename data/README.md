# Data

This folder contains historical data used by the power and dispatch models.

## Main Data Areas

| Folder or file | Purpose |
| --- | --- |
| `processed/` | Cleaned wind, price, power, and load data used by the project |
| `processed/dataset_1980-2023_withloads_fix.csv` | Long historical dispatch dataset |
| `processed/dataset_14-23.csv` | 2014-2023 testing-style dataset |
| `processed/dataset_2014_2023_with_dam_prices.csv` | Future-experiment dataset with the project RTM Pyron LMP plus ERCOT DAM West hub/load-zone SPP columns |
| `build_dam_price_dataset.py` | Rebuilds the DAM-integrated 2014-2023 dataset |
| `newest_pyron_shaped/` | New public proxy datasets built to match the same column format |
| `raw/` | Raw downloaded files that were preserved |

## Proxy Data Warning

The newest public dataset is useful for testing the pipeline on newer dates, but it is not verified plant-level Pyron production. Its `power` column is a proxy.

## DAM Data Note

The DAM-integrated dataset is separate from the frozen RTM benchmark. It is intended for a future experiment where dispatch is planned with day-ahead West prices and realized revenue is scored with Pyron RTM LMP. The annual ERCOT DAM SPP archive pulled by `gridstatus` did not include `PYR_PYRON1`, so the dataset includes `LZ_WEST` and `HB_WEST` DAM columns instead of a Pyron-node DAM column.
