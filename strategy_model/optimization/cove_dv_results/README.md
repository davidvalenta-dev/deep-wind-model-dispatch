# COVE-DV Results

This folder stores the compact result table for the COVE-DV teacher-student experiment.

## What COVE-DV Means

COVE-DV is the neural-network student trained from an optimization teacher. The teacher is a MILP/Gurobi-style dispatch optimizer. The student tries to learn the dispatch pattern from the teacher so it can produce decisions without solving the full optimization problem every time.

## Key Result

| Model | COVE | Improvement vs baseload |
| --- | ---: | ---: |
| Baseload | 20.305371 | 0.00% |
| Original COVE-NN comparison | 14.829817 | 26.97% |
| COVE-DV h256 | 12.901129 | 36.46% |
| MILP teacher | 12.725301 | 37.33% |

## File

- `cove_dv_key_results.csv`: compact table for this experiment.
