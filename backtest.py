# backtest.py

import statistics
from datetime import datetime
from exchange import fetch_ohlcv
from config import FAST_SMA, SLOW_SMA, TIMEFRAME, SYMBOL

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

def run_backtest(fast=FAST_SMA, slow=SLOW_SMA):
    print(f"Backtest run at {datetime.utcnow().isoformat()} UTC\n")

    # 1) Fetch ~500 1-m bars of history
    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [bar[4] for bar in bars]

    position    = 0      # 0 = flat, 1 = long
    entry_price = 0.0
    pnl         = 0.0

    # 2) Step through each bar once we have 'slow' points
    for i in range(slow, len(closes)):
        window = closes[: i+1 ]
        sig    = generate_signal(window, fast=fast, slow=slow)
        price  = closes[i]

        if sig == "buy"  and position == 0:
            position    = 1
            entry_price = price
            print(f"{i:3d}: BUY  @ {price:.2f}")
        elif sig == "sell" and position == 1:
            trade_pnl = price - entry_price
            pnl      += trade_pnl
            print(f"{i:3d}: SELL @ {price:.2f}, P&L = {trade_pnl:.2f}")
            position = 0

    # 3) Close any remaining position at the last price
    if position == 1:
        trade_pnl = closes[-1] - entry_price
        pnl      += trade_pnl
        print(f"Exit LAST @ {closes[-1]:.2f}, P&L = {trade_pnl:.2f}")

    print(f"\nTotal P&L over backtest: {pnl:.2f} USDT")

if __name__ == "__main__":
    run_backtest()
