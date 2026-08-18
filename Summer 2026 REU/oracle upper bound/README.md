# Step 4: Perfect-Information Oracle

This experiment asks:

> What finite-window performance ceiling is possible if Gurobi knows the actual future wind and price inside each planning window?

The Oracle is not deployable. It is context for the realistic causal methods.
It uses the same physical storage configuration, evaluation period, one-hour
execution, hourly replanning, and annual/final 600 MWh SoC rule. Its information
is different: forecast values are replaced by realized future values inside the
window. It does not need the forecast safety reserve or gate.

## Run

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

Change horizons and physical settings in `EXPERIMENT_KNOBS.py`.

## Results

Primary benchmark: 100-MW Constant-Output Baseload Benchmark, revenue metric
5,962,774.41 and COVE 8.622953.

| Perfect-information window | Revenue metric | COVE | COVE reduction vs 100 MW | Final SoC |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 9,983,543.25 | 5.150148 | 40.27% | 600 MWh |
| 48 h | 10,075,427.34 | 5.103181 | 40.82% | 600 MWh |
| 72 h | 10,079,309.13 | 5.101215 | 40.84% | 600 MWh |
| 168 h | 10,079,788.48 | 5.100973 | 40.84% | 600 MWh |

The ceiling nearly plateaus after 48-72 hours. This means most of the available
finite-window value is already visible within a few days when future wind and
price are perfect. The 168-hour row is still only a rolling one-week Oracle; it
is not an all-knowing full-dataset optimization.

The roughly 5.47 percentage-point COVE gap between the realistic deterministic
168-hour controller (35.37%) and the Oracle 168-hour ceiling (40.84%) measures
remaining value associated mainly with forecast uncertainty and causal
execution.

## Outputs

```text
results/frozen_controlled/forecast_dispatch_summary.csv
results/oracle_upper_bound_summary.csv
results/frozen_controlled/oracle_dispatch_24h.csv
results/frozen_controlled/oracle_dispatch_48h.csv
results/frozen_controlled/oracle_dispatch_72h.csv
results/frozen_controlled/oracle_dispatch_168h.csv
results/full_hourly_outputs/
```

## Code Map

| File | Role |
| --- | --- |
| `RUN_4_ORACLE_UPPER_BOUND.py` | Front door: runs/loads the Oracle sweep, prints comparisons, copies hourly CSVs, and draws figures. |
| `EXPERIMENT_KNOBS.py` | Horizons, storage configuration, annual target, and output settings. |
| `code/forecast_backtest_rolling_horizons.py` | Builds and executes the rolling-window Oracle MILPs. |
| `code/rolling_horizon_gurobi_dispatch.py` | Defines the Gurobi storage optimization model and canonical fixed-cost calculation. |

The primary comparison uses the same-storage 100 MW benchmark. Wind-only is
printed separately as secondary context.
