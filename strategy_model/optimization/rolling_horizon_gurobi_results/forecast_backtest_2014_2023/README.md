# Forecast Backtest: 2014-2023

This folder contains the realistic forecast-driven dispatch test.

The controller plans using predicted wind and predicted price, executes only the first 24 hours, carries the battery state forward, and repeats. The causal rows use a 75 MW direct-export reserve to reduce unnecessary curtailment when wind is underpredicted.

## Result Table

| Method | Horizon | Direct reserve | COVE | Baseload COVE | COVE reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Causal forecast + direct reserve | 24 h | 75 MW | 7.033181 | 7.273584 | 3.31% |
| Causal forecast + direct reserve | 48 h | 75 MW | 6.818936 | 7.273584 | 6.25% |
| Causal forecast + direct reserve | 72 h | 75 MW | 6.833112 | 7.273584 | 6.06% |
| Causal forecast + direct reserve | 168 h | 75 MW | 6.878207 | 7.273584 | 5.44% |
| Oracle | 24 h | 0 MW | 5.214904 | 7.273584 | 28.30% |
| Oracle | 48 h | 0 MW | 4.995396 | 7.273584 | 31.32% |
| Oracle | 72 h | 0 MW | 4.920584 | 7.273584 | 32.35% |
| Oracle | 168 h | 0 MW | 4.885438 | 7.273584 | 32.83% |

## Figures

- [Forecast vs oracle improvement](figure_01_forecast_vs_oracle_improvement.png)
- [Realized COVE by horizon](figure_02_realized_cove_by_horizon.png)
- [Realized value by horizon](figure_03_realized_value_by_horizon.png)
- [Forecast error by lead](figure_04_forecast_error_by_lead.png)
- [Forecast example week](figure_05_forecast_example_week.png)

## Key Takeaway

With imperfect forecasts, the 48-hour horizon was best in this backtest. Longer horizons can hurt because forecast error grows farther into the future. The direct reserve helps because the ridge forecast tends to underpredict wind, and strict planned-direct execution otherwise turns some physically deliverable wind into curtailment.
