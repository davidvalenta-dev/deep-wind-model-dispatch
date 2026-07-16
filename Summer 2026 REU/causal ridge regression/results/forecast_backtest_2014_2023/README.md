# Forecast Backtest: 2014-2023

This folder contains the realistic forecast-driven dispatch test.

The controller plans using predicted wind and predicted price, executes only the first 24 hours, carries the battery state forward, and repeats.

## Result Table

| Method | Horizon | COVE | Baseload COVE | COVE reduction |
| --- | ---: | ---: | ---: | ---: |
| Causal forecast | 24 h | 6.568551 | 7.273584 | 9.69% |
| Causal forecast | 48 h | 6.377563 | 7.273584 | 12.32% |
| Causal forecast | 72 h | 6.389838 | 7.273584 | 12.15% |
| Causal forecast | 168 h | 6.430980 | 7.273584 | 11.58% |
| Oracle | 24 h | 5.224981 | 7.273584 | 28.16% |
| Oracle | 48 h | 5.004137 | 7.273584 | 31.20% |
| Oracle | 72 h | 4.928657 | 7.273584 | 32.24% |
| Oracle | 168 h | 4.893397 | 7.273584 | 32.72% |

## Figures

- [Forecast vs oracle improvement](figure_01_forecast_vs_oracle_improvement.png)
- [Realized COVE by horizon](figure_02_realized_cove_by_horizon.png)
- [Realized value by horizon](figure_03_realized_value_by_horizon.png)
- [Forecast error by lead](figure_04_forecast_error_by_lead.png)
- [Forecast example week](figure_05_forecast_example_week.png)

## Key Takeaway

With imperfect forecasts, the 48-hour horizon was best in this backtest. Longer horizons can hurt because forecast error grows farther into the future.
