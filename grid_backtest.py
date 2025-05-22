# File: grid_backtest.py

import statistics
from exchange import fetch_ohlcv
from config import SYMBOL, TIMEFRAME, FEE_PCT, SLIPPAGE_PCT


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


def run_backtest(closes, fast, slow):
    pnl, trades, position, entry_cost = 0.0, 0, 0, 0.0
    for price in closes[slow:]:
        sig = generate_signal(closes[: closes.index(price)+1], fast, slow)
        # Simulate buy
        if sig == "buy" and position == 0:
            entry_price_slipped = price * (1 + SLIPPAGE_PCT)
            entry_cost = entry_price_slipped * (1 + FEE_PCT)
            position = 1
        # Simulate sell
        elif sig == "sell" and position == 1:
            exit_price_slipped = price * (1 - SLIPPAGE_PCT)
            proceeds = exit_price_slipped * (1 - FEE_PCT)
            pnl += proceeds - entry_cost
            trades += 1
            position = 0
    # Close final position
    if position == 1:
        price = closes[-1]
        exit_price_slipped = price * (1 - SLIPPAGE_PCT)
        proceeds = exit_price_slipped * (1 - FEE_PCT)
        pnl += proceeds - entry_cost
        trades += 1
    return pnl, trades


def grid_search(fast_list, slow_list):
    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [b[4] for b in bars]
    results = []
    for fast in fast_list:
        for slow in slow_list:
            if slow <= fast:
                continue
            pnl, trades = run_backtest(closes, fast, slow)
            results.append({
                "fast": fast,
                "slow": slow,
                "pnl": pnl,
                "trades": trades
            })
    return results

if __name__ == "__main__":
    fast_periods = [5, 10, 15, 20]
    slow_periods = [30, 50, 100]

    results = grid_search(fast_periods, slow_periods)
    top = sorted(results, key=lambda x: x["pnl"], reverse=True)[:5]
    print("Top 5 SMA settings by P&L:")
    for r in top:
        print(f"FAST={r['fast']}, SLOW={r['slow']} → P&L={r['pnl']:.2f} over {r['trades']} trades")
