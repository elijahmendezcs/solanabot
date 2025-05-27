# File: grid_backtest.py

from exchange import fetch_ohlcv
from config import SYMBOL, TIMEFRAME
from utils.signals import generate_sma_signal

def run_backtest_detailed(closes, fast, slow, fee_pct, slippage_pct):
    """
    Run an SMA backtest and return a list of PnL values for each completed trade.
    """
    trades = []
    position = None
    entry_cost = entry_price = entry_index = None

    for i in range(slow, len(closes)):
        window = closes[: i + 1]
        sig = generate_sma_signal(window, fast, slow)
        price = closes[i]

        # Enter long
        if sig == "buy" and position is None:
            slipped     = price * (1 + slippage_pct)
            entry_cost  = slipped * (1 + fee_pct)
            entry_price = price
            entry_index = i
            position    = 'long'

        # Exit long
        elif sig == "sell" and position == 'long':
            slipped  = price * (1 - slippage_pct)
            proceeds = slipped * (1 - fee_pct)
            trades.append(proceeds - entry_cost)
            position = None
            entry_cost = entry_price = entry_index = None

    # Close any open at the end
    if position == 'long':
        price    = closes[-1]
        slipped  = price * (1 - slippage_pct)
        proceeds = slipped * (1 - fee_pct)
        trades.append(proceeds - entry_cost)

    return trades

def run_backtest(closes, fast, slow, fee_pct, slippage_pct):
    """
    Run backtest and return (total_pnl, trade_count).
    """
    pnls = run_backtest_detailed(closes, fast, slow, fee_pct, slippage_pct)
    return sum(pnls), len(pnls)

def grid_search(fast_list, slow_list, fee_pct, slippage_pct):
    """
    Original grid search: returns total PnL and trade count per (fast, slow).
    """
    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [b[4] for b in bars]
    results = []

    for fast in fast_list:
        for slow in slow_list:
            if slow <= fast:
                continue
            total_pnl, count = run_backtest(closes, fast, slow, fee_pct, slippage_pct)
            results.append({
                "fast": fast,
                "slow": slow,
                "total_pnl": total_pnl,
                "trades_count": count
            })

    return results

def grid_search_with_winrate(fast_list, slow_list, fee_pct, slippage_pct):
    """
    Extended grid search: adds win_rate to the results.
    """
    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    closes = [b[4] for b in bars]
    results = []

    for fast in fast_list:
        for slow in slow_list:
            if slow <= fast:
                continue
            pnls = run_backtest_detailed(closes, fast, slow, fee_pct, slippage_pct)
            total_pnl = sum(pnls)
            count     = len(pnls)
            wins      = sum(1 for p in pnls if p > 0)
            win_rate  = wins / count if count else 0.0

            results.append({
                "fast": fast,
                "slow": slow,
                "total_pnl": total_pnl,
                "trades_count": count,
                "win_rate": win_rate
            })

    return results

if __name__ == "__main__":
    from config import FEE_PCT, SLIPPAGE_PCT

    fast_periods = [5, 10, 15, 20]
    slow_periods = [30, 50, 100]

    # Top 5 by P&L
    results = grid_search(fast_periods, slow_periods, FEE_PCT, SLIPPAGE_PCT)
    top = sorted(results, key=lambda x: x["total_pnl"], reverse=True)[:5]
    print("Top 5 SMA settings by P&L:")
    for r in top:
        print(f"FAST={r['fast']}, SLOW={r['slow']} → P&L={r['total_pnl']:.2f} over {r['trades_count']} trades")

    # Top 5 by Win Rate
    wr_results = grid_search_with_winrate(fast_periods, slow_periods, FEE_PCT, SLIPPAGE_PCT)
    top_wr = sorted(wr_results, key=lambda x: x["win_rate"], reverse=True)[:5]
    print("\nTop 5 SMA settings by Win Rate:")
    for r in top_wr:
        print(f"FAST={r['fast']}, SLOW={r['slow']} → Win Rate={r['win_rate']:.2%} over {r['trades_count']} trades")
