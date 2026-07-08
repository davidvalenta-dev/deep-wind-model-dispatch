# Proxy Validation Results

This folder stores the dispatch test on the new public Pyron-shaped proxy dataset.

## Important Caveat

This is not final plant-level Pyron validation. The `power` column is a public proxy based on ERCOT West-zone generation. Use this as a pipeline test, not as a final paper result.

## Result Table

| Horizon | Baseload COVE | Gurobi COVE | COVE reduction | Revenue |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 23.4913 | 23.3139 | 0.76% | $2.205M |
| 48 h | 23.4913 | 23.3139 | 0.76% | $2.205M |
| 72 h | 23.4913 | 23.3139 | 0.76% | $2.205M |
| 168 h | 23.4913 | 23.3139 | 0.76% | $2.205M |

## Figures

- [Proxy COVE by horizon](proxy_cove_by_horizon.png)
- [Proxy COVE improvement by horizon](proxy_cove_improvement_by_horizon.png)
- [Proxy revenue by horizon](proxy_revenue_by_horizon.png)
- [Proxy example week dispatch](proxy_example_week_dispatch.png)
