# File: backtest.py

import argparse
import statistics
from datetime import datetime
from exchange import fetch_ohlcv
from config import FAST_SMA, SLOW_SMA, TIMEFRAME, SYMBOL, FEE_PCT, SLIPPAGE_PCT


def generate_signal(closes, fast, slow):
    """
    Given a list of closing prices, return "buy", "sell", or None
    based on a simple fast/slow SMA crossover.
    """
    if len(closes) < slow + 1:
        return None
    sma_fast_prev = statistics.mean(closes[-(fast+1):-1])
    sma_slow_prev = statistics.mean(closes[-(slow+1):-1])
    sma_fast_now  = statistics.mean(closes[-fast:])
    sma_slow_now  = statistics.mean(closes[-slow:])
    if sma_fast_prev <= sma_slow_prev and sma_fast_now > sma_slow_now:
        return "buy"
    if sma_fast_prev >= sma_slow_prev and sma_fast_now < sma_slow_now:
        return "sell"
    return None


def run_backtest(fast, slow):
    print(f"Backtest run at {datetime.utcnow().isoformat()} UTC for FAST={fast}, SLOW={slow}")

    # 1) Fetch ~500 1-m bars of history
    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [bar[4] for bar in bars]

    position   = 0       # 0 = flat, 1 = long
    entry_cost = 0.0     # cost basis including fee & slippage
    pnl        = 0.0

    # 2) Step through each bar
    for i in range(slow, len(closes)):
        window = closes[: i+1]
        sig    = generate_signal(window, fast, slow)
        price  = closes[i]

        # On buy, simulate slippage + fee
        if sig == "buy" and position == 0:
            entry_price_slipped = price * (1 + SLIPPAGE_PCT)
            entry_cost = entry_price_slipped * (1 + FEE_PCT)
            print(f"{i:3d}: BUY  @ {price:.2f}  (cost incl fee/slip: {entry_cost:.2f})")
            position = 1

        # On sell, simulate slippage + fee, compute P&L
        elif sig == "sell" and position == 1:
            exit_price_slipped = price * (1 - SLIPPAGE_PCT)
            proceeds = exit_price_slipped * (1 - FEE_PCT)
            trade_pnl = proceeds - entry_cost
            pnl += trade_pnl
            print(f"{i:3d}: SELL @ {price:.2f}, P&L = {trade_pnl:.2f} (proceeds incl fee/slip: {proceeds:.2f})")
            position = 0

    # 3) Close any remaining position at the last price
    if position == 1:
        price = closes[-1]
        exit_price_slipped = price * (1 - SLIPPAGE_PCT)
        proceeds = exit_price_slipped * (1 - FEE_PCT)
        trade_pnl = proceeds - entry_cost
        pnl += trade_pnl
        print(f"Exit LAST @ {price:.2f}, P&L = {trade_pnl:.2f}")

    print(f"\nTotal P&L over backtest: {pnl:.2f} USDT")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SMA backtest with fees/slippage")
    parser.add_argument("fast", type=int, nargs="?", help="Fast SMA period (default from config)")
    parser.add_argument("slow", type=int, nargs="?", help="Slow SMA period (default from config)")
    args = parser.parse_args()

    fast = args.fast if args.fast is not None else FAST_SMA
    slow = args.slow if args.slow is not None else SLOW_SMA
    run_backtest(fast, slow)
