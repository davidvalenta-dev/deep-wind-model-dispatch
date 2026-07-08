# Nora Weekly Comparison: Jan. 6-12, 2020, Raw LMP

This folder stores the one-week Gurobi comparison using the shared CAES setup.

## Setup

| Item | Value |
| --- | ---: |
| Storage type | CAES |
| Power rating | 100 MW |
| Duration | 10 hours |
| Capacity | 1000 MWh |
| RTE | 55% |
| Cmin | 200 MWh |
| Initial SoC | 600 MWh |
| Final SoC | 600 MWh |
| Grid cap | 249 MW |
| Horizon | 168 hours |
| SoC indexing | N+1, final after hour 168 |

## Result

| Metric | Value |
| --- | ---: |
| Wind-only revenue | $451,354.54 |
| Baseload revenue | $432,923.47 |
| Gurobi revenue | $500,809.95 |
| Baseload COVE | 118.7663 |
| Gurobi COVE | 102.6671 |
| COVE reduction | 13.56% |

## Figures

- [All plots](nora_weekly_comparison_all_plots.png)
- [Wind generation](wind_generation.png)
- [Electricity price](electricity_price.png)
- [Delivered power](delivered_power.png)
- [Net storage power](net_storage_power.png)
- [State of charge](state_of_charge.png)

## Note

Nora's exact attached MATLAB/input-file comparison produced an approximately matching revenue after aligning the Python model to N+1 SoC indexing. This folder stores the raw-LMP figure set generated in this repo.
