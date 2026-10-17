# Portfolio Risk Lab

Reuses the existing India `model.js` unchanged, including complete-case one-session
covariance, dynamic buy-and-hold variance attribution, beta and drawdown. A new wrapper
generates explicitly synthetic paths with controlled sample return correlation and
fixed starting weights. This is neither market history nor portfolio performance.

    node --test test_lab.js
    node run.js runs/demo-v1
    node run.js runs/demo-v1-repeat
    cmp runs/demo-v1/results.json runs/demo-v1-repeat/results.json

24 tests cover sample covariance, daily/annual units, risk-share reconciliation,
correlation versus capital concentration, scaling, missing sessions/endpoints,
duplicates, minimum sample gates, undefined beta/correlation, weights, drawdown,
same-date holdings overlap, overlapping horizons and reproducibility.

All returns are decimals at one synthetic weekday session. The 253-close path has
252 returns. Annualized volatility uses sqrt(252), not a crypto 365-day assumption.
Synthetic weekdays exclude weekends but are not a real exchange holiday calendar.
Initial allocations drift under buy-and-hold; this is not daily rebalancing. Capital
concentration is HHI of starting weights, not variance contribution. Negative risk
contributions are retained where present. No fees, liquidity, taxes, forecasts or
allocation recommendations. Overlapping returns are never passed as daily risk inputs.
