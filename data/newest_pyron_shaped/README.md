# Newest Pyron-Shaped Proxy Data

This folder contains public proxy datasets built to match the older Pyron data format.

Expected columns:

```text
datetime, speed, power, price, load
```

## Files

| File | Meaning |
| --- | --- |
| `newest_pyron_shaped_dataset_2026070701_2026070712.csv` | Small July 7, 2026 sample with 12 complete rows |
| `newest_pyron_shaped_dataset_2026070701_2026070712_with_sources.csv` | Same sample plus source columns |
| `pyron_proxy_continuation_2024010101_2026070712_available_rows.csv` | Larger proxy continuation dataset with 8,794 complete rows |
| `pyron_proxy_continuation_2024010101_2026070712_available_rows_with_sources.csv` | Larger proxy continuation dataset plus source columns |
| `pyron_proxy_continuation_2024010101_2026070712_README.md` | Detailed notes for the larger proxy dataset |

## Source Logic

| Column | Proxy source idea |
| --- | --- |
| `speed` | HRRR 80m wind speed near Pyron |
| `price` | ERCOT LMP at or near `PYR_PYRON1` |
| `load` | ERCOT West load/forecast series where available |
| `power` | ERCOT West-zone wind generation proxy, not verified plant-level Pyron production |

## Important Warning

This is a proxy dataset. It is good for pipeline validation, but it should not replace verified Pyron plant data in final paper claims.
