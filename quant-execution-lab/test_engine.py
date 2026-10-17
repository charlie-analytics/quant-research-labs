import unittest
from decimal import Decimal
from engine import Simulator
from scenarios import event,book,submit,trade,scenarios

class Mechanics(unittest.TestCase):
    def test_queue_before_own_partial_and_full_fill(self):
        s=Simulator().run(scenarios()['queue_then_partial']);self.assertEqual([f['qty'] for f in s.fills],[2,1]);self.assertEqual(s.orders['A'].remaining,0)
    def test_no_fill_before_order_arrival(self):
        s=Simulator(latency_us=5).run(scenarios()['late_order_misses_trade']);self.assertEqual(s.fills,[])
    def test_cancel_arrival_wins(self):
        s=Simulator(cancel_latency_us=2).run(scenarios()['cancel_wins']);self.assertEqual(s.fills,[]);self.assertEqual(s.orders['A'].status,'CANCELLED')
    def test_fill_can_win_cancel_race(self):
        s=Simulator(cancel_latency_us=5).run(scenarios()['fill_wins_cancel_race']);self.assertEqual(sum(f['qty'] for f in s.fills),3);self.assertEqual(s.orders['A'].status,'FILLED')
    def test_same_time_tape_before_cancel_is_explicit(self):
        e=[book(0),submit(),event(8,'cancel',order_id='A'),trade(13,13)];s=Simulator(cancel_latency_us=5).run(e);self.assertEqual(s.orders['A'].status,'FILLED')
    def test_conservative_cancel_does_not_imply_fill(self):
        s=Simulator().run(scenarios()['depth_cancellation_uncertain']);self.assertEqual(s.fills,[])
    def test_optimistic_cancel_is_separate_assumption(self):
        s=Simulator(cancel_policy='optimistic').run(scenarios()['depth_cancellation_uncertain']);self.assertEqual(sum(f['qty'] for f in s.fills),3)
    def test_allocation_policy_changes_fill(self):
        e=[book(0),submit(),trade(10,8)];a=Simulator().run(e);b=Simulator(allocation='pro_rata').run(e);self.assertEqual(len(a.fills),0);self.assertEqual(b.fills[0]['qty'],1)
    def test_inventory_cap_rejects_order(self):
        s=Simulator(inventory_cap=2).run([book(0),submit()]);self.assertEqual(s.orders,{});self.assertEqual(s.log[-1]['kind'],'REJECT_SUBMIT')
    def test_cash_inventory_fee_identity(self):
        s=Simulator(fee_bps=1).run([book(0),submit(),trade(10,13)]);self.assertEqual(s.inventory,3);self.assertEqual(s.fees,Decimal('0.0297'));self.assertEqual(s.cash,Decimal('-297.0297'));self.assertEqual(s.result()['marked_pnl'],'2.9703')
    def test_buy_adverse_markout_negative(self):
        s=Simulator().run([book(0),submit(),trade(10,13),book(20,96,98)]);self.assertEqual(s.markouts()[0]['signed_markout'],'-6')
    def test_sell_adverse_markout_negative(self):
        s=Simulator().run(scenarios()['sell_adverse_selection']);self.assertEqual(s.markouts()[0]['signed_markout'],'-6')
    def test_missing_future_markout_is_unknown(self):
        s=Simulator().run([book(0),submit(),trade(10,13)]);self.assertIsNone(s.markouts()[0]['signed_markout'])
    def test_future_event_cannot_change_past_decisions(self):
        e=[book(0),submit(),trade(10,13)];a=Simulator().run(e);b=Simulator().run(e+[book(20,1,3)]);self.assertEqual(a.log,[x for x in b.log if x['time_us']<=10]);self.assertEqual(a.fills,b.fills)
    def test_gap_stops_inference(self):
        s=Simulator().run([book(0),submit(),event(8,'gap'),trade(10,20)]);self.assertEqual(s.fills,[]);self.assertIsNone(s.result()['liquidation_scenario_pnl'])
    def test_resnapshot_does_not_reconstruct_lost_queue(self):
        s=Simulator().run([book(0),submit(),event(8,'gap'),book(9),trade(10,20)]);self.assertEqual(s.fills,[]);self.assertFalse(s.result()['accounting_complete'])
    def test_gap_invalidates_markout(self):
        s=Simulator().run([book(0),submit(),trade(10,13),event(12,'gap'),book(20)]);self.assertIsNone(s.markouts()[0]['signed_markout'])
    def test_computation_delay_distinct_from_outbound_delay(self):
        s=Simulator(latency_us=2,compute_delay_us=4).run([book(0),submit(),trade(5,13)]);self.assertEqual(s.orders['A'].arrival_us,7);self.assertEqual(s.fills,[])
    def test_duplicate_event_rejected(self):
        e=book(0);self.assertRaises(ValueError,Simulator().run,[e,e])
    def test_mixed_clock_rejected(self):
        e=book(0);e['clock_domain']='exchange_unmapped';self.assertRaises(ValueError,Simulator().run,[e])
    def test_passive_cross_rejected(self):
        s=Simulator().run([book(0),submit(price=101)]);self.assertEqual(s.orders['A'].status,'REJECTED')
    def test_one_active_order_per_side_prevents_double_allocation(self):
        s=Simulator().run([book(0),submit(),submit(2,oid='B'),trade(10,20)]);self.assertEqual(len(s.orders),1);self.assertEqual(sum(x['qty'] for x in s.fills),3)
    def test_inventory_skew_direction(self):
        s=Simulator().run([book(0),submit(),trade(10,13)]);self.assertEqual(s.quote_prices(),(96,98));self.assertEqual(s.quote_prices(False),(99,101))
    def test_reproducible(self):
        e=scenarios()['queue_then_partial'];self.assertEqual(Simulator().run(e).result(),Simulator().run(e).result())
    def test_latency_only_changes_order_arrival(self):
        e=[book(0),submit(),trade(4,13),book(20)];a=Simulator(latency_us=1).run(e);b=Simulator(latency_us=5).run(e);self.assertEqual(len(a.fills),1);self.assertEqual(len(b.fills),0)
    def test_invalid_input_rejected(self):
        self.assertRaises(ValueError,Simulator,latency_us=-1);self.assertRaises(ValueError,Simulator().run,[book(0),trade(1,-1)])

if __name__=='__main__':unittest.main(verbosity=2)
