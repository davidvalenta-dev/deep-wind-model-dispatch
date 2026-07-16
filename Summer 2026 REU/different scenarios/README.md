# Different Scenarios

This folder contains the uncertainty-aware dispatch result. Instead of giving Gurobi one predicted future, the scenario method gives it several possible 24-hour futures for wind and price.

## What Baseload Was

For the scenario experiment:

| Quantity | Value |
| --- | ---: |
| Baseload revenue | $180,653,095.06 |
| Baseload COVE | 0.324684 |

Baseload is the reference case used to measure whether scenario-aware storage dispatch earns more revenue and lowers COVE.

## What We Compared Baseload With

We compared baseload against:

1. single-forecast closed-loop dispatch,
2. three-scenario dispatch,
3. five-scenario dispatch,
4. seven-scenario dispatch,
5. ten-scenario dispatch.

## Main Result

| Method | Dispatch revenue | Gain vs baseload | Dispatch COVE | COVE reduction vs baseload |
| --- | ---: | ---: | ---: | ---: |
| Single forecast | $209,947,648.70 | 16.22% | 0.279380 | 13.95% |
| Three scenarios | $210,298,180.87 | 16.41% | 0.278914 | 14.10% |
| Five scenarios | $211,596,820.64 | 17.13% | 0.277202 | 14.62% |
| Seven scenarios | $212,097,824.78 | 17.41% | 0.276547 | 14.83% |
| Ten scenarios | $205,263,577.22 | 13.62% | 0.285755 | 11.99% |

The best result was the seven-scenario closed-loop gated controller.

## Why Seven Beat Ten

More scenarios do not automatically make better dispatch. The ten-scenario case became more conservative, meaning it avoided some useful charge/discharge decisions because it was trying to protect against too many possible futures. Seven scenarios gave enough uncertainty information without becoming too cautious.

## Key Files

| Subfolder | Contents |
| --- | --- |
| `code` | Scenario runner and supporting forecast/dispatch scripts |
| `results` | Scenario summary CSVs |
| `figures` | Revenue, COVE, example week, and pipeline figures |

