# Step 2: Deterministic Rolling Horizon

This controlled experiment asks one question:

> With one frozen causal-ridge forecast and one fixed controller, how far ahead should Gurobi plan?

## Run

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

Edit `EXPERIMENT_KNOBS.py` to change a horizon or storage setting. The frozen
default is `RERUN_FROM_SOURCE = False`, which immediately displays the committed
results and rebuilds the figures. Set it to `True` only for an intentional full
source rerun.

## What Is Held Fixed

- 2014-01-01 through 2023-12-23 evaluation period: 87,417 hours.
- Causal-ridge center forecast trained before the test period.
- One-hour execution and one-hour replanning.
- Current-hour wind and price nowcast.
- Same nowcast-gated realized recourse used by Step 3.
- 75 MW direct-wind reserve.
- 100 MW / 10 h CAES, 1,000 MWh capacity, 200-1,000 MWh SoC.
- Initial SoC 600 MWh; every completed evaluation year and the final row end at 600 MWh.
- RTE 0.55 on discharge, 249 MW grid cap, wind-only charging, no grid charging.

Only the planning horizon changes: 24, 48, 72, or 168 hours. Gurobi solves the
entire window, executes the first hour, observes the new current state, and
solves again.

## Controlled Results

Primary benchmark: the 100-MW Constant-Output Baseload Benchmark, revenue
metric 5,962,774.41 and COVE 8.622953.

| Horizon | Revenue metric | COVE | COVE reduction vs 100 MW | Final SoC |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 8,853,470.17 | 5.807522 | 32.65% | 600 MWh |
| 48 h | 9,055,868.37 | 5.677724 | 34.16% | 600 MWh |
| 72 h | 9,118,656.03 | 5.638630 | 34.61% | 600 MWh |
| 168 h | 9,226,453.36 | 5.572751 | 35.37% | 600 MWh |

The 168-hour horizon is the controlled winner. Longer look-ahead helps this
controller identify more storage opportunities, while hourly replanning limits
the damage from later forecast errors. The improvement from 72 to 168 hours is
small, so the result is a diminishing-return finding, not a claim that longer
is always better.

Wind-only/no-storage is a secondary reference. It uses a different cost
numerator, so revenue and COVE comparisons against wind-only must be interpreted
separately from the primary same-storage benchmark.

## Outputs

```text
results/controlled_hourly_nowcast_from_knobs/controlled_single_forecast_horizon_summary.csv
results/controlled_hourly_nowcast_from_knobs/horizon_24h/
results/controlled_hourly_nowcast_from_knobs/horizon_48h/
results/controlled_hourly_nowcast_from_knobs/horizon_72h/
results/controlled_hourly_nowcast_from_knobs/horizon_168h/
results/full_hourly_outputs/
```

Each horizon folder contains the complete hourly dispatch CSV, summary, and
metadata. Step 3 copies the winning 168-hour one-forecast row directly from
this controlled result, then changes only scenario count.

## Figures

The seven current figures show COVE reduction, COVE level, revenue metric,
incremental value from extending the horizon, runtime/value tradeoff, matched
revenue/COVE small multiples, and a compact horizon scorecard. They are rebuilt
from `controlled_single_forecast_horizon_summary.csv`; no plotted value is
typed manually.

## Code Map

| File | Role |
| --- | --- |
| `RUN_2_ROLLING_HORIZON.py` | Front door: loops over horizons, combines rows, checks Step 3 equality, and draws figures. |
| `EXPERIMENT_KNOBS.py` | Frozen settings and user-editable experiment knobs. |
| `../different scenarios/code/run_uncertainty_aware_dispatch.py` | Canonical Gurobi controller shared with Step 3. |
| `results/.../single_forecast_recourse_nowcast_gated_labels.csv` | Complete realized hourly trajectory for a horizon. |
