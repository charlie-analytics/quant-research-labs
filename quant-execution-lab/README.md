# Order Book & Execution Research Simulator

Independent synthetic demonstration. No network client, exchange account, order API,
service, scheduler or new package. The host's installed Python and unittest run the
mechanics. The private archive-parser utility is not part of this source release.

    PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_engine
    PYTHONDONTWRITEBYTECODE=1 python run_lab.py --output runs/demo-v1
    PYTHONDONTWRITEBYTECODE=1 python run_lab.py --output runs/demo-v1-repeat

The output directory must be new. Compare `results.json` and `manifest.json` byte for
byte on repeat; `host_runtime.json` is intentionally variable measured host runtime.
26 unittest cases cover causal decisions, delayed arrival, cancel races, partial fills,
fees/cash/inventory, gap handling, allocation scenarios, adverse-selection markouts,
missing horizons and reproducibility. Six fixtures × three delays × two cancellation
assumptions × two allocation illustrations = 72 replay configurations, not 72 strategies.

Prices are integer synthetic ticks; quantity and cap are integer units; tick value and
contract multiplier are 1. Decimal arithmetic tracks cash/fees. Fee assumption is one
basis point per fill. Inventory is marked at final synthetic mid and separately valued
under crossing liquidation with fees. Neither is realized portfolio performance.

Only current-top passive quotes and one active own order per side are supported.
Inventory skew is a deterministic tested quote helper, not an autonomous market maker.
All fixture clocks are one explicit synthetic domain. Unknown real clock mappings are
rejected. Equal-time tape precedes arrivals/cancels. Receive availability is supplied;
no inbound network delay is added. Assumed computation/outbound delays remain separate
from the separately measured host Python replay runtime.

Depth cancellations never consume own orders. Conservative mode does not reduce queue
ahead; optimistic mode does. FIFO and simplified pro-rata are assumptions. A depth
snapshot cannot establish real queue priority or allocation. Any gap invalidates open
queue/order accounting even after a new snapshot; missing markouts stay unknown.

The private real archive was never used to infer fills. No new
public-data recording was attempted, so no new provider access/redistribution terms
are assumed. Public downloads contain only generated synthetic inputs/results.
