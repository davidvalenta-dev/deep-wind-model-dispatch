# Real Results for Next Week

## 1. Reproduced Zach/Jessica COVE-NN result
- Baseload COVE: 102.388
- COVE-NN COVE: 69.320
- Improvement: 32.30%

## 2. Full-dataset SciPy optimizer benchmark
- Dataset: 385,572 hourly rows, 1980-2023 Pyron data
- Storage setup: CAES, 100 MW, 4 hours, RTE 0.550
- Baseload COVE: 2.306185
- SciPy optimized COVE: 1.323746
- Improvement: 42.60%

Important caveat: SciPy used historical future information and yearly chunks, so this is a teacher/benchmark result, not a deployable real-time controller.

## 3. Teacher-label neural-network experiment
- Original COVE-NN test COVE: 14.832572
- Fine-tuned COVE-NN test COVE: 14.831326
- SciPy teacher COVE on same split: 12.647042
- Fine-tuned model was technically better by 0.001246 COVE, but the improvement is tiny.

## Best honest claim
I reproduced the original COVE-NN result, generated full-dataset optimizer teacher labels, and ran an initial fine-tuning experiment. Fine-tuning slightly improved the original model on the same split, but the improvement is very small and needs stronger follow-up experiments.
