# Benchmark Definitions

This document defines the benchmark cases used to compare the paper-facing
methods.

## Wind-Only Baseline

The wind-only baseline has no storage.

Rule:

- deliver actual wind directly to the grid
- cap delivered power at 249 MW
- curtail actual wind above the grid export cap
- do not charge storage
- do not discharge storage

This baseline answers:

> What happens if the wind farm sells wind directly without storage control?

## 100-MW Constant-Output Baseload Benchmark

This is the new required baseload benchmark.

It is rule-based, not revenue-maximizing.

Frozen configuration:

| Item | Required setting |
| --- | --- |
| Target grid output | 100 MW |
| Storage power rating | 100 MW charge / 100 MW discharge |
| Storage duration | 10 h |
| Storage capacity | 1000 MWh |
| Minimum SoC | 200 MWh |
| Maximum SoC | 1000 MWh |
| Initial SoC | 600 MWh |
| RTE convention | 0.55, applied on the discharge side |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |
| Terminal equality | None; final SoC is reported |
| Settlement price | Actual RTM LMP |

If actual wind is at least 100 MW:

- deliver 100 MW directly to the grid
- use excess wind to charge storage if possible
- curtail remaining wind
- do not discharge

If actual wind is below 100 MW:

- deliver all available wind directly to the grid
- discharge storage to cover as much of the gap to 100 MW as possible
- record output shortfall if the battery cannot cover the gap
- do not charge

SoC update:

```text
SoC(t+1) = SoC(t) + charge(t) - discharge(t) / 0.55
```

This benchmark answers:

> How well can a simple physical storage rule maintain a constant 100 MW output?

## H-Hour Perfect-Information Oracle Rolling-Horizon MILP

This is the new required oracle benchmark.

It is not deployable because it uses future actual wind and future actual RTM
price. It is an upper-bound reference for a rolling-horizon controller.

Required implementation:

- at time t, read actual wind and actual RTM price from t through t+H-1
- solve the constrained CAES MILP over that planning horizon
- execute only the first hour
- carry SoC forward
- advance one hour
- repeat until the end of 2020
- no terminal SoC constraint in ordinary intermediate windows
- when the end of the year enters the planning horizon, enforce final SoC = 600 MWh

Required planning horizons:

- 24 h
- 48 h
- 168 h

This benchmark answers:

> How much value is available if the controller knows the actual future, but still only operates in a rolling-horizon way?

## Deterministic Forecast-Driven Rolling-Horizon MILP

This is a later comparison case.

It uses one realizable forecast trajectory instead of future actual data.

Example:

- forecast wind
- DAM price or another point price forecast
- deterministic MILP
- execute first hour
- replan

This is not the same as the oracle because it cannot see actual future values.

## Scenario-Based Rolling-Horizon MILP

This is a later comparison case.

It uses multiple plausible future trajectories instead of one forecast.

The key scenario rule is non-anticipativity:

> The first-hour action must be shared across scenarios because the controller
> has to choose one real action before knowing which future happens.
