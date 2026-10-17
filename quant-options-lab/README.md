# Options & Volatility Lab

Synthetic assumptions, not observed quotes, positions or an implied-volatility surface.
Reuses the user's India European BSM `options.js` unchanged. It prices calls/puts,
dividends and Greeks. This wrapper adds defined-leg expiry payoff and an educational
time/volatility scenario. No network, new dependencies, accounts or live trading.

    node --test test_lab.js
    node run.js runs/demo-v1
    node run.js runs/demo-v1-repeat
    cmp runs/demo-v1/results.json runs/demo-v1-repeat/results.json

19 named tests: reference prices, parity, finite-difference Greeks with explicit units,
expiry and zero-volatility conventions, bounds, scaling, defined spreads, invalid and
overflow inputs, and a right-direction-but-negative-option-P&L case. 24 grid scenarios
are parameter combinations, not strategies or calibration evidence.

Entry is a theoretical 30-day ATM option, spot/strike 100, volatility 40%, rate 3%, no
dividend yield. Current spot/days/volatility are assumptions. Payoff subtracts premium;
interim theoretical value differs from expiry payoff. No fees/impact or early exercise,
discrete dividends, margin, assignment or realized execution is modeled. Greeks at
expiry and zero volatility are reported unknown by convention. Theta uses 365 calendar
days; volatility/rates are annual decimals; vega/rho are per percentage point.
