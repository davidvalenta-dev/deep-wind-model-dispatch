# Final Paper Figure Index

This folder contains the final Summer 2026 REU figures used for the manuscript.
The figures are copied into the experiment folder they belong to, with names
starting with `paper_figXX_` so they are easy to distinguish from older draft
figures.

## Causal Ridge Regression

Location: `Summer 2026 REU/causal ridge regression/figures/`

- `paper_fig02_forecast_rmse.png`: forecast model RMSE comparison.
- `paper_fig03_forecast_generalization.png`: train/validation/test forecast check.
- `paper_fig04_example_forecast_week.png`: example week comparing actual power and causal ridge forecast.
- `paper_fig20_forecast_methods.png`: plain comparison of the forecast methods tested before dispatch.

## Rolling Horizon

Location: `Summer 2026 REU/rolling horizon/figures/`

- `paper_fig05_rolling_horizon.png`: COVE reduction by planning horizon.
- `paper_fig06_horizon_scorecard.png`: compact scorecard for horizon choice.
- `paper_fig16_rolling_revenue_cove.png`: rolling-horizon revenue and COVE side by side.
- `paper_fig21_rolling_step.png`: simple diagram of solve, execute, update, and replan.

## Different Scenarios

Location: `Summer 2026 REU/different scenarios/figures/`

- `paper_fig07_scenario_count.png`: scenario count comparison.
- `paper_fig08_scenario_scorecard.png`: scenario revenue and COVE scorecard.
- `paper_fig12_best_scenario_week.png`: representative best-scenario week.
- `paper_fig13_revenue_cove_tradeoff.png`: revenue gain versus COVE reduction.
- `paper_fig14_scenario_logic.png`: how one forecast becomes several possible futures.
- `paper_fig17_scenario_revenue_cove.png`: scenario revenue and COVE result.

## Oracle Upper Bound

Location: `Summer 2026 REU/oracle upper bound/figures/`

- `paper_fig09_oracle_upper_bound.png`: oracle horizon sweep.
- `paper_fig18_oracle_revenue_cove.png`: oracle revenue and COVE result.

## Paper Overview Figures

Location: `Summer 2026 REU/paper overview figures/figures/`

These figures explain the whole project instead of one experiment.

- `paper_fig01_pipeline.png`: full wind-storage dispatch pipeline.
- `paper_fig10_ladder.png`: final paper ladder.
- `paper_fig11_constraints.png`: storage and dispatch constraints.
- `paper_fig15_revenue_cove_calculation.png`: revenue and COVE calculation.
- `paper_fig19_ladder_scorecard.png`: proposal ladder scorecard.
- `paper_fig22_information_cases.png`: baseload, causal, scenario, and oracle information cases.
- `paper_fig23_gap_to_oracle.png`: remaining gap between scenario and oracle.
- `paper_fig24_why_ladder_works.png`: why the ladder improves results.
