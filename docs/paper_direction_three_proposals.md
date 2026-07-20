# Paper Direction: Three Candidate Contributions After Canonical Benchmarks

This document reframes the project around the advisor-required architecture.
The goal is not to throw away the work already completed. The goal is to place
each result in the correct layer so the paper story becomes clear and fair.

## Main Message

The project should be presented as a forecast-aware, physically constrained
wind-storage dispatch framework.

The important claim is:

> Storage value depends on the information available to the controller, the
> optimization model used to turn that information into a plan, and the
> rolling-horizon execution rule used to implement the plan.

This avoids saying that "causal ridge regression," "rolling horizon," and
"different scenarios" are three equal alternatives. They are not. They belong
to different parts of the pipeline.

## Required Benchmark Foundation

Before making the paper claim, the project needs trustworthy reference cases.
These are the new cases requested by Chris.

### 100-MW Constant-Output Baseload Benchmark

This is the required rule-based lower reference.

It tries to deliver exactly 100 MW every hour:

- if wind is above 100 MW, deliver 100 MW and charge storage with extra wind
- if wind is below 100 MW, deliver all wind and discharge storage to fill the gap
- if the battery cannot fill the gap, record output shortfall
- do not use price to make the decision

This benchmark is useful because it gives a simple physical comparison that is
not revenue optimized.

### H-Hour Perfect-Information Oracle Rolling-Horizon MILP

This is the required upper reference for rolling-horizon control.

It gives Gurobi the real future wind and real future RTM price over the next H
hours, then executes only the first hour and repeats. This is not realistic in
deployment, but it shows how much value is available if forecast error were
removed.

Required horizons:

- 24 hours
- 48 hours
- 168 hours

These oracle cases should be used to understand the value of look-ahead and the
gap between realistic methods and perfect information.

## Proposal 1 - Deterministic Forecast-Driven Rolling-Horizon MILP

This proposal uses one causal forecast trajectory.

Layer mapping:

| Layer | Role |
| --- | --- |
| Layer 1 - Information and Forecast | Causal ridge regression predicts future wind and price using only past data. |
| Layer 2 - Optimization | Deterministic MILP optimizes dispatch over one forecasted future. |
| Layer 3 - Rolling-Horizon Control | Execute the first action, update SoC, and replan. |

This is the simplest deployable version of the project.

What it tests:

> If the controller has one forecast of wind and price, can Gurobi use that
> forecast to improve wind-storage dispatch under the physical CAES constraints?

Important caution:

The deterministic forecast case is only as good as the forecast. If the forecast
misses wind or price spikes, Gurobi can optimize the wrong future. This is why
the deterministic case should be compared against the 100-MW baseload, the
oracle rolling-horizon benchmark, and the scenario-based method.

## Proposal 2 - Scenario-Based Rolling-Horizon MILP

This proposal uses multiple possible futures instead of one forecast.

Layer mapping:

| Layer | Role |
| --- | --- |
| Layer 1 - Information and Forecast | Generate several plausible wind and price scenarios. |
| Layer 2 - Optimization | Scenario MILP chooses a shared first-hour action using non-anticipativity. |
| Layer 3 - Rolling-Horizon Control | Execute the first action, observe actual outcome, update SoC, and replan. |

This is the stronger paper direction because it directly addresses uncertainty.

What it tests:

> Instead of betting on one future, can the controller choose a dispatch action
> that performs well across several possible wind and price futures?

Why it matters:

Real wind and price are volatile. A single point forecast can be wrong in a way
that causes poor dispatch decisions. Scenario-based dispatch is more realistic
because it treats forecast uncertainty as part of the optimization problem.

## Proposal 3 - Rolling-Horizon Control Sensitivity and Oracle Gap

This proposal focuses on the control/execution layer.

Layer mapping:

| Layer | Role |
| --- | --- |
| Layer 1 - Information and Forecast | Either actual future values for oracle or forecasts for realistic cases. |
| Layer 2 - Optimization | MILP dispatch with the same CAES constraints. |
| Layer 3 - Rolling-Horizon Control | Compare 24 h, 48 h, 168 h planning horizons with one-hour execution. |

This proposal asks:

> How much does planning horizon matter once the storage constraints and
> execution rule are fixed?

The oracle horizon cases give the cleanest version of this question because
forecast error is removed. Later, the same horizon logic can be compared using
deterministic and scenario forecasts.

## How The Pieces Fit Together

The final paper should not say:

> We tried causal ridge regression, rolling horizon, and scenarios.

A better framing is:

> We built a layered wind-storage dispatch framework. First, we created
> trustworthy physical benchmarks. Then we evaluated deterministic point
> forecasts and scenario-based forecasts inside the same constrained
> rolling-horizon MILP execution framework.

## Current Canonical Results From The Required Run

The required 2020 canonical cases produced:

| Case | Revenue USD | COVE | Final SoC MWh | Violations |
| --- | ---: | ---: | ---: | ---: |
| 100-MW Constant-Output Baseload Benchmark | 9,091,719.37 | 5.655336 | 1000.000 | 0 |
| 24-hour Perfect-Information Oracle RH MILP | 13,361,449.44 | 3.848140 | 600.000 | 0 |
| 48-hour Perfect-Information Oracle RH MILP | 13,392,056.97 | 3.839345 | 600.000 | 0 |
| 168-hour Perfect-Information Oracle RH MILP | 13,398,119.70 | 3.837608 | 600.000 | 0 |

All four outputs contain 8784 hourly rows and passed the QA checks.

## Recommended Paper Story

The clean paper story should be:

1. Define the hybrid wind-storage dispatch problem and CAES constraints.
2. Establish required baselines: wind-only, 100-MW baseload, and oracle rolling-horizon MILP.
3. Show that perfect-information oracle value increases with planning horizon, but with diminishing returns.
4. Evaluate deterministic forecast-driven rolling-horizon MILP as the simplest deployable controller.
5. Evaluate scenario-based rolling-horizon MILP as the uncertainty-aware controller.
6. Discuss the gap between deployable methods and oracle upper bounds.

## What To Say To Chris

Short version:

> I reframed the project into the three layers you requested: information,
> optimization, and rolling-horizon execution. I implemented the 100-MW
> constant-output baseload benchmark and the 24/48/168-hour perfect-information
> oracle rolling-horizon MILP. All four outputs use the same 2020 Pyron wind and
> raw RTM LMP data, have 8784 rows, pass QA with zero violations, and are now
> recorded in the experiment registry.
