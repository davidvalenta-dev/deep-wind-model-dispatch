# 100 MW Baseload

This folder answers the benchmark question Chris asked for:

> What happens if the wind-storage system follows a simple rule that tries to
> deliver 100 MW every hour?

This is not a Gurobi revenue optimizer. It is a rule-based benchmark.

## Run

From this folder:

```bash
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```

Before running, change all experiment settings in:

```text
EXPERIMENT_KNOBS.py
```

That file controls storage power, storage duration, RTE, target output, grid
cap, initial SoC, min/max SoC, year-end SoC, and oracle horizons. For example,
to test a 35-hour oracle benchmark, set `HORIZONS = [35]`.

The script prints:

- the 100-MW constant-output baseload result;
- the 2014-2023 100-MW constant-output baseload reference for the paper-period ladder;
- the QA violation count;
- the 24 h, 48 h, and 168 h oracle cases compared against this 100-MW baseload;
- the B6 same-year causal/oracle runs compared against this 100-MW baseload by raw realized revenue;
- aligned 2014-2023 comparison CSVs for rolling horizon, scenarios, and oracle;
- updated figures in `figures/`;
- a comparison CSV in the configured output folder.

The full hourly CSVs are in:

```text
results/
```

## Rule

Storage configuration:

| Parameter | Value |
| --- | ---: |
| Target output | 100 MW |
| Storage power | 100 MW |
| Storage duration | 10 h |
| Storage capacity | 1000 MWh |
| Minimum SoC | 200 MWh |
| Maximum SoC | 1000 MWh |
| Initial SoC | 600 MWh |
| RTE | 55%, discharge-side |
| Grid export cap | 249 MW |
| Grid charging | no |

If actual wind is above 100 MW:

1. deliver 100 MW directly;
2. charge storage with extra wind if possible;
3. curtail the rest.

If actual wind is below 100 MW:

1. deliver all available wind;
2. discharge storage to make up the gap if possible;
3. record any remaining output shortfall.

The final SoC is reported but not forced back to 600 MWh.

## Main Canonical 2020 Result

From `results/canonical_2020_summary.csv`:

```text
100-MW baseload revenue: $9,091,719.37
100-MW baseload COVE:    5.655336
Final SoC:               1000.00 MWh
QA violations:           0
```

## Main 2014-2023 Paper-Period 100 MW Baseload

This folder now also builds the same 100 MW rule over the longer paper-period
data so the rolling-horizon, scenario, and oracle folders can be compared
against the same constant-output storage rule.

From `results/constant_output_baseload_100mw_2014_2023_summary.csv`:

```text
Period:                    2014-01-01 00:00:00 to 2023-12-23 20:00:00
Hours:                     87,432
Raw revenue:               $211,515,621.83
Normalized revenue metric: 5,981,942.95
Final SoC:                 980.22 MWh
```

This period intentionally matches the active ladder outputs. The final partial
week of 2023 is excluded because the 168-hour rolling-horizon cases need a
complete future window for a fair comparison.

The hourly file is:

```text
results/constant_output_baseload_100mw_2014_2023_hourly.csv
```

There are also aligned comparison files:

| File | What it compares |
| --- | --- |
| `results/comparison_rolling_horizon_vs_100mw_baseload.csv` | causal ridge + rolling-horizon Gurobi against the 100 MW rule |
| `results/comparison_scenarios_vs_100mw_baseload.csv` | single forecast and scenario dispatch against the 100 MW rule |
| `results/comparison_oracle_vs_100mw_baseload.csv` | perfect-future oracle against the 100 MW rule |

Important: the rolling-horizon/oracle comparison uses the repo's normalized
price metric, because that is how those folders score their runs. The scenario
comparison uses raw LMP revenue, because the scenario folder reports raw
dispatch revenue. The comparison CSVs label this with
`comparison_price_mode`.

## Fair Comparisons In This Folder

This folder compares only cases that share the same canonical setup:

- 2020 Pyron wind;
- raw realized RTM LMP;
- 100 MW / 10 h CAES;
- SoC bounds of 200 to 1000 MWh;
- initial SoC of 600 MWh;
- 249 MW grid export cap;
- no grid charging;
- discharge-side RTE of 0.55.

The fair comparison cases here are:

| Case | What it means |
| --- | --- |
| 100-MW baseload | Rule tries to deliver 100 MW without price optimization |
| 24 h oracle | Gurobi sees the next 24 hours of actual wind and actual price |
| 48 h oracle | Gurobi sees the next 48 hours of actual wind and actual price |
| 168 h oracle | Gurobi sees the next 168 hours of actual wind and actual price |

This folder also includes a B6 revenue-only comparison against the same
100-MW baseload. B6 uses the same 2020 raw realized LMP year and has zero QA
violations, but it was a separate verification package with its own annual SoC
rule, so it should be discussed as a same-year raw-revenue check rather than
merged directly into the long paper ladder.

| B6 case | Revenue vs 100-MW baseload |
| --- | ---: |
| A causal, 100 MW / 6 h | -10.01% |
| A oracle, 100 MW / 6 h | +42.19% |
| B causal, 200 MW / 3 h | -9.84% |
| B oracle, 200 MW / 3 h | +51.90% |
| C causal, 100 MW / 10 h | -7.62% |
| C oracle, 100 MW / 10 h | +47.36% |

The long-period comparison files align each method to the matching timestamp
range before calculating the 100 MW baseload reference value.

## Files

| File | Purpose |
| --- | --- |
| `RUN_0_100MW_BASELOAD.py` | Main Step 0 command. |
| `code/canonical_benchmark_oracle_runner.py` | Full rebuild runner. It can change horizons, storage power, duration, RTE, target output, grid cap, and SoC values from the terminal. |
| `results/constant_output_baseload_100mw_2020_hourly.csv` | Hourly 100-MW baseload output. |
| `results/full_hourly_outputs/` | Full hourly baseload and oracle output CSVs. |
| `results/canonical_2020_summary.csv` | Summary for baseload and oracle cases. |
| `results/canonical_2020_QA_report.csv` | QA checks for baseload and oracle cases. |
| `results/oracle_vs_100mw_baseload_comparison.csv` | Generated comparison against 100-MW baseload. |
| `results/b6_2020_vs_100mw_baseload_revenue_comparison.csv` | B6 A/B/C causal and oracle raw-revenue comparison against 100-MW baseload. |
| `results/constant_output_baseload_100mw_2014_2023_hourly.csv` | Full hourly 2014-2023 100 MW baseload output. |
| `results/constant_output_baseload_100mw_2014_2023_summary.csv` | Summary for the long-period 100 MW baseload. |
| `results/comparison_rolling_horizon_vs_100mw_baseload.csv` | Long-period rolling-horizon comparison against 100 MW baseload. |
| `results/comparison_scenarios_vs_100mw_baseload.csv` | Long-period scenario comparison against 100 MW baseload. |
| `results/comparison_oracle_vs_100mw_baseload.csv` | Long-period oracle comparison against 100 MW baseload. |

Example custom reruns:

```bash
../../venv/bin/python code/canonical_benchmark_oracle_runner.py --horizons 248 --out "results/test_248h"
../../venv/bin/python code/canonical_benchmark_oracle_runner.py --storage-power-mw 200 --storage-duration-h 5 --target-output-mw 100 --horizons 48 --out "results/test_200mw_5h"
```
