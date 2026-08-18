# Step 0: 100-MW Constant-Output Baseload Benchmark

This is the primary benchmark for the controlled Step 0-4 ladder. It is a
simple rule-based wind-storage controller, not a Gurobi revenue optimizer.

## Run

```bash
cd "/Users/davidvalenta/deep-wind-model-dispatch/Summer 2026 REU/100 MW baseload"
../../venv/bin/python RUN_0_100MW_BASELOAD.py
```

Change settings in `EXPERIMENT_KNOBS.py`.

## Operating Rule

The system tries to deliver 100 MW every hour.

- If wind is at least 100 MW, send 100 MW directly, charge storage from extra wind, and curtail what cannot be charged.
- If wind is below 100 MW, send all wind directly and discharge storage toward the 100 MW target.
- Price is not used to choose the action. It is used only afterward to score realized value.

## Frozen Configuration

| Parameter | Value |
| --- | ---: |
| Storage power | 100 MW charge / 100 MW discharge |
| Storage duration / capacity | 10 h / 1,000 MWh |
| SoC bounds | 200-1,000 MWh |
| Initial SoC | 600 MWh |
| Annual and final SoC target | 600 MWh |
| Annual target corridor | Last 720 hours of each completed year |
| RTE | 0.55, applied on discharge |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |

The controller remains chronological. It does not reset SoC at year boundaries;
it physically schedules charge/discharge so the realized year-end state reaches
600 MWh.

## Controlled Full-Period Result

From
`results/frozen_controlled/constant_output_baseload_100mw_2014_2023_summary.csv`:

| Field | Value |
| --- | ---: |
| Evaluation period | 2014-01-01 00:00 to 2023-12-23 05:00 |
| Hours | 87,417 |
| Raw realized revenue | $210,880,185.44 |
| Normalized price-weighted revenue metric | 5,962,774.41 |
| COVE index | 8.622953 |
| Initial / final SoC | 600 / 600 MWh |
| Minimum / maximum SoC | 200 / 1,000 MWh |
| Completed year-end targets | 9 |
| Annual target violations | 0 |
| Physical QA violations | 0 |

The COVE numerator is the frozen annualized wind-plus-100 MW CAES cost of
$51,416,725. All Step 2-4 same-storage COVE values use this same numerator.

## Outputs

```text
results/frozen_controlled/constant_output_baseload_100mw_2014_2023_hourly.csv
results/frozen_controlled/constant_output_baseload_100mw_2014_2023_summary.csv
results/frozen_controlled/constant_output_baseload_100mw_2014_2023_metadata.json
```

The hourly CSV records direct wind, charge, discharge, delivered power,
curtailment, shortfall, SoC before/after, both price measures, both revenue
measures, and annual-target control fields for every evaluated hour.

## Figures

| Figure | What it shows |
| --- | --- |
| `step0_100mw_baseload_2014_2023_example_week.png` | A representative week of actual wind, delivered power, the 100 MW target, and chronological SoC. |
| `step0_energy_flow_totals.png` | Full-period delivered, charged, discharged, curtailed, and shortfall energy. |
| `step0_soc_duration_curve.png` | How often the benchmark operated at each stored-energy level. |
| `step0_annual_raw_revenue.png` | Raw realized revenue for each evaluation year. |

## Code Map

| File | Role |
| --- | --- |
| `RUN_0_100MW_BASELOAD.py` | Front door: runs or displays the benchmark and prints QA. |
| `EXPERIMENT_KNOBS.py` | User-editable storage, period, target, and output settings. |
| `code/build_100mw_baseload_reference.py` | Applies the chronological 100 MW operating rule and writes full-period outputs. |
| `../common/annual_soc.py` | Builds feasible target corridors without resetting or creating energy. |
| `../common/metrics.py` | One canonical annualized-cost and COVE definition. |

Wind-only/no-storage remains a secondary reference in Steps 2-4. It is not the
primary same-storage benchmark.
