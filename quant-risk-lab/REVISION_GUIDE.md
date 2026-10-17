# Revise and explain Portfolio Risk Lab

`model.js` is the unchanged calculation engine. `lab.js` generates two fictional asset
paths plus a fictional benchmark, then calls the existing analysis. It also wraps
same-date holdings overlap and distinguishes overlapping from nonoverlapping horizons.

Run `node --test test_lab.js`, then `node run.js runs/NEW-NAME` into two new directories.
Compare results; preserve old runs. Change the fixture only with a new manifest/version.
The separately maintained website builder exports synthetic paths and generic model code only. Keep frequency,
covariance units, drift in weights and missing-data limits visible. Never label these
paths sourced market history or use them as a performance edge or recommendation.

## Try this

Keep initial A/B capital weights 60%/40%. Change sample return correlation from 0 to
0.9. Expected: less diversification and higher portfolio variation, while the capital
HHI stays at 0.52. Actual: annualized volatility 17.2772% → 23.2335%; drawdown −12.3195% → −14.4181%; A variance share 71.6822% → 60.5231%. This proves sensitivity of this fictional path, not next year's risk.

## Add real data later

Require permitted input, exact currency, adjustment treatment, exchange sessions,
membership/weight dates and frequencies. Missing endpoints fail; missing interior
sessions remove adjacent one-session intervals instead of creating multi-day returns.
Do not fill gaps or call overlapping windows independent observations. The original
India gate withholds risk below its sample requirement. No data collection is included.
