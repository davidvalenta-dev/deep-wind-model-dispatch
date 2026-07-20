# Bridge From Summer 2026 REU Folder To Chris Required Names

This file keeps the existing `Summer 2026 REU` folder but maps its experiments
to the required names from Chris's feedback document.

## Existing Folder: causal ridge regression

Required name:

```text
Deterministic Forecast-Driven Rolling-Horizon MILP
```

Meaning:

```text
causal forecast -> deterministic MILP -> rolling-horizon execution
```

This is a later comparison case after the required baseload and oracle
benchmarks are frozen.

## Existing Folder: different scenarios

Required name:

```text
Scenario-Based Rolling-Horizon MILP
```

Meaning:

```text
multiple possible futures -> scenario MILP -> shared first action -> rolling-horizon execution
```

This is a later uncertainty-aware comparison case.

## Existing Folder: rolling horizon

Required name:

```text
Rolling-Horizon Control and Execution
```

Meaning:

```text
planning horizon + execution step + replanning interval + SoC carryover
```

The new required oracle cases belong here:

```text
H-hour Perfect-Information Oracle Rolling-Horizon MILP
```

## New Required Benchmark

Required name:

```text
100-MW Constant-Output Baseload Benchmark
```

Meaning:

```text
try to deliver 100 MW every hour using actual wind and CAES storage
```

This is a rule-based benchmark, not a revenue-maximizing MILP.
