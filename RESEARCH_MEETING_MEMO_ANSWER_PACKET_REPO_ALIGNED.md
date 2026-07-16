# Research Meeting Memo Answer Packet - Repo Aligned

This file aligns the July 16 research memo with the current repository layout.
Use it together with:

```bash
./venv/bin/python strategy_model/optimization/CHRIS_MEMO_CHECKLIST.py
./venv/bin/python strategy_model/optimization/REPO_REVIEWER_AUDIT.py
```

## Main Answer

The repository now separates the final reproducible benchmark from the broader
research history.

| Category | Status | Path |
| --- | --- | --- |
| Frozen benchmark | Canonical reviewer-safe result | `strategy_model/optimization/B6_CANONICAL_RUNNER.py` |
| Frozen benchmark validation | PASS | `strategy_model/optimization/B6_FINAL_VALIDATE.py` |
| Frozen benchmark outputs | Six hourly CSVs, summary, QA, logs | `strategy_model/optimization/b6_final_results/` |
| Chris memo checklist | All requested paths in one place | `strategy_model/optimization/CHRIS_MEMO_CHECKLIST.py` |
| Repo audit | Verifies required files and B6 QA | `strategy_model/optimization/REPO_REVIEWER_AUDIT.py` |
| Research history | Older deterministic/scenario/COVE-DV results | `strategy_model/optimization/` |

## Section 3 - Result Reconciliation

The B6 result is the frozen benchmark. Older deterministic, scenario, and COVE-DV
folders are research history unless explicitly rerun under the B6 rulebook.

| Result family | Use |
| --- | --- |
| B6 A/B/C Oracle/Causal | Final reproducible benchmark for Chris/reviewers |
| Deterministic horizon sweep | Research history showing forecast horizon behavior |
| Scenario dispatch | Research history showing uncertainty-aware dispatch potential |
| COVE-DV | Teacher-student ML research history |
| Nora weekly match | Constraint validation/history, not the full B6 benchmark |

## Section 5 - Methods and Recourse

The B6 runner follows the strict final rule:

```text
direct wind = min(planned direct wind,
                  actual wind remaining after executed charging,
                  grid capacity remaining after executed discharge)
```

Remaining actual wind is curtailment. This avoids the old mistake where the
realized execution could automatically sell extra wind that was not planned.

## Section 6 - Files to Open

| What Chris asks for | File |
| --- | --- |
| exact repo runner | `strategy_model/optimization/B6_CANONICAL_RUNNER.py` |
| exact QA workflow | `strategy_model/optimization/B6_FINAL_VALIDATE.py` |
| exact config and output | `strategy_model/optimization/b6_final_results/David_B6_frozen_config.json` |
| raw revenue table | `strategy_model/optimization/b6_final_results/David_B6_run_summary.csv` |
| QA table | `strategy_model/optimization/b6_final_results/David_B6_QA_summary.csv` |
| constraints | `strategy_model/optimization/NORA_PARAMETERS_AND_CONSTRAINTS.py` |
| memo map | `strategy_model/optimization/CHRIS_MEMO_CHECKLIST.py` |

## Section 8 - Decision Record

Current decision:

```text
B6 is canonical for reviewer reproduction.
Historical scenario and deterministic results stay in the repo,
but are not mixed with B6 unless rerun under B6 rules.
```

## B6 Numbers

| Run | Raw realized revenue | Final SoC | Rows | QA |
| --- | ---: | ---: | ---: | --- |
| A Oracle | $12,927,456.69 | 120 MWh | 8,784 | PASS |
| A Causal | $8,181,454.34 | 120 MWh | 8,784 | PASS |
| B Oracle | $13,810,058.70 | 120 MWh | 8,784 | PASS |
| B Causal | $8,196,866.97 | 120 MWh | 8,784 | PASS |
| C Oracle | $13,397,415.84 | 200 MWh | 8,784 | PASS |
| C Causal | $8,399,203.77 | 200 MWh | 8,784 | PASS |

## Reviewer Command Sequence

```bash
cd /Users/davidvalenta/deep-wind-model-dispatch
./venv/bin/python strategy_model/optimization/REPRODUCE_REVIEWER_RESULTS.py
./venv/bin/python strategy_model/optimization/B6_FINAL_VALIDATE.py
./venv/bin/python strategy_model/optimization/REPO_REVIEWER_AUDIT.py
```

To rebuild the six frozen cases:

```bash
./venv/bin/python strategy_model/optimization/B6_CANONICAL_RUNNER.py
```
