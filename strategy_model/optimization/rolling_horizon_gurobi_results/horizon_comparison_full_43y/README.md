# Legacy Full Historical Horizon Comparison

This folder contains an older perfect-information horizon comparison. It is
kept as historical output only.

The current oracle package is here:

```text
Summer 2026 REU/oracle upper bound/
```

## Current Paper-Facing Oracle Result

Primary benchmark: **100-MW Constant-Output Baseload Benchmark**.
Wind-only is secondary reference only.

| Oracle view | Best horizon | COVE | COVE gain vs 100 MW | Revenue metric |
| --- | ---: | ---: | ---: | ---: |
| Daily replan | 168 h | 5.082358 | 40.87% | 10,116,705.90 |
| Hourly replan ceiling | 168 h | 5.076786 | 40.85% | 10,127,810.67 |

The oracle is not deployable because it sees actual future wind and actual
future price. It is used only as an upper-bound reference for the realistic
forecast and scenario controllers.

## Current Command

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/oracle upper bound"
../../venv/bin/python RUN_4_ORACLE_UPPER_BOUND.py
```
