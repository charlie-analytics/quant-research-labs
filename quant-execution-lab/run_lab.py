"""Bounded synthetic run; no network access."""
import argparse,hashlib,json,platform,statistics,time
from pathlib import Path
from engine import Simulator
from scenarios import scenarios

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(output):
    root=Path(__file__).resolve().parent;out=Path(output)
    if out.exists():raise ValueError('New output directory required')
    out.mkdir(parents=True)
    fixture=scenarios();results=[]
    for name,events in fixture.items():
        for delay in (1,5,15):
            for policy in ('conservative','optimistic'):
                for allocation in ('fifo','pro_rata'):
                    s=Simulator(latency_us=delay,cancel_policy=policy,allocation=allocation).run(events)
                    results.append({'scenario':name,**s.result()})
    data={'classification':'SYNTHETIC_DEMONSTRATION_ONLY','version':'0.1.0',
          'fixture_scenarios':len(fixture),'configurations':len(results),'fixture_tests':26,
          'time_units':'hypothetical microseconds; not measured network/exchange latency',
          'price_units':'synthetic integer ticks, tick value 1 currency unit, multiplier 1',
          'fee_bps_assumed':1,'inventory_cap_units':5,
          'tie_rule':'Input tape/decisions precede modeled arrivals at equal time; tape wins same-time cancel race.',
          'markout_rule':'First observed synthetic mid at/after requested horizon; actual delay recorded. No later mid means unknown.',
          'limitations':['Hand-authored synthetic events and assumed delays are not real-market calibration.',
                         'Only one active own order per side at current top of book; deeper quotes are rejected.',
                         'No hidden liquidity, self-market impact or venue-specific priority calibration.',
                         'Conservative depth cancellations do not reduce queue-ahead; optimistic mode assumes they do.',
                         'Pro-rata mode is a simplified integer-floor illustration, not CME/Kraken allocation.',
                         'Gap makes existing order/queue state unresolved and prevents complete P&L claims.',
                         'Inventory skew helper is tested but not a calibrated autonomous quoting strategy.',
                         'No HFT employment, colocation, kernel-bypass or trading-performance claim.'],
          'fixtures':fixture,'results':results}
    (out/'results.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    manifest={'classification':data['classification'],'python':platform.python_version(),
              'source_sha256':{p.name:digest(p) for p in root.glob('*.py')},
              'fixtures_sha256':hashlib.sha256(json.dumps(fixture,sort_keys=True).encode()).hexdigest(),
              'results_sha256':digest(out/'results.json'),'no_network':True}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    timings=[]
    for _ in range(1000):
        begin=time.perf_counter_ns();Simulator().run(fixture['queue_then_partial']);timings.append((time.perf_counter_ns()-begin)/1000)
    host={'classification':'MEASURED_HOST_PYTHON_REPLAY_RUNTIME_ONLY','trials':len(timings),
          'median_us':statistics.median(timings),'p95_us':sorted(timings)[949],
          'scope':'One tiny synthetic replay. Excludes feed/network/exchange latency, timestamp accuracy and serialization. Not colocated HFT evidence.'}
    (out/'host_runtime.json').write_text(json.dumps(host,indent=2)+'\n')
    print(json.dumps({'fixture_scenarios':len(fixture),'configurations':len(results),'results_sha256':manifest['results_sha256'],'output':str(out)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();run(a.output)
