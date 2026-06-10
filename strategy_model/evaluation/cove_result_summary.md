# COVE Result Summary

## Plain English

COVE is the project score for dispatch. Lower COVE is better.

The dispatch problem asks:

```text
When should the wind farm send power directly to the grid,
when should it store energy,
and when should it release stored energy?
```

The published COVE-NN result from Zach/Jessica reported about a 32.3% COVE improvement over baseload.

## Reproduced Paper COVE-NN Result

After the full-cove update was merged into the repo, the dispatch result can be reproduced from:

```text
strategy_model/src/reproduce_dispatch_results.ipynb
```

Reproduced overall result:

| Method | COVE |
| --- | ---: |
| Baseload | 102.388 |
| COVE-NN | 69.320 |

Improvement:

```text
32.3%
```

Training and validation were also consistent with the paper:

| Split | Improvement |
| --- | ---: |
| Training | about 32.4% |
| Validation | about 32.1% |
| Complete dataset | about 32.3% |

## Corrected Gurobi/MIP Benchmark

A newer benchmark was added under:

```text
strategy_model/optimization/rolling_horizon_gurobi_dispatch.py
```

The corrected full-dataset run uses PNNL CAES values:

| Parameter | Value |
| --- | ---: |
| Storage type | CAES |
| Storage rating | 100 MW |
| Duration | 24 h |
| Capacity | 2,400 MWh |
| RTE | 55% |
| DoD | 80% |
| Minimum SoC | 480 MWh |
| Initial SoC | 1,440 MWh |

Corrected full-dataset result:

| Method | COVE |
| --- | ---: |
| Baseload | 1.743062 |
| Rolling Gurobi MIP | 1.179495 |

Improvement:

```text
32.33%
```

This essentially matches the published COVE-NN improvement while enforcing explicit storage constraints and chronological battery carryover.

## Current Interpretation

The current strongest claim is:

> The paper COVE-NN result was reproduced, and a corrected chronological rolling-horizon Gurobi/MIP benchmark using PNNL CAES constraints matched the published COVE-NN improvement on the full 1980-2023 dataset.

This is not yet a claim that the neural COVE-DV student beats COVE-NN. The COVE-DV student is still a follow-up direction.
