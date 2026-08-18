# Summer 2026 REU: Controlled Wind-Storage Experiment Ladder

This folder is the final controlled Step 0-4 workflow for forecasting and
rolling-horizon dispatch at the Pyron wind-farm case study. Each step has one
front-door runner, one knobs file, complete hourly outputs, figures, and a
README explaining what changes and what stays fixed.

## Research Ladder

| Step | Question | What changes |
| ---: | --- | --- |
| 0 | How does a simple 100 MW constant-output wind-storage rule perform? | Establishes the primary same-storage benchmark. |
| 1 | Which causal power forecast has the lowest RMSE? | Forecast method only; no dispatch or COVE. |
| 2 | How far should one-forecast Gurobi look ahead? | Planning horizon: 24/48/72/168 h. |
| 3 | Do several fixed forecast futures beat one forecast? | Scenario count: 1/3/5/7/10 at the Step 2 winning horizon. |
| 4 | What is the finite-window perfect-information ceiling? | Forecasts are replaced with realized future wind/price. |

## Frozen Physical and Execution Setup

| Setting | Value |
| --- | ---: |
| Evaluation period | 2014-01-01 00:00 through 2023-12-23 05:00 |
| Evaluated hours | 87,417 |
| Storage | 100 MW / 10 h CAES-equivalent system |
| Capacity and SoC bounds | 1,000 MWh; 200-1,000 MWh |
| Initial SoC | 600 MWh |
| Completed year-end and final SoC | 600 MWh, physically reached without resets |
| Efficiency | RTE 0.55, applied on discharge |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |
| Realized execution / replanning | 1 hour / 1 hour |
| Primary benchmark | 100-MW Constant-Output Baseload Benchmark |
| Secondary reference | Wind-only/no-storage |

The deterministic and scenario cases also share the current-hour nowcast,
nowcast-gated recourse, 75 MW direct reserve, causal-ridge forecast family, and
forecast fingerprint at the selected horizon. The Oracle keeps the same
physical and timing constraints but replaces forecasts with perfect future
values and therefore does not need the forecast safety heuristics.

## Final Controlled Results

The primary benchmark has normalized price-weighted revenue metric
**5,962,774.41** and COVE **8.622953**. The annualized same-storage cost numerator
is **$51,416,725**.

| Experiment | Best case | Revenue metric | COVE | COVE reduction vs 100 MW |
| --- | --- | ---: | ---: | ---: |
| Step 1 forecast | Causal lag/ridge | RMSE 21.24 MW | n/a | n/a |
| Step 2 deterministic | 168 h | 9,226,453.36 | 5.572751 | 35.37% |
| Step 3 scenario sweep | 1 forecast, 168 h | 9,226,453.36 | 5.572751 | 35.37% |
| Best multi-scenario row | 10 futures, 168 h | 9,117,510.56 | 5.639338 | 34.60% |
| Step 4 rolling-window Oracle | 168 h | 10,079,788.48 | 5.100973 | 40.84% |

The central controlled finding is not that more scenarios automatically win.
The one-forecast 168-hour controller outperforms every tested fixed-quantile
multi-scenario controller. The Oracle is about 5.47 percentage points better,
showing that useful value remains if forecast information improves. The Oracle
also nearly plateaus after 48-72 hours, so longer perfect look-ahead has sharply
diminishing returns.

## Run the Frozen Ladder

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py

cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

All committed knobs use `RERUN_FROM_SOURCE = False`, so the commands immediately
read the frozen CSVs, print the canonical tables, and regenerate the current
figures. Set that value to `True` only for an intentional source reproduction.
Step 3 is computationally expensive because a full rerun solves thousands of
168-hour scenario MILPs.

## Final QA

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch"
./venv/bin/python "Summer 2026 REU/common/validate_controlled_ladder.py"
```

The validator currently passes. It confirms:

- one benchmark revenue and COVE definition across Steps 0, 2, 3, and 4;
- Step 2 and Step 3 exact equality at the selected 168-hour one-forecast case;
- identical selected-horizon forecast SHA-256;
- annual and final realized SoC of 600 MWh;
- zero physical QA violations;
- complete requested horizon and scenario tables.

Machine-readable outputs:

```text
results/final_controlled_ladder/final_controlled_ladder_manifest.csv
results/final_controlled_ladder/final_controlled_ladder_QA.json
audit/summer_2026_reu_data_config_audit.csv
```

The broader file/config audit also passes all 14 controlled hourly files under the
common 100 MW / 10 h checks.

See `RUN_COMMANDS.md` and each subfolder README for exact output paths and code
maps.
