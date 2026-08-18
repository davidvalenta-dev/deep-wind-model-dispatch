# Step 3: Scenario-Based Rolling Horizon

This controlled experiment asks:

> After selecting the best deterministic horizon, does optimizing across several fixed forecast futures improve realized dispatch?

## Run

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

Edit `EXPERIMENT_KNOBS.py` to change scenario variants or shared settings.
Leave `MAX_ORIGINS = None` for the full 87,417-hour evaluation.

## Controlled Design

Step 3 inherits the winning 168-hour horizon from Step 2. It keeps the same:

- frozen causal-ridge center forecast;
- 2014-2023 evaluation timestamps;
- current-hour nowcast;
- one-hour execution and one-hour replanning;
- nowcast-gated realized recourse and 75 MW direct reserve;
- 100 MW / 10 h CAES and all physical constraints;
- annual and final 600 MWh realized SoC target;
- primary 100 MW constant-output benchmark and COVE definition.

Only the number of possible futures changes: 1, 3, 5, 7, or 10. Multi-scenario
Gurobi maximizes weighted expected revenue while requiring the first action to
be shared across all futures. Later hypothetical actions can differ because the
controller will replan after the first realized hour.

## Controlled Results

| Futures | Revenue metric | Revenue gain vs 100 MW | COVE | COVE reduction vs 100 MW | Final SoC |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 9,226,453.36 | 54.73% | 5.572751 | 35.37% | 600 MWh |
| 3 | 9,103,166.54 | 52.67% | 5.648224 | 34.50% | 600 MWh |
| 5 | 9,101,377.46 | 52.64% | 5.649334 | 34.48% | 600 MWh |
| 7 | 9,090,553.15 | 52.46% | 5.656061 | 34.41% | 600 MWh |
| 10 | 9,117,510.56 | 52.91% | 5.639338 | 34.60% | 600 MWh |

The deterministic one-forecast case is the winner. The Step 3 one-forecast row
matches the Step 2 168-hour row exactly, including revenue, COVE, timestamps,
forecast fingerprint, and final SoC.

The multi-scenario rows are close to one another but about 0.77-0.97 percentage
points below the deterministic COVE reduction. Under this fixed quantile
construction, averaging across paired wind/price futures makes the first action
more conservative, but those fixed futures are not calibrated strongly enough
to improve the one realized trajectory. This is a negative but useful result:
scenario count alone does not guarantee better realized operation.

## Outputs

```text
results/frozen_controlled/uncertainty_aware_summary.csv
results/frozen_controlled/scenario_summary_vs_wind_only_and_100mw.csv
results/frozen_controlled/single_forecast_recourse_nowcast_gated_labels.csv
results/frozen_controlled/three_scenario_expected_nowcast_gated_labels.csv
results/frozen_controlled/five_scenario_expected_nowcast_gated_labels.csv
results/frozen_controlled/seven_scenario_expected_nowcast_gated_labels.csv
results/frozen_controlled/ten_scenario_expected_nowcast_gated_labels.csv
results/frozen_controlled/experiment_metadata.json
```

## Code Map

| File | Role |
| --- | --- |
| `RUN_3_SCENARIO_COMPARISON.py` | Front door: runs/loads variants, enforces Step 2 equality, prints results, and draws figures. |
| `EXPERIMENT_KNOBS.py` | Winning horizon, scenario list, forecast, storage, SoC, gate, and output settings. |
| `code/run_uncertainty_aware_dispatch.py` | Builds forecasts/scenarios, solves the scenario MILP, executes one realized hour, and writes QA. |
| `code/merge_parallel_scenario_results.py` | Merges independently computed full variants and rejects mismatched fingerprints, final SoC, or QA failures. |
| `../common/annual_soc.py` | Enforces physical year-end targets without SoC resets. |

Primary comparison: **100-MW Constant-Output Baseload Benchmark**. Wind-only is
reported separately because it has no storage and a different annualized-cost
numerator.
