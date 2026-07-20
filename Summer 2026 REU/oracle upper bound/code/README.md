# Oracle Upper-Bound Code

This folder contains the code for the perfect-future upper-bound step.

| File | Purpose |
| --- | --- |
| `build_oracle_summary.py` | Extracts the oracle rows from the Step 2 rolling-horizon result table and writes the oracle-only summary. |

The actual Gurobi solve that produced these oracle rows is in:

```text
../rolling horizon/code/forecast_backtest_rolling_horizons.py
```

In that script, oracle mode uses realized future wind and realized future price inside each planning horizon. That is why the oracle result is not realistic: it is a benchmark showing the highest possible improvement under the same storage constraints.
