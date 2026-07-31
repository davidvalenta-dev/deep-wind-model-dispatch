# Legacy Forecast Backtest: 2014-2023

This folder contains an older forecast-driven dispatch backtest. Keep the files
for history, but do **not** treat the numbers in this directory as the current
paper-facing result set.

The current deterministic rolling-horizon package is here:

```text
Summer 2026 REU/rolling horizon/
```

## Current Paper-Facing Deterministic Result

Primary benchmark: **100-MW Constant-Output Baseload Benchmark**.
Wind-only is secondary reference only.

| Horizon | COVE | COVE gain vs 100 MW | Revenue metric | Revenue gain vs 100 MW |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 6.966281 | 18.95% | 7,380,799.56 | 22.16% |
| 48 h | 6.822045 | 20.63% | 7,536,849.56 | 26.08% |
| 72 h | 6.830033 | 20.54% | 7,528,034.19 | 25.80% |
| 168 h | 6.847708 | 20.33% | 7,508,603.24 | 25.35% |

Current best deterministic case: **48 h**, with **20.63% COVE gain** versus the
100 MW benchmark.

## Current Command

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/rolling horizon"
../../venv/bin/python RUN_2_ROLLING_HORIZON.py
```

## Current Oracle Context

The current perfect-future oracle result is maintained separately:

```text
Summer 2026 REU/oracle upper bound/
```

Best daily-replan oracle: **168 h**, with **40.87% COVE gain** versus the 100
MW benchmark. The separate hourly-replan 168 h oracle ceiling is **40.85% COVE
gain**.
