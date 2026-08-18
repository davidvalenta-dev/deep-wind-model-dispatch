# Controlled Step 0-4 Commands

Run each command from its listed folder. Every dispatch step uses the frozen
100 MW / 10 h CAES configuration, hourly realized execution, chronological SoC,
and the final 600 MWh target described in the folder README.

## Step 0: 100 MW Benchmark

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```

Main outputs:

```text
results/frozen_controlled/constant_output_baseload_100mw_2014_2023_hourly.csv
results/frozen_controlled/constant_output_baseload_100mw_2014_2023_summary.csv
```

## Step 1: Forecast Comparison

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

The causal lag/ridge model is the winner at 21.24 MW one-hour RMSE. Steps 2
and 3 use its frozen direct-lead forecast family and verify the same forecast
matrix with SHA-256 fingerprint
`318cdac27903e562204f1c78701745dbddb55edd32dd25459d7c79287a62fc91`.

## Step 2: Deterministic Horizon Sweep

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

This changes only `HORIZONS = [24, 48, 72, 168]`. The controlled winner is
168 hours. Complete hourly CSVs are copied to `results/full_hourly_outputs/`.

## Step 3: Scenario-Count Sweep

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

This keeps the Step 2 winning horizon and controller, then changes only the
number of futures: 1, 3, 5, 7, and 10. Leave `MAX_ORIGINS = None` for the full
87,417-hour experiment. The full rerun is intentionally slow.

## Step 4: Oracle Horizon Sweep

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```

All rows execute one hour and replan hourly. The Oracle replaces forecasts with
actual future wind and price inside its 24/48/72/168-hour window.

## Final Cross-Step QA

Run after all five steps exist:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch"
./venv/bin/python "Summer 2026 REU/common/validate_controlled_ladder.py"
```

The validator rejects the package if benchmark COVE/revenue drift, annual or
final SoC misses 600 MWh, physical constraints fail, forecast fingerprints
differ, or the Step 2 winning one-forecast row does not exactly match Step 3.

## Display Saved Results Without Recomputing

Every paper-facing `EXPERIMENT_KNOBS.py` is frozen with
`RERUN_FROM_SOURCE = False`. Running the normal command therefore rebuilds the
terminal table and figures immediately from the committed CSVs. Set the value
to `True` only when you intentionally want a complete source rerun; restore it
to `False` before committing paper results.
