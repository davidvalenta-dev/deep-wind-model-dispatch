# Legacy COVE-DV Exploratory Results

This archive stores an early COVE-DV teacher-student experiment. It is **not** the current Summer 2026 REU benchmark package and should not be used as the headline result for the paper/poster.

For the current frozen results, use:

- `Summer 2026 REU/100 MW baseload/`
- `Summer 2026 REU/causal ridge regression/`
- `Summer 2026 REU/rolling horizon/`
- `Summer 2026 REU/different scenarios/`
- `Summer 2026 REU/oracle upper bound/`

## What COVE-DV Means

COVE-DV is the neural-network student trained from an optimization teacher. The teacher is a MILP/Gurobi-style dispatch optimizer. The student tries to learn the dispatch pattern from the teacher so it can produce decisions without solving the full optimization problem every time.

## Current Paper Benchmark

The current primary comparison is the **100 MW constant-output baseload benchmark** with the 100 MW / 10 h CAES configuration. Wind-only is retained only as a secondary reference. The active result tables and figures live in the `Summer 2026 REU/` folder.

## File

- `cove_dv_key_results.csv`: compact table for this experiment.
