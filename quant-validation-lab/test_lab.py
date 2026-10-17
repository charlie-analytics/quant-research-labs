import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import build_events, evaluate, fit, panels, run, select, sha256, validate


def fixture(n=180, symbols=8, flat=False):
    dates = pd.date_range("2020-01-01", periods=n, tz="UTC")
    rows = []
    for j in range(symbols):
        for i, ts in enumerate(dates):
            price = 100.0 if flat else 100 + i * (j+1) / 100
            rows.append((f"S{j}", ts, price, price+1, price-1, price, 1000))
    return pd.DataFrame(rows, columns=["symbol","ts","open","high","low","close","volume"]).set_index(["symbol","ts"])


class LabTests(unittest.TestCase):
    def test_duplicate_rejected(self):
        d=fixture(); self.assertRaises(ValueError,validate,pd.concat([d,d.iloc[:1]]))

    def test_invalid_price_and_ohlc_rejected(self):
        d=fixture();d.iloc[0,0]=0;self.assertRaises(ValueError,validate,d)
        d=fixture();d.iloc[0,1]=1;self.assertRaises(ValueError,validate,d)

    def test_nonfinite_rejected(self):
        d=fixture();d.iloc[0,0]=np.nan;self.assertRaises(ValueError,validate,d)

    def test_matched_clock_and_hand_calculation(self):
        d=validate(fixture()); e,_=build_events(d)
        first=e[e.signal_date==e.signal_date.min()]
        expected=[]
        for _,r in first.iterrows():
            bars=d.loc[r.symbol]
            self.assertEqual(r.entry_date,r.signal_date+pd.Timedelta(days=1))
            self.assertEqual(r.exit_date,r.entry_date+pd.Timedelta(days=5))
            v=(bars.loc[r.exit_date,'close']/bars.loc[r.entry_date,'open']-1)*100
            self.assertAlmostEqual(v,r.gross_pct,12);expected.append(v)
        self.assertAlmostEqual(first.iloc[0].benchmark_gross_pct,np.mean(expected),12)

    def test_flat_loses_exact_roundtrip_cost(self):
        e,_=build_events(validate(fixture(flat=True)))
        x,_=evaluate(e,'2020-04-01','2020-06-01',min_train_dates=3)
        self.assertTrue(np.allclose(x.net_pct,-0.25))
        self.assertTrue(np.allclose(x.net_excess_vs_net_benchmark_pct,0))

    def test_boundary_labels_purged(self):
        e,_=build_events(validate(fixture()))
        cut=e.signal_available.drop_duplicates().iloc[10]+pd.Timedelta(days=2)
        _,f=evaluate(e,cut,'2020-06-01',min_train_dates=3)
        self.assertGreater(f['purged_rows'],0)
        self.assertLess(pd.Timestamp(f['train_last_exit_available']),cut)

    def test_future_cannot_change_scores_or_training_selection(self):
        d=validate(fixture()); a,_=build_events(d)
        cut=pd.Timestamp('2020-04-01',tz='UTC')
        mask=d.index.get_level_values('ts')>=cut
        d.loc[mask,['open','high','low','close']]*=10
        b,_=build_events(validate(d))
        pd.testing.assert_frame_equal(a.loc[a.signal_available<cut,['symbol','signal_date','score']].reset_index(drop=True),
                                      b.loc[b.signal_available<cut,['symbol','signal_date','score']].reset_index(drop=True))
        _,fa=evaluate(a,cut,'2020-06-01',min_train_dates=3)
        _,fb=evaluate(b,cut,'2020-06-01',min_train_dates=3)
        self.assertEqual(fa['training_candidate_mean_excess_pp'],fb['training_candidate_mean_excess_pp'])
        self.assertEqual(fa['ranking_sign'],fb['ranking_sign'])

    def test_missing_endpoint_rejects_fixed_benchmark(self):
        d=fixture();target=pd.Timestamp('2020-01-27',tz='UTC')
        d=d.drop(('S0',target));e,r=build_events(validate(d))
        self.assertFalse((e.signal_date==pd.Timestamp('2020-01-21',tz='UTC')).any())
        self.assertIn('incomplete_fixed_benchmark',r.reason.tolist())

    def test_missing_interior_history_not_filled(self):
        d=fixture().drop(('S0',pd.Timestamp('2020-01-10',tz='UTC')))
        self.assertTrue(pd.isna(panels(validate(d))['close'].loc['2020-01-10','S0']))

    def test_equal_scores_have_stable_ties(self):
        e,_=build_events(validate(fixture(flat=True)))
        a=select(e,1,3);b=select(e.sample(frac=1,random_state=12),1,3)
        self.assertEqual(a.symbol.tolist(),b.symbol.tolist())

    def test_run_deterministic_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'data.parquet';fixture(1200).to_parquet(src)
            before=sha256(src)
            run(src,p/'a',[2022]);run(src,p/'b',[2022])
            self.assertEqual(before,sha256(src))
            for name in ['events.csv','folds.csv','summary.json','manifest.json','output_hashes.json']:
                self.assertEqual((p/'a'/name).read_bytes(),(p/'b'/name).read_bytes())
            self.assertRaises(ValueError,run,src,p/'a',[2022])


if __name__=='__main__': unittest.main(verbosity=2)
