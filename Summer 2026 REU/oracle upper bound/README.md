# Oracle Upper Bound

This folder answers the ceiling question:

> How good could dispatch be if Gurobi knew the future perfectly?

Run:

```bash
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

The oracle case gives Gurobi realized future wind and realized future price. This is not a realistic controller because real operators do not know the future exactly. It is included as an upper bound for comparison.

Main result:

```text
24 h oracle:  28.30% COVE improvement
48 h oracle:  31.32% COVE improvement
72 h oracle:  32.35% COVE improvement
168 h oracle: 32.83% COVE improvement
```

The best oracle case is the 168-hour perfect-future horizon.

Generated figures:

```text
figures/step4_oracle_improvement_by_horizon.png
figures/step4_oracle_cove_by_horizon.png
figures/step4_oracle_runtime_value_tradeoff.png
figures/step4_3d_oracle_revenue_cove.png
```

## Code In This Folder

| File | What it does |
| --- | --- |
| `RUN_4_ORACLE_UPPER_BOUND.py` | Main command for the oracle upper-bound table and figures. |
| `code/build_oracle_summary.py` | Extracts the perfect-future oracle rows from the rolling-horizon result table. |

The full Gurobi backtest code that generated the oracle rows is:

```text
../rolling horizon/code/forecast_backtest_rolling_horizons.py
```

In oracle mode, that script gives each planning window the actual future wind and price instead of forecasted values.
