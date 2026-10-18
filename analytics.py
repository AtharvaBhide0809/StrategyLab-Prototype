"""Derived statistics for completed trade records (simulation amounts, not live trading)."""

def trade_metrics(trades):
    pnl=[float(t['pnl']) for t in trades if t['side']=='SELL' and t.get('pnl') is not None]
    gains=[v for v in pnl if v>0];losses=[v for v in pnl if v<0]
    gross_profit=sum(gains);gross_loss=-sum(losses)
    return dict(pnl=pnl,gross_profit=gross_profit,gross_loss=gross_loss,
                net_pnl=sum(pnl),profit_factor=gross_profit/gross_loss if gross_loss else None,
                expectancy=sum(pnl)/len(pnl) if pnl else None,
                winners=len(gains),losers=len(losses),breakeven=len(pnl)-len(gains)-len(losses))
