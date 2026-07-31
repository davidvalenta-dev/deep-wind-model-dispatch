# Legacy Best Non-DAM Causal Ridge Result

This folder preserves an older non-DAM causal ridge dispatch run. The current
paper-facing version now lives in the clean Summer 2026 ladder:

```text
Summer 2026 REU/rolling horizon/
```

## Current Paper-Facing Result

Primary benchmark: **100-MW Constant-Output Baseload Benchmark**.
Wind-only is secondary reference only.

Current deterministic setup:

- Forecast method: causal lag/ridge.
- Planning signal: RTM-based causal ridge forecast, not DAM.
- Dispatch solver: rolling-horizon Gurobi MILP.
- Storage: 100 MW / 10 h / 1,000 MWh CAES-equivalent setup.
- SoC bounds: 200-1,000 MWh.
- Initial SoC: 600 MWh.
- Grid export cap: 249 MW.
- Direct reserve: 75 MW.
- Backtest: 2014-2023 aligned ladder period.

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
