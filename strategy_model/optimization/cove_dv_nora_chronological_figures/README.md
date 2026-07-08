# COVE-DV Nora Chronological Figures

This folder contains figures from the COVE-DV experiment after switching to Nora-style chronological storage handling.

## Why This Matters

The battery state must carry forward in time. If each week starts from a fresh battery state, the model can accidentally create or lose stored energy between weeks. The chronological version fixes that by carrying the state of charge forward.

## Figures

| Figure | Meaning |
| --- | --- |
| `01_nora_chronological_cove_result.png` | COVE result with chronological storage |
| `02_nora_chronological_improvement.png` | Improvement percentage |
| `03_nora_chronological_training_curve.png` | Neural student training behavior |
| `04_nora_chronological_action_example_week.png` | Learned action signal |
| `05_nora_chronological_generation_price.png` | Generation and price over the example week |
| `06_nora_chronological_dispatch_example_week.png` | Dispatch output over the example week |
| `07_nora_chronological_storage_example_week.png` | Storage state of charge over the example week |
