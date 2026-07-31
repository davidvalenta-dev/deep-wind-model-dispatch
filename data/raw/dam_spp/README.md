# ERCOT DAM SPP Data

This folder is for ERCOT Day-Ahead Market Settlement Point Price data used in future DAM-informed dispatch experiments.

The builder is:

```bash
./venv/bin/python data/build_dam_price_dataset.py
```

Important note: the annual public DAM SPP files pulled through `gridstatus.Ercot.get_dam_spp(year)` contain West hub/load-zone locations such as `HB_WEST` and `LZ_WEST`. In the pulled annual DAM SPP files, `PYR_PYRON1` was not present. Therefore the merged future-experiment dataset keeps the original Pyron RTM LMP column and adds West DAM proxy columns.

The default builder pulls 2011-2023 so the model can learn the relationship between DAM and RTM during the pre-2014 training period, then test on 2014-2023.
