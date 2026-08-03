# Benchmark Definitions

## Primary Benchmark: 100-MW Constant-Output Baseload Benchmark

This is the main comparison for COVE reduction, revenue gain, and summary tables.

Required configuration:

| Setting | Value |
| --- | ---: |
| Target grid output | 100 MW |
| Storage power | 100 MW charge / 100 MW discharge |
| Storage capacity | 1,000 MWh |
| Minimum SoC | 200 MWh |
| Maximum SoC | 1,000 MWh |
| Initial SoC | 600 MWh |
| RTE | 55%, discharge-side |
| Grid export cap | 249 MW |
| Grid charging | Not allowed |
| Terminal equality | Not required; final SoC is reported |

Operating rule:

```text
If wind >= 100 MW:
  direct = 100
  charge = min(wind - 100, 100, 1000 - SoC)
  discharge = 0
  curtail = wind - direct - charge

If wind < 100 MW:
  direct = wind
  discharge = min(100 - wind, 100, (SoC - 200) * 0.55)
  charge = 0
  shortfall = max(0, 100 - direct - discharge)

SoC_next = SoC + charge - discharge / 0.55
```

## Secondary Reference: Wind-Only Baseline

Wind-only is not the main benchmark anymore. It is kept at the bottom of command
output for context.

```text
direct = min(actual wind, 249 MW)
charge = 0
discharge = 0
curtail = max(0, actual wind - 249 MW)
```

## Oracle Reference

Oracle means Gurobi is given actual future wind and actual future price. It is
not realistic, but it shows the value of perfect information.
