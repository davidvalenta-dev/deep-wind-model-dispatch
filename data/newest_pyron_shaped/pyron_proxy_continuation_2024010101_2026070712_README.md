# Pyron-Shaped Proxy Continuation Dataset

This file extends the old Pyron-shaped format after the 1980-2023 dataset using the public/local pieces currently available.

## Exact CSV columns

`datetime,speed,power,price,load`

## Coverage

- Rows: 8794
- First timestamp: 2024-01-01 00:00:00
- Last timestamp: 2026-07-07 12:00:00
- 2024 complete hourly block rows: 8782
- 2024 missing hourly timestamps after merge: 2
- Complete local block: 2024-01-01 01:00 through 2024-12-31 23:00 from existing repo processed files.
- Current public block: 2026-07-07 01:00 through 2026-07-07 12:00 from ERCOT/NOAA public sources.
- Gap note: 2025 through most of 2026 is not filled here because the repo does not currently contain complete matching public-proxy power/speed/load pieces for that period.

## Important caveat

This is a proxy dataset, not true Pyron plant-specific generation. The power column uses ERCOT West-zone wind generation proxies where available.
