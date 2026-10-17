"""Hand-authored synthetic events. Times are hypothetical microseconds."""
def event(t,kind,**kw):return {'id':str(t)+'-'+kind+'-'+str(kw),'available_us':t,'kind':kind,'clock_domain':'synthetic_unified',**kw}
def book(t,bid=99,ask=101,q=10):return event(t,'book',bid=bid,ask=ask,bid_qty=q,ask_qty=q)
def submit(t=1,side='BUY',qty=3,price=99,oid='A'):return event(t,'submit',order_id=oid,side=side,qty=qty,price=price)
def trade(t,qty,side='SELL',price=99):return event(t,'trade',qty=qty,side=side,price=price)

def scenarios():
    return {
      'queue_then_partial':[book(0),submit(),trade(10,8),trade(12,4),trade(14,2),book(20,98,100),book(30,97,99)],
      'cancel_wins':[book(0),submit(),event(8,'cancel',order_id='A'),trade(15,20),book(25)],
      'fill_wins_cancel_race':[book(0),submit(),event(8,'cancel',order_id='A'),trade(11,20),book(20,96,98)],
      'late_order_misses_trade':[book(0),submit(),trade(3,20),book(20,98,100)],
      'depth_cancellation_uncertain':[book(0),submit(),event(8,'cancel_depth',side='BUY',price=99,qty=10),trade(10,3),book(20,97,99)],
      'sell_adverse_selection':[book(0),submit(side='SELL',price=101),trade(10,13,side='BUY',price=101),book(20,102,104)],
    }
