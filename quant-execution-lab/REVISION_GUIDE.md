# Revise and understand this tool

1. Read `scenarios.py`: every event is invented and labeled synthetic. A book gives
   visible bid/ask size; submit creates a delayed order; trade consumes queue; cancel
   arrives later than its request. Times are hypothetical microseconds.
2. Read `engine.py`: input availability determines what can be known. A scheduled
   arrival makes an order eligible to rest. Queue ahead must clear before FIFO fills.
   Cancellation requests do not instantly remove resting orders. Cash and inventory
   update on each partial fill, with fees charged once per fill.
3. Run `python -m unittest -v test_engine`. A passing result verifies these mechanics
   against hand-calculated scenarios. It does not validate a real trading edge.
4. Run `run_lab.py` into a new directory. It saves 72 deterministic scenario/configuration
   results, hashes and a separate host-runtime observation. Keep earlier runs.
5. The separately maintained website builder exports only synthetic content. Change explanations here, preserving
   the synthetic label and assumptions. Check the dropdowns and trace at desktop/mobile
   widths. Do not add client history, real price downloads, credentials or private paths.
6. Existing route updates need only replace the allowlisted static files after a dated
   backup. A new route requires backed-up nginx configuration, `nginx -t`, graceful
   reload and health checks. Never expose the complete project directory.

To add a more realistic mechanism, first write a fixture that can fail: delayed cancel,
partial fill, priority change, missing data, adverse markout or inventory limit. Then
change the model until that fixture passes and repeat earlier tests. Do not tune a
result to become profitable. Update the version and assumptions whenever rules change.

Before real-data execution research, establish rights, sequence-complete books/matched
trades, exact venue allocation, instrument definitions and clock mapping. The 1.24-second
archive is only a parser smoke test. No recorded API ping establishes exchange location
or matching-engine latency; local Python timing measures host computation only.
