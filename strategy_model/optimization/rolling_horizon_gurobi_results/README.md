# Rolling-Horizon Gurobi Results

This folder contains the full-dataset rolling-horizon Gurobi/MIP results using Nora's dispatch constraints.

## Main result

Best full-dataset case found so far: **CAES, 100 MW, 24 hour duration**.

- Full dataset hours: 385572
- Horizon: 168 hours
- Step: 24 hours
- Terminal rule: SoC_final = SoC_initial inside each rolling lookahead window
- Baseload COVE: 1.743062
- Rolling Gurobi COVE: 1.165131
- Improvement over baseload: 33.16%
- Paper COVE-NN improvement reference: 32.3%
- Difference vs paper COVE-NN: 0.86 percentage points
- Max constraint violation: 4.093e-12

## Important comparison

The original CAES 100MW / 4h setup with rolling Gurobi improved COVE by 21.99% on the full dataset.
The tuned CAES 100MW / 24h setup improved COVE by 33.16%, slightly above the 32.3% COVE-NN improvement reported in the paper.

This is not yet a claim that COVE-DV beats COVE-NN. It is a stronger constrained optimization benchmark and storage-design result. The next neural-network step is to train COVE-DV using the best rolling-horizon Gurobi labels.


## COVE-DV student result

I also trained COVE-DV on the best full-dataset rolling-Gurobi labels.

- COVE-DV held-out test COVE: 12.035521
- COVE-DV held-out improvement: 29.10%
- Gurobi teacher on same test split COVE: 11.302790
- Gurobi teacher on same test split improvement: 33.41%

Interpretation: the student learned a useful policy, but the breakthrough result is currently the rolling-horizon Gurobi + storage-duration tuning benchmark, not the neural student. The student still has about 4.32 percentage points to close against its teacher on the held-out test split.
