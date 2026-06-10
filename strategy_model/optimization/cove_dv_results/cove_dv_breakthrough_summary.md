# COVE-DV Breakthrough Summary

COVE-DV is a new forecast-window planner. It sees the full 168-hour week and predicts all 168 dispatch actions at once. The action signal is -1 for charge/store, 0 for hold, and +1 for discharge/release.

## Same Held-Out Test Split

- Baseload COVE: 20.305371
- Original COVE-NN COVE: 14.829817
- COVE-DV COVE: 12.901129
- MILP teacher COVE: 12.725301

## Improvement Over Baseload

- Original COVE-NN: 26.97%
- COVE-DV: 36.46%
- MILP teacher: 37.33%

## Main Claim

COVE-DV lowered test COVE from 14.829817 to 12.901129 compared with the original COVE-NN on the same split. That is a COVE reduction of 1.928688. It closes most of the gap between the original neural network and the MILP teacher.

## Caveat

The MILP teacher still uses historical future information, so COVE-DV is best described as a forecast-window planner trained from an optimization teacher. For real operation, the same structure should use forecasts instead of true future data.
