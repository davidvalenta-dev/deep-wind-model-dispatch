# Step 2 Source Code

Step 2 deliberately calls the same canonical controller used by Step 3:
`../../different scenarios/code/run_uncertainty_aware_dispatch.py`. This avoids
protocol drift. `../RUN_2_ROLLING_HORIZON.py` changes only horizon length,
collects the four rows, copies complete hourly outputs, and regenerates the
three current figures. Change settings only in `../EXPERIMENT_KNOBS.py`.
