# Controlled Result File Map

Use only the files below for the frozen controlled Step 0-4 paper claims.

| Claim | Frozen value | Source file |
| --- | ---: | --- |
| 100 MW benchmark revenue metric | 5,962,774.41 | `100 MW baseload/results/frozen_controlled/constant_output_baseload_100mw_2014_2023_summary.csv` |
| 100 MW benchmark COVE | 8.622953 | same Step 0 summary |
| Forecast winner | causal lag/ridge, RMSE 21.24 MW | `causal ridge regression/results/frozen_controlled/forecast_model_rmse_comparison.csv` |
| Deterministic winner | 168 h, 35.37% COVE reduction | `rolling horizon/results/controlled_hourly_nowcast_from_knobs/controlled_single_forecast_horizon_summary.csv` |
| Step 3 one-forecast row | exact Step 2 168 h match | `different scenarios/results/frozen_controlled/uncertainty_aware_summary.csv` |
| Best multi-scenario row | 10 futures, 34.60% COVE reduction | same Step 3 summary |
| Oracle ceiling | 168 h, 40.84% COVE reduction | `oracle upper bound/results/oracle_upper_bound_summary.csv` |
| Cross-step QA | PASS | `results/final_controlled_ladder/final_controlled_ladder_QA.json` |

## Complete Hourly Outputs

| Experiment | Files |
| --- | --- |
| Step 0 benchmark | `100 MW baseload/results/frozen_controlled/constant_output_baseload_100mw_2014_2023_hourly.csv` |
| Step 2 horizons | `rolling horizon/results/full_hourly_outputs/single_forecast_*h_hourly.csv` |
| Step 3 scenarios | `different scenarios/results/frozen_controlled/*_labels.csv` |
| Step 4 Oracle | `oracle upper bound/results/full_hourly_outputs/oracle_dispatch_*h.csv` |

## Reproduction Entry Points

| Step | Runner | Knobs |
| ---: | --- | --- |
| 0 | `100 MW baseload/RUN_0_100MW_BASELOAD.py` | `100 MW baseload/EXPERIMENT_KNOBS.py` |
| 1 | `causal ridge regression/RUN_1_FORECAST_RMSE.py` | `causal ridge regression/EXPERIMENT_KNOBS.py` |
| 2 | `rolling horizon/RUN_2_ROLLING_HORIZON.py` | `rolling horizon/EXPERIMENT_KNOBS.py` |
| 3 | `different scenarios/RUN_3_SCENARIO_COMPARISON.py` | `different scenarios/EXPERIMENT_KNOBS.py` |
| 4 | `oracle upper bound/RUN_4_ORACLE_UPPER_BOUND.py` | `oracle upper bound/EXPERIMENT_KNOBS.py` |

## Verification

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch"
./venv/bin/python "Summer 2026 REU/common/validate_controlled_ladder.py"
```

The validator confirms one benchmark definition, matching selected forecast
fingerprints, exact Step 2/Step 3 one-forecast equality, annual/final 600 MWh
SoC, and zero physical QA violations. The separate data/config audit reports
14/14 controlled hourly files passing the common 100 MW / 10 h checks.
