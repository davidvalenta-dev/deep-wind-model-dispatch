# Canonical Case Descriptions

## Step 0

Build the 100-MW Constant-Output Baseload Benchmark and same-year oracle QA
checks.

Command:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```

## Step 1

Compare forecast models by RMSE. This step does not compute dispatch COVE.

Command:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/causal ridge regression"
../../venv/bin/python RUN_1_FORECAST_RMSE.py
```

## Step 2

Run deterministic forecast-driven rolling-horizon Gurobi dispatch using the
causal lag/ridge forecast and the 75 MW direct-reserve execution rule.

Command:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

## Step 3

Run scenario-based rolling-horizon dispatch for 1, 3, 5, 7, and 10 forecast
futures. The primary comparison is the 100 MW benchmark.

Command:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

## Step 4

Run the controlled perfect-information Oracle horizon sweep. Every row executes
one hour and replans hourly; only the perfect-information window changes.

Command:

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```
