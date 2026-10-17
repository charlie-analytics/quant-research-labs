# Backtest validation

Retrospective daily event-study engine. Requires Python, NumPy, pandas and a Parquet reader already available in your own environment. No dataset is distributed. Tests create synthetic fixtures.

Run: `python -m unittest -v test_lab`. To analyse your own permitted dataset: `python lab.py --input YOUR_FILE.parquet --output runs/NEW --as-of YYYY-MM-DD`. Expected MultiIndex: symbol, ts (daily UTC), columns open/high/low/close/volume.

The website uses reused cached history whose provenance and extreme outlier remain unverified. It is not an untouched holdout, compounded portfolio, real execution result or reliable hit rate. Universe survivorship, missingness and selection bias remain unresolved.
