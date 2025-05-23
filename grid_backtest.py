# File: grid_backtest.py

from exchange import fetch_ohlcv
from config import SYMBOL, TIMEFRAME
from utils.signals import generate_sma_signal

def run_backtest(closes, fast, slow, fee_pct, slippage_pct):
    trades = []
    position = None
    entry_cost = entry_price = entry_index = None

    for i in range(slow, len(closes)):
        window = closes[: i + 1]
        sig = generate_sma_signal(window, fast, slow)
        price = closes[i]

        if sig == "buy" and position is None:
            slipped = price * (1 + slippage_pct)
            entry_cost = slipped * (1 + fee_pct)
            entry_price = price
            entry_index = i
            position = 'long'

        elif sig == "sell" and position == 'long':
            slipped = price * (1 - slippage_pct)
            proceeds = slipped * (1 - fee_pct)
            pnl = proceeds - entry_cost
            trades.append(pnl)
            position = None
            entry_cost = entry_price = entry_index = None

    # Final close
    if position == 'long':
        price = closes[-1]
        slipped = price * (1 - slippage_pct)
        proceeds = slipped * (1 - fee_pct)
        pnl = proceeds - entry_cost
        trades.append(pnl)

    total_pnl = sum(trades)
    return total_pnl, len(trades)


def grid_search(fast_list, slow_list, fee_pct, slippage_pct):
    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [b[4] for b in bars]
    results = []

    for fast in fast_list:
        for slow in slow_list:
            if slow <= fast:
                continue
            pnl, count = run_backtest(closes, fast, slow, fee_pct, slippage_pct)
            results.append({
                "fast": fast,
                "slow": slow,
                "total_pnl": pnl,
                "trades_count": count
            })

    return results


if __name__ == "__main__":
    from config import FEE_PCT, SLIPPAGE_PCT

    fast_periods = [5, 10, 15, 20]
    slow_periods = [30, 50, 100]

    results = grid_search(fast_periods, slow_periods, FEE_PCT, SLIPPAGE_PCT)
    top = sorted(results, key=lambda x: x["total_pnl"], reverse=True)[:5]
    print("Top 5 SMA settings by P&L:")
    for r in top:
        print(f"FAST={r['fast']}, SLOW={r['slow']} → P&L={r['total_pnl']:.2f} over {r['trades_count']} trades")
