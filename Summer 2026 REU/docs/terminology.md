# Terminology

| Term | Meaning |
| --- | --- |
| 100-MW Constant-Output Baseload Benchmark | Primary benchmark. A rule-based wind-storage controller tries to deliver 100 MW every hour using actual wind and the 100 MW / 10 h storage setup. |
| Wind-only baseline | Secondary reference. No storage; actual wind is delivered directly to the grid up to 249 MW and excess wind is curtailed. |
| Deterministic Forecast-Driven Rolling-Horizon MILP | One forecasted future path is optimized by Gurobi. |
| Scenario-Based Rolling-Horizon MILP | Multiple possible forecast futures are optimized together. The first committed action is shared across scenarios. |
| H-hour Perfect-Information Oracle Rolling-Horizon MILP | Gurobi sees actual future wind and actual future price for the next H hours. This is not deployable. |
| Daily-replan oracle | Perfect-future oracle that executes 24 hours before replanning. |
| Hourly-replan oracle ceiling | Perfect-future oracle that executes only 1 hour before replanning. |
| COVE | Cost of Valued Energy. Lower is better. In these outputs, COVE gain means the percent reduction in COVE relative to the benchmark. |
| Revenue metric | The normalized revenue-style value used by the forecast backtest runner. |
| Raw realized revenue | Actual delivered MWh multiplied by actual raw RTM/LMP price. |
