"""Synthetic event replay only. No network, accounts, or live orders."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
import heapq

D=lambda x: Decimal(str(x))

@dataclass
class Order:
    id: str
    side: str
    price: int
    qty: int
    remaining: int
    submitted_us: int
    arrival_us: int
    status: str = 'IN_FLIGHT'
    ahead: Decimal = Decimal(0)


class Simulator:
    def __init__(self, latency_us=5, cancel_latency_us=None, fee_bps=1, inventory_cap=5, compute_delay_us=0,
                 cancel_policy='conservative', allocation='fifo'):
        if latency_us<0 or compute_delay_us<0 or (cancel_latency_us is not None and cancel_latency_us<0):raise ValueError('Negative delay')
        if allocation not in ['fifo','pro_rata'] or cancel_policy not in ['conservative','optimistic']:
            raise ValueError('Unknown modeled allocation/cancellation policy')
        if inventory_cap<1 or D(fee_bps)<0:raise ValueError('Invalid risk/cost setting')
        self.latency=latency_us;self.compute=compute_delay_us;self.cancel_latency=latency_us if cancel_latency_us is None else cancel_latency_us
        self.fee=D(fee_bps);self.cap=inventory_cap;self.cancel_policy=cancel_policy;self.allocation=allocation
        self.orders={};self.fills=[];self.log=[];self.mids=[];self.book=None;self.valid=True
        self.cash=D(0);self.inventory=0;self.fees=D(0);self.queue=[];self.ordinal=0;self.complete=True

    def record(self,t,kind,**data):
        self.log.append({'time_us':t,'kind':kind,'inventory':self.inventory,
                         'cash':str(self.cash),'fees':str(self.fees),**data})

    def schedule(self,t,kind,data):
        self.ordinal+=1;heapq.heappush(self.queue,(t,1,self.ordinal,kind,data))

    def quote_prices(self,skew=True):
        if not self.book or not self.valid:raise ValueError('Unavailable book')
        # Educational inventory skew: lower both quotes when long, raise when short.
        shift=self.inventory if skew else 0
        return self.book['bid']-shift,self.book['ask']-shift

    def run(self,events):
        ids=set();last_seq={}
        for i,e in enumerate(events):
            if e.get('clock_domain','synthetic_unified')!='synthetic_unified':raise ValueError('No cross-clock mapping supplied')
            if e['id'] in ids:raise ValueError('Duplicate event id')
            ids.add(e['id']);t=e['available_us']
            if not isinstance(t,int) or t<0:raise ValueError('Invalid availability clock')
            if e['kind'] in ['trade','cancel_depth'] and (e.get('qty',0)<=0 or not isinstance(e.get('qty'),int)):
                raise ValueError('Positive integer market quantity required')
            if e['kind']=='book' and not (e['bid']<e['ask'] and e['bid']>0 and e['bid_qty']>=0 and e['ask_qty']>=0):
                raise ValueError('Invalid synthetic book')
            heapq.heappush(self.queue,(t,0,i,e['kind'],e))
        self.ordinal=len(events)
        while self.queue:
            t,_,_,kind,e=heapq.heappop(self.queue)
            if kind=='book':
                self.book={k:e[k] for k in ['bid','ask','bid_qty','ask_qty']}
                self.valid=True;self.mids.append((t,(D(e['bid'])+D(e['ask']))/2))
                self.record(t,'BOOK')
            elif kind=='gap':
                self.valid=False;self.complete=False
                for o in self.orders.values():
                    if o.status in ['IN_FLIGHT','RESTING','PARTIALLY_FILLED','CANCEL_PENDING']:o.status='UNRESOLVED_AFTER_GAP'
                self.record(t,'GAP')
            elif kind=='submit':
                oid=e['order_id'];side=e['side'];qty=e['qty'];price=e['price']
                if oid in self.orders:raise ValueError('Duplicate order id')
                if side not in ['BUY','SELL'] or not isinstance(qty,int) or qty<=0 or not isinstance(price,int) or price<=0:
                    raise ValueError('Invalid order')
                active=[o for o in self.orders.values() if o.side==side and o.status in ['IN_FLIGHT','RESTING','PARTIALLY_FILLED','CANCEL_PENDING']]
                sign=1 if side=='BUY' else -1
                if active or abs(self.inventory+sign*qty)>self.cap or not self.valid or self.book is None:
                    self.record(t,'REJECT_SUBMIT',order_id=oid,reason='active_side_or_inventory_or_data');continue
                o=Order(oid,side,price,qty,qty,t,t+self.compute+self.latency);self.orders[oid]=o
                self.schedule(o.arrival_us,'arrival',{'order_id':oid});self.record(t,'SUBMIT',order_id=oid,arrival_us=o.arrival_us)
            elif kind=='arrival':
                o=self.orders[e['order_id']]
                if o.status=='UNRESOLVED_AFTER_GAP':continue
                if not self.valid or self.book is None:
                    o.status='REJECTED';self.record(t,'REJECT_ARRIVAL',order_id=o.id);continue
                crossing=o.price>=self.book['ask'] if o.side=='BUY' else o.price<=self.book['bid']
                if crossing:o.status='REJECTED';self.record(t,'REJECT_PASSIVE_CROSS',order_id=o.id);continue
                key='bid' if o.side=='BUY' else 'ask'
                # Only modeled top-of-book passive orders are supported.
                if o.price!=self.book[key]:o.status='REJECTED';self.record(t,'REJECT_NON_TOP',order_id=o.id);continue
                o.ahead=D(self.book[key+'_qty']);o.status='RESTING';self.record(t,'RESTING',order_id=o.id,ahead=str(o.ahead))
            elif kind=='cancel':
                o=self.orders.get(e['order_id'])
                if o and o.status in ['RESTING','PARTIALLY_FILLED']:
                    o.status='CANCEL_PENDING';self.schedule(t+self.cancel_latency,'cancel_arrival',{'order_id':o.id});self.record(t,'CANCEL_REQUEST',order_id=o.id)
                else:self.record(t,'CANCEL_IGNORED',order_id=e['order_id'])
            elif kind=='cancel_arrival':
                o=self.orders[e['order_id']]
                if o.status=='CANCEL_PENDING':o.status='CANCELLED';self.record(t,'CANCELLED',order_id=o.id)
                else:self.record(t,'LATE_CANCEL',order_id=o.id)
            elif kind in ['trade','cancel_depth']:
                if not self.valid or not self.book:self.record(t,'UNKNOWN_MARKET_EVENT',reason='gap_or_no_book');continue
                if e['side'] not in ['BUY','SELL']:raise ValueError('Invalid aggressor/depth side')
                # Trade side is aggressor; cancellation side names resting book side.
                side=('BUY' if e['side']=='SELL' else 'SELL') if kind=='trade' else e['side']
                key='bid' if side=='BUY' else 'ask';qty=D(e['qty'])
                if e['price']!=self.book[key]:self.record(t,'OUT_OF_SCOPE_PRICE');continue
                for o in self.orders.values():
                    if o.side!=side or o.price!=e['price'] or o.status not in ['RESTING','PARTIALLY_FILLED','CANCEL_PENDING']:continue
                    if kind=='cancel_depth':
                        if self.cancel_policy=='optimistic':o.ahead=max(D(0),o.ahead-qty)
                        self.record(t,'DEPTH_CANCEL_ASSUMPTION',order_id=o.id,ahead=str(o.ahead));continue
                    old_ahead=o.ahead
                    if self.allocation=='fifo':
                        amount=min(D(o.remaining),max(D(0),qty-old_ahead));o.ahead=max(D(0),old_ahead-qty)
                    else:
                        # Hypothetical pro-rata, integer floor; not a venue calibration.
                        amount=min(D(o.remaining),D(int(qty*o.remaining/(old_ahead+o.remaining))))
                        o.ahead=max(D(0),old_ahead-max(D(0),qty-amount))
                    fill=int(amount)
                    self.record(t,'QUEUE_PROGRESS',order_id=o.id,ahead_before=str(old_ahead),ahead_after=str(o.ahead),modeled_fill_qty=fill)
                    if fill:
                        sign=1 if o.side=='BUY' else -1
                        fee=D(fill)*o.price*self.fee/10000
                        self.cash-=sign*D(fill)*o.price+fee;self.inventory+=sign*fill;self.fees+=fee;o.remaining-=fill
                        pending=o.status=='CANCEL_PENDING'
                        o.status='FILLED' if not o.remaining else 'CANCEL_PENDING' if pending else 'PARTIALLY_FILLED'
                        self.fills.append({'time_us':t,'order_id':o.id,'side':o.side,'qty':fill,'price':o.price,'fee':str(fee)})
                        self.record(t,'FILL',order_id=o.id,qty=fill,remaining=o.remaining)
                        assert abs(self.inventory)<=self.cap
                self.book[key+'_qty']=max(0,self.book[key+'_qty']-e['qty'])
                self.record(t,'TRADE' if kind=='trade' else 'DEPTH_CANCEL',qty=e['qty'])
            else:raise ValueError('Unknown event kind')
        return self

    def markouts(self,horizons=(5,10)):
        out=[]
        for f in self.fills:
            for h in horizons:
                candidates=[(t,m) for t,m in self.mids if t>=f['time_us']+h]
                row={**f,'horizon_us':h,'mark_time_us':None,'observation_delay_us':None,'signed_markout':None}
                if candidates:
                    t,mid=candidates[0];sign=1 if f['side']=='BUY' else -1
                    gaps=[x for x in self.log if x['kind']=='GAP' and f['time_us']<=x['time_us']<=t]
                    if not gaps:row.update(mark_time_us=t,observation_delay_us=t-f['time_us']-h,signed_markout=str(sign*(mid-f['price'])*f['qty']))
                out.append(row)
        return out

    def result(self):
        mid=self.mids[-1][1] if self.mids else None
        marked=self.cash+self.inventory*mid if mid is not None and self.complete else None
        # Explicit crossing liquidation, observed synthetic final spread + fee; no impact.
        liquidation=None
        if self.book and self.valid and self.complete:
            px=self.book['bid'] if self.inventory>0 else self.book['ask']
            liquidation=self.cash+self.inventory*D(px)-abs(self.inventory)*D(px)*self.fee/10000
        return {'classification':'SYNTHETIC_NOT_REAL_MARKET_CALIBRATED','latency_us_assumed':self.latency,
                'compute_delay_us_assumed':self.compute,'accounting_complete':self.complete,
                'cancel_latency_us_assumed':self.cancel_latency,'allocation_assumed':self.allocation,
                'queue_cancel_policy':self.cancel_policy,'inventory':self.inventory,'cash':str(self.cash),
                'fees':str(self.fees),'marked_pnl':str(marked) if marked is not None else None,
                'liquidation_scenario_pnl':str(liquidation) if liquidation is not None else None,
                'fills':self.fills,'markouts':self.markouts(),'orders':[asdict(o)|{'ahead':str(o.ahead)} for o in self.orders.values()],
                'decisions':self.log}
