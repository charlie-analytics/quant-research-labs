(function(root){'use strict';
const model=typeof module!=='undefined'?require('./options'):root.IndiaOptions;
function payoff(terminal,legs,costs=0){
 if(!Number.isFinite(terminal)||terminal<0||!Number.isFinite(costs)||costs<0||!legs.length)throw Error('Invalid payoff assumptions');
 let net=-costs;for(const l of legs){if(!['call','put'].includes(l.type)||![l.strike,l.qty,l.premium].every(Number.isFinite)||l.strike<=0||l.qty===0||l.premium<0)throw Error('Invalid option leg');net+=l.qty*(Math.max(0,(l.type==='call'?1:-1)*(terminal-l.strike))-l.premium);}
 if(!Number.isFinite(net))throw Error('Nonfinite payoff');return net;
}
function scenario(spot=104,days=7,vol=.15,type='call'){
 if(!Number.isFinite(days)||days<0||days>30)throw Error('Remaining days must be 0–30');
 const entry=model.price(100,100,30/365,.4,.03,0,type);
 const current=model.price(spot,100,days/365,vol,.03,0,type);
 return {classification:'SYNTHETIC_ASSUMPTIONS_NOT_MARKET_QUOTES',entry:{spot:100,strike:100,days:30,vol:.4,rate:.03,dividend:0,type,premium:entry.value},current:{spot,days,vol,...current},pnl:current.value-entry.value,
 expiry:Array.from({length:41},(_,i)=>({spot:80+i,pnl:payoff(80+i,[{type,strike:100,qty:1,premium:entry.value}])}))};
}
const api={payoff,scenario};if(typeof module!=='undefined')module.exports=api;else root.OptionsLab=api;
})(typeof window!=='undefined'?window:globalThis);
