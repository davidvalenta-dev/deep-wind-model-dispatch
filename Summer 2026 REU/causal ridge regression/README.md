# Causal Ridge Regression

This folder contains the forecast-driven dispatch experiment. The model predicts future wind generation and price using only past information, then Gurobi uses those predictions to optimize dispatch. The final causal result uses a 75 MW direct-export reserve so the strict realized-execution rule does not curtail useful wind only because the wind forecast was too low.

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

1. Reserve-adjusted causal forecast rolling horizon at 24, 48, 72, and 168 hours.
2. Oracle rolling horizon at 24, 48, 72, and 168 hours.

The causal case is realistic because it uses forecasts. The direct-export reserve is a robustness buffer that keeps extra direct-wind headroom in the planned schedule so wind forecast underprediction does not automatically become curtailment. The oracle case is not realistic because it sees the actual future; it is only an upper bound.

## Main Result

| Method | Horizon | Direct reserve | Revenue metric | COVE | COVE reduction vs baseload |
| --- | ---: | ---: | ---: | ---: | ---: |
| Causal forecast + direct reserve | 24 h | 75 MW | 7,378,742.00 | 7.033181 | 3.31% |
| Causal forecast + direct reserve | 48 h | 75 MW | 7,610,576.00 | 6.818936 | 6.25% |
| Causal forecast + direct reserve | 72 h | 75 MW | 7,594,786.00 | 6.833112 | 6.06% |
| Causal forecast + direct reserve | 168 h | 75 MW | 7,544,994.00 | 6.878207 | 5.44% |

The best reserve-adjusted causal forecast horizon was 48 hours.

## Why This Happens

Short horizons do not see far enough ahead to use storage well. Very long horizons see farther, but the forecasts become less reliable. The direct-export reserve addresses a different issue: the ridge model tends to underpredict wind, so strict planned-direct execution can curtail wind that physically could have fit under the grid cap. In this run, 48 hours gave the best balance between useful look-ahead, forecast error, and direct-wind reserve.

## Run Command

From the repository root:

```bash
./venv/bin/python strategy_model/optimization/forecast_backtest_rolling_horizons.py \
  --direct-reserve-mw 75
```

## Key Files

| Subfolder | Contents |
| --- | --- |
| `code` | Python scripts used for the forecast backtest and robustness analysis |
| `results` | Summary CSVs and hourly output CSVs from the forecast backtest |
| `figures` | Paper figures from the forecast and horizon backtest |
| `metadata` | JSON metadata describing training/backtest periods and storage assumptions |
