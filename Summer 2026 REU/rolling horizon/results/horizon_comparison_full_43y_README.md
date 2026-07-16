# Full Historical Horizon Comparison

This folder compares perfect-information Gurobi rolling-horizon windows.

Perfect-information means Gurobi is allowed to see the actual future values inside the lookahead window. This is useful as an upper-bound benchmark, not as a real deployed forecast controller.

## Result Table

| Horizon | COVE | Baseload COVE | COVE reduction | Runtime |
| ---: | ---: | ---: | ---: | ---: |
| 24 h | 1.247991 | 1.743062 | 28.40% | 16.81 s |
| 48 h | 1.203263 | 1.743062 | 30.97% | 29.23 s |
| 72 h | 1.186326 | 1.743062 | 31.94% | 45.19 s |
| 168 h | 1.179495 | 1.743062 | 32.33% | 102.59 s |

## Figures

- [COVE by horizon](figure_01_cove_by_horizon.png)
- [Improvement by horizon](figure_02_improvement_by_horizon.png)
- [Value metric by horizon](figure_03_value_metric_by_horizon.png)
- [Runtime by horizon](figure_04_runtime_by_horizon.png)
- [Example week SoC](figure_05_example_week_soc.png)
- [Example week dispatch](figure_06_example_week_dispatch.png)

## Key Takeaway

A longer lookahead helps when future values are known. The 168-hour horizon is best in this perfect-information test, but 48-72 hours captures most of the improvement.
