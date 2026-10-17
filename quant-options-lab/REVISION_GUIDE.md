# Revise the Options & Volatility Lab

Read `lab.js` for the scenario and payoff wrapper, `options.js` for the reused model,
and `test_lab.js` for numerical checks. Run `node --test test_lab.js` before changes.
Use `node run.js runs/NEW-NAME` twice into separate new directories and compare results.
Keep previous runs and update manifests when code or assumptions change.

The separately maintained website builder writes the synthetic public page. Browser controls calculate locally
using the same copied model; no market data or account is contacted. Keep Greek units,
the distinction between interim value and expiry payoff, and the synthetic label visible.
Do not relabel the assumed volatility grid an observed implied-volatility surface.

Before publishing a revision, back up the current public allowlist and test controls,
keyboard errors and desktop/mobile layout. Never publish private paths, raw market
downloads, CVs, credentials or client material. No repository license was inferred:
source ownership/provenance review accompanies the eventual GitHub destination choice.

## Try this walkthrough

Keep current spot 104 and seven days remaining. Change volatility from 15% to 40%. Expected: higher long-call value. Actual: 4.0800 → 4.8394; modeled P&L −0.6110 → +0.1484 against the fixed 4.6910 entry premium. This demonstrates assumption sensitivity, not market pricing or a profitable trade.
