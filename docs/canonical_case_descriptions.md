# Canonical Case Descriptions

This document defines the frozen canonical cases created for the next research
meeting.

## Common Data

Evaluation period:

```text
2020-01-01 00:00:00 through 2020-12-31 23:00:00
```

Expected row count:

```text
8784 hourly rows
```

Wind source:

```text
data/processed/pyron_power.csv
```

Price source:

```text
data/raw/prices/12cfb125-8fa9-4401-8b0f-9d928544b721.csv
```

Price rule:

```text
raw, uncapped, unnormalized RTM LMP in USD/MWh
```

## Common Storage Configuration

| Parameter | Value |
| --- | --- |
| Storage type | CAES |
| Storage power | 100 MW |
| Duration | 10 h |
| Energy capacity | 1000 MWh |
| Minimum SoC | 200 MWh |
| Maximum SoC | 1000 MWh |
| Initial SoC | 600 MWh |
| RTE | 0.55 |
| RTE convention | discharge-side loss |
| Grid export cap | 249 MW |
| Grid charging | not allowed |

## Case 1: 100-MW Constant-Output Baseload Benchmark

Case ID:

```text
constant_output_baseload_100mw_2020
```

Case name:

```text
100-MW Constant-Output Baseload Benchmark
```

Information:

- current actual wind only
- price is not used to make decisions
- actual RTM price is used only for realized revenue

Decision method:

- rule-based controller
- not a MILP
- not revenue maximizing

Execution:

- one hour at a time
- chronological SoC carryover
- no terminal equality constraint
- final SoC is reported

Required hourly output:

- timestamp
- actual_wind_MW
- target_output_MW
- direct_wind_MW
- charge_MW
- discharge_MW
- delivered_power_MW
- curtailment_MW
- output_shortfall_MW
- SOC_start_MWh
- SOC_end_MWh
- RTM_price_per_MWh
- hourly_revenue

## Case 2: H-Hour Perfect-Information Oracle Rolling-Horizon MILP

Case IDs:

```text
oracle_rh_milp_24h_2020
oracle_rh_milp_48h_2020
oracle_rh_milp_168h_2020
```

Case names:

```text
24-hour Perfect-Information Oracle Rolling-Horizon MILP
48-hour Perfect-Information Oracle Rolling-Horizon MILP
168-hour Perfect-Information Oracle Rolling-Horizon MILP
```

Information:

- future actual wind
- future actual RTM LMP
- non-deployable oracle information

Decision method:

- constrained CAES MILP
- maximize raw realized revenue over the planning horizon

Execution:

- planning horizon H = 24, 48, or 168 h
- execution step = 1 h
- replanning interval = 1 h
- execute only first-hour decision
- carry SoC forward chronologically
- no terminal equality in ordinary intermediate windows
- force final SoC = 600 MWh when the end of the year enters the planning horizon

## QA Checks

Every canonical output must pass:

- exact row count and chronological continuity
- SoC recursion closes every hour
- SoC remains between 200 and 1000 MWh
- charge and discharge stay within 100 MW
- no simultaneous charge and discharge
- no grid charging
- wind-energy balance closes
- curtailment is nonnegative
- hourly revenue sums exactly to total revenue
- initial and final SoC are reported

Additional baseload checks:

- delivered power never exceeds 100 MW
- output shortfall is nonnegative
- charging only occurs when actual wind exceeds 100 MW
- discharging only occurs when actual wind is below 100 MW
- final SoC is reported but not forced

Additional oracle checks:

- execution step is exactly 1 hour
- replanning interval is exactly 1 hour
- only first-hour action is executed
- year-end SoC equals 600 MWh
- future actual data is used only in oracle-labeled cases
