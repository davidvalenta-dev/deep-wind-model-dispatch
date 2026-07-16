# Research Meeting Memo Answer Packet

The paper-facing files are now organized in:

```text
Summer 2026 REU/
```

Use that folder for the clean explanation of the project. It contains three subfolders:

1. `causal ridge regression`
2. `rolling horizon`
3. `different scenarios`

## What To Open During A Meeting

| Question | File or folder |
| --- | --- |
| Main paper result map | `Summer 2026 REU/PAPER_RESULT_FILE_MAP.md` |
| Run commands | `Summer 2026 REU/RUN_COMMANDS.md` |
| Causal forecast and oracle results | `Summer 2026 REU/causal ridge regression/` |
| Rolling-horizon Gurobi results | `Summer 2026 REU/rolling horizon/` |
| Scenario dispatch results | `Summer 2026 REU/different scenarios/` |
| B6 verification package | `Summer 2026 REU/rolling horizon/b6 verification/b6_final_results/` |

## Real Runner Files

| Topic | Runner |
| --- | --- |
| Causal ridge forecast and oracle upper bound | `strategy_model/optimization/forecast_backtest_rolling_horizons.py` |
| Robustness/statistics | `strategy_model/optimization/analyze_forecast_backtest_robustness.py` |
| Gurobi rolling-horizon solver | `strategy_model/optimization/rolling_horizon_gurobi_dispatch.py` |
| Scenario optimization | `strategy_model/optimization/run_uncertainty_aware_dispatch.py` |
| B6 frozen benchmark | `strategy_model/optimization/B6_CANONICAL_RUNNER.py` |
| B6 validation | `strategy_model/optimization/B6_FINAL_VALIDATE.py` |

## Main Point

The paper should use the 2014-2023 scenario and forecast-driven rolling-horizon results as the research story. B6 is a separate 2020 verification package that confirms the implementation details are trustworthy.

The archived COVE-DV/teacher-student exploratory work is preserved in:

```text
strategy_model/optimization/archive/cove_dv_exploratory/
```

