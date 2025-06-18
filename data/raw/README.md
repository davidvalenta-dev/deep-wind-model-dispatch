## This directory contains the raw, compressed data for the following items and sources:
- ```./era5``` contains hourly wind speed gathered at a height of 100m from 2024-2020
- ```./power``` contains ERCOT-provided hourly power generation metrics from 2024-2020
- ```./prices``` contains ERCOT-provided hourly Real-Time-Market prices from 2024-2020
- ```./load``` contains ERCOT-provided hourly user loads from 2024-2020

## Sources:
- ```./era5```: ```../src/download_era5.py```
- ```./power```: https://data.ercot.com/data-product-bundles/NP4-742-CD
- ```./prices```: https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER
- ```./load```: https://www.ercot.com/gridinfo/load/load_hist/index.html