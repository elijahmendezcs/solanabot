# File: backtest.py

import argparse
from datetime import datetime

from exchange import fetch_ohlcv
from config import FAST_SMA, SLOW_SMA, TIMEFRAME, SYMBOL, FEE_PCT, SLIPPAGE_PCT
from utils.signals import generate_sma_signal


def run_backtest(fast, slow):
    """
    Run an SMA crossover backtest returning structured trade data and P&L.

    Returns:
        dict: {
            'trades': List[{
                'entry_index': int,
                'exit_index': int,
                'entry_price': float,
                'exit_price': float,
                'pnl': float
            }],
            'total_pnl': float
        }
    """
    print(f"Backtest run at {datetime.utcnow().isoformat()} UTC for FAST={fast}, SLOW={slow}")

    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [bar[4] for bar in bars]

    trades = []
    position = None  # None or 'long'
    entry_cost = entry_price = entry_index = None

    # Walk through bars
    for i in range(slow, len(closes)):
        window = closes[: i + 1]
        sig = generate_sma_signal(window, fast, slow)
        price = closes[i]

        # Enter long
        if sig == "buy" and position is None:
            slipped = price * (1 + SLIPPAGE_PCT)
            entry_cost = slipped * (1 + FEE_PCT)
            entry_price = price
            entry_index = i
            position = 'long'

        # Exit long
        elif sig == "sell" and position == 'long':
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

    # Close any open at last bar
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
    print(f"Total trades: {len(trades)}, Total P&L: {total_pnl:.2f} USDT")
    return {'trades': trades, 'total_pnl': total_pnl}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SMA backtest with structured output")
    parser.add_argument("fast", type=int, nargs="?", help="Fast SMA period (default from config)")
    parser.add_argument("slow", type=int, nargs="?", help="Slow SMA period (default from config)")
    args = parser.parse_args()

    fast = args.fast if args.fast is not None else FAST_SMA
    slow = args.slow if args.slow is not None else SLOW_SMA
    result = run_backtest(fast, slow)

    # Print each trade
    for t in result['trades']:
        print(f"Trade: entry@{t['entry_price']:.2f}(i={t['entry_index']}), "
              f"exit@{t['exit_price']:.2f}(i={t['exit_index']}), PnL={t['pnl']:.2f}")
