# Legacy Uncertainty-Aware Dispatch Results

This folder contains older scenario-dispatch outputs from earlier research
iterations. Keep the files for history, but do **not** use this folder as the
current paper-facing result source.

The current reproducible scenario package is here:

```text
Summer 2026 REU/different scenarios/
```

## Current Paper-Facing Scenario Result

Primary benchmark: **100-MW Constant-Output Baseload Benchmark**.
Wind-only is secondary reference only.

| Method | Revenue | Revenue gain vs 100 MW | COVE | COVE gain vs 100 MW |
| --- | ---: | ---: | ---: | ---: |
| 1 forecast | $337,322,348.04 | 59.31% | 0.173884 | 37.23% |
| 3 scenarios | $353,949,333.45 | 67.16% | 0.165716 | 40.18% |
| 5 scenarios | $353,117,910.43 | 66.77% | 0.166106 | 40.04% |
| 7 scenarios | $353,220,656.50 | 66.82% | 0.166058 | 40.05% |
| 10 scenarios | $341,858,797.71 | 61.45% | 0.171577 | 38.06% |

Current best scenario case: **3 scenarios**, with **40.18% COVE gain** and
**67.16% revenue gain** versus the 100 MW benchmark.

## Current Command

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/different scenarios"
../../venv/bin/python RUN_3_SCENARIO_COMPARISON.py
```

## Current Constraints

The current Summer 2026 ladder uses one shared CAES-equivalent setup:

| Item | Value |
| --- | ---: |
| Storage power | 100 MW charge / 100 MW discharge |
| Storage duration | 10 h |
| Capacity | 1,000 MWh |
| SoC bounds | 200-1,000 MWh |
| Initial SoC | 600 MWh |
| RTE | 55%, discharge-side |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |

For current figures, hourly CSVs, and README instructions, use the `Summer 2026
REU` folder rather than this legacy folder.
