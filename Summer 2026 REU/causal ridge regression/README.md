# Causal Ridge Regression

This folder contains the forecast-driven dispatch experiment. The model predicts future wind generation and price using only past information, then Gurobi uses those predictions to optimize dispatch.

## What Baseload Was

Baseload is the comparison case where wind is delivered in a simple reference pattern instead of using optimized storage dispatch.

For this forecast backtest:

| Quantity | Value |
| --- | ---: |
| Baseload revenue metric | 7,134,863.37 |
| Baseload COVE | 7.273584 |

This result uses the normalized/value metric from the forecast backtest. Do not mix this revenue number with the raw USD scenario result or the B6 2020 raw-LMP result.

## What We Compared Baseload With

We compared baseload against:

1. Causal forecast rolling horizon at 24, 48, 72, and 168 hours.
2. Oracle rolling horizon at 24, 48, 72, and 168 hours.

The causal case is realistic because it uses forecasts. The oracle case is not realistic because it sees the actual future; it is only an upper bound.

## Main Result

| Method | Horizon | Revenue metric | COVE | COVE reduction vs baseload |
| --- | ---: | ---: | ---: | ---: |
| Causal forecast | 24 h | 7,900,680.73 | 6.568551 | 9.69% |
| Causal forecast | 48 h | 8,137,281.56 | 6.377563 | 12.32% |
| Causal forecast | 72 h | 8,121,648.93 | 6.389838 | 12.15% |
| Causal forecast | 168 h | 8,069,691.73 | 6.430980 | 11.58% |

The best causal forecast horizon was 48 hours.

## Why This Happens

Short horizons do not see far enough ahead to use storage well. Very long horizons see farther, but the forecasts become less reliable. In this run, 48 hours gave the best balance between useful look-ahead and forecast error.

## Key Files

| Subfolder | Contents |
| --- | --- |
| `code` | Python scripts used for the forecast backtest and robustness analysis |
| `results` | Summary CSVs and hourly output CSVs from the forecast backtest |
| `figures` | Paper figures from the forecast and horizon backtest |
| `metadata` | JSON metadata describing training/backtest periods and storage assumptions |

