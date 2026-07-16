# B6 Final Canonical Reproduction

This is the strict Chris-compatible benchmark package. Use this folder and these
Python files when the goal is reproducibility with no configuration mixing.

## What This Freezes

| Item | Frozen value |
| --- | --- |
| Year | 2020 only |
| Runs | A/B/C x Oracle/Causal = six runs |
| Power data | `data/processed/pyron_power.csv` |
| Price data | `data/raw/prices/12cfb125-8fa9-4401-8b0f-9d928544b721.csv` |
| Price node | PYR_PYRON1 |
| Price treatment | raw, uncapped, unnormalized USD/MWh |
| Primary metric | `sum(delivered_power_MW * actual_raw_price_USD_per_MWh)` |
| Storage type | CAES-equivalent |
| RTE | 0.55 |
| Grid export cap | 249 MW |
| Charging | wind-only; no grid charging |
| Causal planning horizon | 48 hours |
| Causal execution step | 24 hours |
| Minimum SoC | 20% of energy capacity |
| Initial SoC | 20% of energy capacity |
| Final realized annual SoC | 20% of energy capacity |
| Causal execution rule | retain planned direct wind; curtail leftover wind |

## Architectures

| Architecture | Power | Duration | Energy | 20% SoC target |
| --- | ---: | ---: | ---: | ---: |
| A | 100 MW | 6 h | 600 MWh | 120 MWh |
| B | 200 MW | 3 h | 600 MWh | 120 MWh |
| C | 100 MW | 10 h | 1000 MWh | 200 MWh |

## Run It

```bash
cd /Users/davidvalenta/deep-wind-model-dispatch
python strategy_model/optimization/B6_CANONICAL_RUNNER.py
python strategy_model/optimization/B6_FINAL_VALIDATE.py
```

The default output folder is:

```text
strategy_model/optimization/b6_final_results/
```

## Expected Final Summary From The Submitted Packet

| Run | Raw realized revenue |
| --- | ---: |
| A Oracle | $12,927,456.69 |
| A Causal | $8,181,454.34 |
| B Oracle | $13,810,058.70 |
| B Causal | $8,196,866.97 |
| C Oracle | $13,397,415.84 |
| C Causal | $8,399,203.77 |

Every final B6 run had 8,784 hourly rows, zero reported constraint violations,
and zero annual terminal SoC violations.

## Why Older Folders May Have Different Numbers

Older research folders in this repository include earlier experiments with
different storage durations, different horizons, COVE scoring, normalized/capped
price metrics, or exploratory scenario settings. They are useful research
history, but they are not the frozen B6 benchmark. For Chris/reviewer
reproduction, use the B6 runner and validator first.
