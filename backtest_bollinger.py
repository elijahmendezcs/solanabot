# File: backtest_bollinger.py

import argparse
from datetime import datetime

from exchange import fetch_ohlcv
from config import SYMBOL, TIMEFRAME, FEE_PCT, SLIPPAGE_PCT
from strategies.bollinger import BollingerStrategy

# ─── Dummy exchange for backtest ─────────────────────────────────────────────
class DummyExchange:
    def amount_to_precision(self, symbol, amount):
        # backtest precision not needed
        return amount

    def fetch_balance(self):
        # assume ample balance
        return {"free": {"USDT": 1_000_000.0, SYMBOL.split("/")[0]: 1_000_000.0}}


def run_backtest_bollinger():
    """
    Backtest the Bollinger Bands strategy, returning structured trades and total P&L.
    """
    print(f"Bollinger Backtest run at {datetime.utcnow().isoformat()} UTC")
    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [bar[4] for bar in bars]

    dummy_exch = DummyExchange()
    strat = BollingerStrategy(dummy_exch, {"symbol": SYMBOL})

    trades = []
    position = None
    entry_cost = entry_price = entry_index = None

    for i in range(len(bars)):
        sig = strat.on_bar(bars[:i+1])
        price = closes[i]

        # Enter long
        if sig and sig.get("side") == "buy" and position is None:
            slipped = price * (1 + SLIPPAGE_PCT)
            entry_cost = slipped * (1 + FEE_PCT)
            entry_price = price
            entry_index = i
            position = 'long'

        # Exit long
        elif sig and sig.get("side") == "sell" and position == 'long':
            slipped = price * (1 - SLIPPAGE_PCT)
            proceeds = slipped * (1 - FEE_PCT)
            pnl = proceeds - entry_cost
            trades.append({
                'entry_index': entry_index,
                'exit_index': i,
                'entry_price': entry_price,
                'exit_price': price,
                'pnl': pnl
            })
            position = None
            entry_cost = entry_price = entry_index = None

    # Close any open position at the end
    if position == 'long':
        price = closes[-1]
        slipped = price * (1 - SLIPPAGE_PCT)
        proceeds = slipped * (1 - FEE_PCT)
        pnl = proceeds - entry_cost
        trades.append({
            'entry_index': entry_index,
            'exit_index': len(closes) - 1,
            'entry_price': entry_price,
            'exit_price': price,
            'pnl': pnl
        })

    total_pnl = sum(t['pnl'] for t in trades)
    print(f"Bollinger: Total trades={len(trades)}, Total P&L={total_pnl:.2f} USDT")
    return {'trades': trades, 'total_pnl': total_pnl}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Bollinger Bands backtest with structured output"
    )
    args = parser.parse_args()

    result = run_backtest_bollinger()
    for t in result['trades']:
        print(
            f"Trade: entry@{t['entry_price']:.2f}(i={t['entry_index']}), "
            f"exit@{t['exit_price']:.2f}(i={t['exit_index']}), PnL={t['pnl']:.2f}"
        )
