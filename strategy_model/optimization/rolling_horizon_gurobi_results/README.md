# Rolling-Horizon Gurobi Results

This folder contains the main constrained Gurobi dispatch results.

## Main Full-Dataset Result

| Item | Value |
| --- | ---: |
| Storage type | CAES |
| Power rating | 100 MW |
| Duration | 24 hours |
| Energy capacity | 2400 MWh |
| RTE | 55% |
| DoD | 80% |
| Grid cap | 249 MW |
| Step size | 24 hours |
| Best horizon tested | 168 hours |
| Baseload COVE | 1.743062 |
| Gurobi COVE | 1.165131 |
| COVE reduction | 33.16% |

## Key Files

| File or folder | Purpose |
| --- | --- |
| `paper_ready_key_results.csv` | Compact paper-ready result table |
| `best_full_dataset_caes_100mw_24h_summary.csv` | Full summary for the best full-dataset Gurobi run |
| `full_dataset_caes_100mw_24h_dod80_mid_soc/` | Full run summaries/windows |
| `horizon_comparison_full_43y/` | 24/48/72/168-hour perfect-information comparison |
| `forecast_backtest_2014_2023/` | Realistic forecast-driven horizon comparison |
| `forecast_backtest_robustness/` | Yearly statistics, confidence intervals, and sensitivities |
| `cove_dv_from_rolling_gurobi_caes_100mw_24h/` | Neural student trained from rolling Gurobi teacher labels |

## Figures In This Folder

- [Full dataset COVE by design](figure_01_full_dataset_cove_by_design.png)
- [Full dataset improvement vs baseload](figure_02_full_dataset_improvement_vs_baseload.png)
- [One-year storage sweep](figure_03_one_year_storage_sweep.png)
- [Best-case example week](figure_04_best_case_example_week.png)
- [COVE-DV training from Gurobi teacher](figure_05_cove_dv_training_from_gurobi_teacher.png)
