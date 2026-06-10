# COVE Result Summary

## Plain English

COVE is the project score for dispatch. Lower COVE is better.

The paper says the COVE-NN dispatch method beat the baseload method by about 32.3% overall.

I checked the repo. The repo does contain COVE experiments in:

- `strategy_model/src/model_exploration.ipynb`
- saved models in `strategy_model/test/`
- available dispatch data in `data/processed/dataset_2018-21_withloads.csv`

But the exact paper COVE result is not fully reproducible from the visible repo as-is.

## Paper Target

From the paper, the target result is:

| Result | Value |
| --- | ---: |
| Training COVE reduction | 32.4% |
| Validation COVE reduction | 32.1% |
| Overall COVE reduction | 32.3% |

This was for the paper's larger 43-year simulated Pyron dataset and the final COVE-NN dispatch setup.

## What The Repo Shows

The notebook's available-data results use `dataset_2018-21_withloads.csv`, which is about 4 years of data, not 43 years.

Best useful notebook result I found:

| Test Length | Method | COVE | Compared To Baseload |
| --- | --- | ---: | ---: |
| 1 year | Baseload | 0.0103903 | baseline |
| 1 year | best saved COVE-NN | 0.0103274 | 0.61% better |
| 4 years | Baseload | 0.00260687 | baseline |
| 4 years | best saved loads model | 0.00262532 | 0.71% worse |

So, with the data and saved models currently visible in this repo:

**I can reproduce small COVE notebook results, but I cannot reproduce the paper's 32.3% COVE improvement.**

I also ran a direct saved-model check across the available strategy model folders. Using the repo's simple COVE proxy, baseload had:

| Method | Revenue Proxy | COVE Proxy |
| --- | ---: | ---: |
| Baseload | 495,844.58 | 0.00000201676 |
| Best saved model found | 375,140.43 | 0.00000266567 |

That means the best saved model I found was about **32.2% worse than baseload** on this available-data proxy check.

## Why Not

The visible repo appears to be missing at least one of these:

- the exact 43-year simulated Pyron dataset used for the paper COVE result
- the exact final script that generated the paper's COVE table/figure
- the exact final trained COVE-NN model folder
- the full paper COVE cost calculation with CAPEX, OPEX, fixed charge rate, storage efficiency, storage capacity, and annual accounting

The current `strategy_model/src/util.py` version of COVE is much simpler:

```python
COVE = 1 / revenue
```

That is useful for experiments, but it is not the full paper equation.

## What To Tell Chris

Simple update:

> I reproduced the power-model table from the repo. For COVE, I found the saved notebook experiments and checked the available saved results. The repo shows small COVE improvements on some 1-year tests, but it does not reproduce the paper's 32.3% COVE result with the files currently present. The exact paper COVE run seems to need the original 43-year simulated Pyron dataset and/or the final evaluation script/model from Zach and Jessica.

## Questions For Zach/Jessica

Ask them:

1. Which script produced the paper's 32.3% COVE result?
2. Which saved model folder is the final COVE-NN model?
3. Where is the 43-year simulated Pyron dataset?
4. Where are the storage cost parameters used for the final COVE equation?
5. Was the final paper COVE calculation done outside this repo or in a notebook not included here?
