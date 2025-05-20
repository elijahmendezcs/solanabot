# backtest.py

from sma_signal import fetch_ohlcv, generate_signal
from datetime import datetime

def run_backtest(fast=10, slow=30):
    # Pull ~500 minutes of history
    bars = fetch_ohlcv(limit=500)
    closes = [bar[4] for bar in bars]

    position    = 0      # 0 = flat, 1 = long
    entry_price = 0.0
    pnl         = 0.0

    # Start looping once we have at least `slow` data points
    for i in range(slow, len(closes)):
        window = closes[: i+1 ]
        sig    = generate_signal(window, fast=fast, slow=slow)
        price  = closes[i]

        if sig == "buy" and position == 0:
            position    = 1
            entry_price = price
            print(f"{i}: BUY  @ {price:.2f}")
        elif sig == "sell" and position == 1:
            trade_pnl = price - entry_price
            pnl      += trade_pnl
            print(f"{i}: SELL @ {price:.2f}, P&L = {trade_pnl:.2f}")
            position = 0

    # Close any open position at last price
    if position == 1:
        trade_pnl = closes[-1] - entry_price
        pnl      += trade_pnl
        print(f"Exit LAST @ {closes[-1]:.2f}, P&L = {trade_pnl:.2f}")

    print(f"\nTotal P&L over backtest: {pnl:.2f} USDT")

if __name__ == "__main__":
    print(f"Backtest run at {datetime.utcnow().isoformat()} UTC")
    run_backtest(fast=10, slow=30)
