# Quant Research Labs

Four Charlie Quant Lab research demonstrations, prepared with AI assistance. They test numerical mechanics and assumptions, not a trading edge.

| Lab | Public demonstration | Tests |
|---|---|---|
| Backtest validation | https://charliequantlab.com/Backtest_Validity | 11 synthetic fixture tests |
| Order-book execution | https://charliequantlab.com/Order_Book_Execution | 26 tests; 72 synthetic configurations |
| Options and volatility | https://charliequantlab.com/Options_Volatility | 19 tests; 24 synthetic configurations |
| Portfolio risk | https://charliequantlab.com/Portfolio_Risk | 24 tests; 20 synthetic configurations |

Run Python tests inside their lab folder with `python -m unittest -v test_lab` or `python -m unittest -v test_engine`. Run JavaScript tests with `node --test test_lab.js`. The first lab requires existing pandas/NumPy; the execution lab uses Python standard library; JavaScript uses Node built-ins only. No automated installer is supplied.

No raw cached market history, private archive, client material, credentials, CVs, deployment configuration or paid-source data is included. The backtest engine accepts user-permitted input; its public historical result remains source-unvalidated and retrospective. Other demonstrations use invented fixtures only.

The options and portfolio models reuse the owner's India research modules unchanged. The public execution runner omits a private-path archive-parser utility; its synthetic simulation logic is unchanged. Test counts are fixture counts, not market predictions. No professional HFT, live-capital, profitability, complete implied-volatility-surface or autonomous-strategy claim is made.

See NUMERICAL_GUIDE.txt and each lab's README and revision guide. Website presentation and deployment scripts are outside this source release.
