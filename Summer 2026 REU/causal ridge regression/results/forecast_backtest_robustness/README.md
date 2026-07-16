# Forecast Backtest Robustness

This folder checks whether the forecast-driven dispatch result is stable by year, model choice, and storage assumptions.

## Yearly Winner Counts

| Horizon | Years won |
| ---: | ---: |
| 24 h | 0 |
| 48 h | 6 |
| 72 h | 2 |
| 168 h | 1 |

## Statistical Checks

| Comparison | Mean value difference | 95% CI | p-value |
| --- | ---: | --- | ---: |
| 48h minus 24h | 24,600.95 | [7,880.34, 47,391.92] | 0.003906 |
| 48h minus 72h | 737.69 | [-105.91, 1,604.58] | 0.156250 |
| 48h minus 168h | 5,737.26 | [1,290.18, 12,917.40] | 0.019531 |

## Figures

- [Yearly horizon results](figure_01_yearly_horizon_results.png)
- [48h confidence intervals](figure_02_48h_confidence_intervals.png)
- [Forecast model comparison](figure_03_forecast_model_comparison.png)
- [Sensitivity analysis](figure_04_sensitivity_analysis.png)

## Key Takeaway

The 48-hour horizon is the strongest practical horizon in this robustness folder, especially compared with 24 hours and 168 hours.
