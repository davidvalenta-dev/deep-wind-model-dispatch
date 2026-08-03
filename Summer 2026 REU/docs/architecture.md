# Architecture

The Summer 2026 workflow has three layers.

## Layer 1 - Information and Forecast

This layer estimates future wind power and price information before dispatch.
The current forecast comparison is in:

```text
causal ridge regression/
```

The best current power forecast is the causal lag/ridge model.

## Layer 2 - Optimization

This layer sends forecast or perfect-information information to Gurobi. Gurobi solves
a mixed-integer linear program with charge, discharge, direct wind, delivered
power, curtailment, and SoC variables.

The optimization code is in:

```text
rolling horizon/code/forecast_backtest_rolling_horizons.py
rolling horizon/code/rolling_horizon_gurobi_dispatch.py
different scenarios/code/run_uncertainty_aware_dispatch.py
oracle upper bound/code/forecast_backtest_rolling_horizons.py
```

## Layer 3 - Rolling-Horizon Control and Execution

This layer converts an optimized plan into realized operation. The controller
solves a horizon, executes the committed action block, updates realized SoC, and
then replans from the new battery state.

Current daily-replan ladder:

```text
solve H hours -> execute 24 hours -> update SoC -> replan next day
```

Separate oracle reference:

```text
solve 168 hours -> execute 1 hour -> update SoC -> replan next hour
```
