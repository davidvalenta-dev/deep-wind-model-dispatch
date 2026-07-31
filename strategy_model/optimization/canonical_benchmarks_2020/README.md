# Canonical Benchmarks 2020

This folder contains the July 2026 advisor-required benchmark/oracle outputs.

Runner:

```text
strategy_model/optimization/canonical_benchmark_oracle_runner.py
```

Run from the repository root:

```bash
./venv/bin/python strategy_model/optimization/canonical_benchmark_oracle_runner.py
```

Cases:

| Case | Purpose |
| --- | --- |
| `constant_output_baseload_100mw_2020` | Rule-based benchmark that tries to deliver exactly 100 MW every hour. |
| `oracle_rh_milp_24h_2020` | Perfect-information oracle MILP with 24-hour planning horizon and 1-hour execution. |
| `oracle_rh_milp_48h_2020` | Perfect-information oracle MILP with 48-hour planning horizon and 1-hour execution. |
| `oracle_rh_milp_168h_2020` | Perfect-information oracle MILP with 168-hour planning horizon and 1-hour execution. |

Important files:

| File | Meaning |
| --- | --- |
| `canonical_summary.csv` | Compact revenue, COVE, SoC, curtailment, shortfall, throughput, runtime, and violation summary. |
| `canonical_QA_report.csv` | Common and case-specific QA checks. |
| `experiment_registry.csv` | Registry rows for these canonical cases. |
| `canonical_run_metadata.json` | Data audit, commit, Gurobi version, and storage configuration. |
| `commands.txt` | Command used to regenerate the outputs. |
| `*_hourly.csv` | Full hourly output for each case. |

All hourly CSV files contain 8784 rows for the full 2020 leap year.

