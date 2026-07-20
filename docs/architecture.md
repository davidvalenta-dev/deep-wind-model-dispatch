# Three-Layer Project Architecture

This document maps the project into the three-layer architecture requested by
Dr. Chris Qin. The purpose is to avoid presenting forecasting, optimization, and
rolling-horizon execution as if they are three unrelated alternatives.

## Layer 1 - Information and Forecast

Layer 1 defines what information the controller is allowed to know before a
dispatch decision is made.

Examples in this repository:

| Information case | Meaning | Repository examples |
| --- | --- | --- |
| Current actual wind | Wind observed at the current hour only | Wind-only baseline and 100-MW constant-output baseload |
| Historical window | Past data used to build forecast features | Causal ridge forecast features using past lags |
| Causal point forecast | One predicted wind and price trajectory | `forecast_backtest_rolling_horizons.py` |
| Scenario forecast | Several possible wind and price futures | `run_uncertainty_aware_dispatch.py` |
| Future actual data | The true future wind and price | Oracle rolling-horizon MILP |

This layer answers, "What does the controller know?"

## Layer 2 - Optimization

Layer 2 converts the available information into a planned dispatch decision.

Examples in this repository:

| Optimization case | Meaning | Repository examples |
| --- | --- | --- |
| Rule-based operation | A fixed rule, not revenue-maximizing optimization | 100-MW constant-output baseload |
| Deterministic MILP | One future trajectory is optimized | Deterministic forecast-driven rolling-horizon MILP |
| Scenario MILP | Several future trajectories are optimized together | Scenario-based rolling-horizon MILP |
| Oracle MILP | Actual future wind and price are optimized | H-hour perfect-information oracle rolling-horizon MILP |

The common physical model is the CAES dispatch model:

- storage power rating: 100 MW
- storage duration: 10 h
- energy capacity: 1000 MWh
- SoC bounds: 200 to 1000 MWh
- RTE: 0.55, applied on the discharge side
- grid export cap: 249 MW
- wind-only charging
- no grid charging

This layer answers, "Given the information, what plan should the system make?"

## Layer 3 - Rolling-Horizon Control and Execution

Layer 3 defines how the plan is executed and scored after actual wind and price
are realized.

Key terms:

| Term | Meaning |
| --- | --- |
| Planning horizon | How far into the future the optimizer solves |
| Execution step | How much of the optimized plan is actually used |
| Replanning interval | How often the optimizer is called again |
| Realized recourse | How planned decisions are clipped to remain feasible under actual wind and SoC |
| SoC carryover | The battery state after one hour becomes the starting state for the next hour |

For the new oracle benchmark, the required execution rule is:

- planning horizons: 24 h, 48 h, and 168 h
- execution step: 1 h
- replanning interval: 1 h
- use future actual wind and RTM price
- execute only the first hour
- carry SoC forward chronologically
- enforce year-end SoC = 600 MWh

In short, this layer answers, "How does the plan actually get used hour by hour?"

## Complete Case Sentence Template

Every case should be explainable in one sentence:

> A defined information source is passed to a defined optimization method with a defined planning horizon, then implemented with a defined execution step, replanning interval, realized settlement rule, and SoC carryover.

Example:

> Future actual wind and RTM price are passed to a perfect-information oracle MILP with a 48-hour planning horizon, executed one hour at a time with hourly replanning, chronological SoC carryover, and year-end SoC forced to 600 MWh.
