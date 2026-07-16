# Rolling Horizon

This folder contains the Gurobi/MILP rolling-horizon dispatch pieces. Rolling horizon means Gurobi plans over a future window, executes only the first part, updates the battery state, and then solves again.

## What Baseload Was

For the full rolling-horizon comparison:

| Quantity | Value |
| --- | ---: |
| Baseload COVE | 1.743062 |

Baseload is the storage reference case used to compare whether optimized dispatch lowers COVE.

## What We Compared Baseload With

We compared baseload against rolling-horizon Gurobi dispatch using different look-ahead windows:

| Horizon | Gurobi COVE | Improvement vs baseload |
| ---: | ---: | ---: |
| 24 h | 1.247991 | 28.40% |
| 48 h | 1.203263 | 30.97% |
| 72 h | 1.186326 | 31.94% |
| 168 h | 1.179495 | 32.33% |

In the full-dataset perfect/teacher-style comparison, longer look-ahead improves because Gurobi is given better future information. In realistic forecast-driven dispatch, longer look-ahead can stop helping because forecasts become less accurate.

## Main Gurobi Variables

| Variable | Meaning |
| --- | --- |
| `P_dir` | wind sent directly to the grid |
| `P_ch` | wind power stored |
| `P_dis` | stored energy released |
| `P_delivered` | total delivered power |
| `SoC` | state of charge, or how full the storage is |
| `u` | binary mode so the system does not charge and discharge at the same time |

## Important Constraints

The rolling-horizon Gurobi model enforces:

- storage minimum and maximum SoC,
- no simultaneous charge and discharge,
- wind-only charging,
- grid export cap,
- delivered power balance,
- available energy limit,
- chronological SoC update.

## B6 Verification

The B6 folder is included here as a verification package. It is not the main paper result. It proves the code can run a clean 2020 benchmark with raw realized LMP, corrected SoC accounting, planned-direct wind execution, and zero constraint violations.

## Key Files

| Subfolder | Contents |
| --- | --- |
| `code` | Gurobi solver, horizon comparison scripts, and B6 verification runner |
| `results` | Rolling-horizon comparison CSVs |
| `figures` | Horizon and dispatch figures |
| `b6 verification` | Frozen 2020 validation outputs requested by Chris |

