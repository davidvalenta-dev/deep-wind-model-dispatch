# Nora Weekly Comparison: CAES 100 MW / 10h

Selected period: 2020-01-06 00:00 through 2020-01-12 23:00, 168 hourly steps.

Configuration:

- Storage type: CAES
- Storage rating: 100 MW
- Storage duration: 10 h
- Storage capacity: 1,000 MWh
- PNNL CAES RTE: 55%
- DoD: 80%
- Cmin: 200 MWh
- Cmax: 1,000 MWh
- Initial SoC: 600 MWh
- Final SoC: 600 MWh
- Objective: maximize sum(price(t) * P_delivered(t))
- Weekly SoC constraint: SoC_final = SoC_initial
- Horizon: 168 h
- Step: 168 h for this one-week comparison

Results from `rolling_horizon_gurobi_summary.csv`:

- Baseload COVE: 2979.220698
- Gurobi COVE: 2575.377295
- Improvement over baseload: 13.56%
- Baseload revenue: 17258.45
- Gurobi revenue: 19964.73
- Max constraint violation: 1.137e-13

Generated files:

- `nora_weekly_hourly_results.csv`
- `nora_weekly_comparison_all_plots.png`
- `wind_generation.png`
- `electricity_price.png`
- `delivered_power.png`
- `net_storage_power.png`
- `state_of_charge.png`
