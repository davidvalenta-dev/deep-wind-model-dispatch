# Uncertainty-Aware Dispatch Results

This folder contains the scenario-based dispatch experiment.

## What Changed

Instead of giving Gurobi one predicted future, the best version gives it several possible 24-hour wind and price futures. Gurobi chooses a first-hour storage action that works well across those futures.

Then only the first hour is executed, the real battery state is carried forward, and the process repeats chronologically.

## Constraints Used

The run uses the Nora/Chris CAES setup:

| Item | Value |
| --- | ---: |
| Storage power | 100 MW |
| Storage duration | 10 hours |
| Max SoC | 1000 MWh |
| Min SoC | 200 MWh |
| Initial SoC | 600 MWh |
| RTE | 55% |
| Grid export limit | 249 MW |
| SoC indexing | N+1 |
| Chronological carryover | Yes |

It also enforces no simultaneous charge/discharge, wind-only charging, delivered-power balance, and grid export limits.

## Final Result Table

| Method | Revenue | Gain vs baseload | COVE reduction |
| --- | ---: | ---: | ---: |
| Single forecast closed-loop gated | $209.948M | 16.22% | 13.95% |
| Three-scenario closed-loop gated | $210.298M | 16.41% | 14.10% |
| Five-scenario closed-loop gated | $211.597M | 17.13% | 14.62% |
| Seven-scenario closed-loop gated | $212.098M | 17.41% | 14.83% |
| Ten-scenario closed-loop gated | $205.264M | 13.62% | 11.99% |

## Figures

- [Revenue breakthrough](final_figure_01_revenue_breakthrough.png)
- [COVE breakthrough](final_figure_02_cove_breakthrough.png)
- [Example week dispatch](final_figure_03_example_week_dispatch.png)
- [Uncertainty pipeline](final_figure_04_uncertainty_pipeline.png)

## Key Takeaway

The seven-scenario controller was best in this test. Adding more scenarios did not automatically help: the ten-scenario case became too conservative.
