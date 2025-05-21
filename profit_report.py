# File: profit_report.py
"""
Simple script to calculate total P&L and average hold time
from your live trades log (data/trades.csv).
Assumes your CSV has columns: timestamp, side, price, amount, cost.

Usage:
    python3 profit_report.py
"""
import csv
import os
from datetime import datetime, timedelta

DATA_FILE = os.path.join("data", "trades.csv")

def load_trades(path):
    """
    Load trades from CSV and return a list of dicts:
      {
        'side': 'buy' or 'sell',
        'price': float,
        'amount': float,
        'cost': signed float,
        'timestamp': datetime
      }
    """
    trades = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            side = row['side'].strip().lower()
            price = float(row['price'])
            amount = float(row['amount'])
            cost = float(row['cost'])
            # buys are a cost (negative cash flow), sells are positive
            signed_cost = cost if side == 'sell' else -cost

            ts_str = row.get('timestamp')
            if not ts_str:
                raise ValueError("CSV missing a 'timestamp' column.")
            # try parsing ISO 8601; if ends with 'Z', replace so fromisoformat can handle it
            if ts_str.endswith('Z'):
                ts_str = ts_str.replace('Z', '+00:00')
            timestamp = datetime.fromisoformat(ts_str)

            trades.append({
                'side': side,
                'price': price,
                'amount': amount,
                'cost': signed_cost,
                'timestamp': timestamp
            })
    return trades

def compute_average_hold_time(trades):
    """
    Match each sell against prior buys (FIFO) and collect hold-duration.
    Returns a timedelta of the average hold time, or None if no full round-trips.
    """
    open_buys = []      # list of {'amount': float, 'timestamp': datetime}
    durations = []      # list of hold times in seconds

    for t in trades:
        if t['side'] == 'buy':
            open_buys.append({'amount': t['amount'], 'timestamp': t['timestamp']})
        elif t['side'] == 'sell':
            sell_amount = t['amount']
            sell_time = t['timestamp']
            # match sell to previous buys
            while sell_amount > 0 and open_buys:
                buy = open_buys[0]
                matched = min(buy['amount'], sell_amount)

                # record hold time for this chunk
                delta = sell_time - buy['timestamp']
                durations.append(delta.total_seconds())

                # decrement amounts
                buy['amount'] -= matched
                sell_amount   -= matched

                # if this buy fully matched, pop it
                if buy['amount'] == 0:
                    open_buys.pop(0)

            # if sell_amount > 0 after depleting buys, we ignore extra sells

    if not durations:
        return None

    avg_sec = sum(durations) / len(durations)
    return timedelta(seconds=avg_sec)

def main():
    if not os.path.exists(DATA_FILE):
        print(f"No trades file found at '{DATA_FILE}'. Run the bot and generate some trades first.")
        return

    trades = load_trades(DATA_FILE)
    total_pnl = sum(t['cost'] for t in trades)
    avg_hold = compute_average_hold_time(trades)

    print(f"Total P&L: {total_pnl:.2f} USDT over {len(trades)} trades")
    if avg_hold is not None:
        # human‐friendly formatting
        hours, rem = divmod(avg_hold.total_seconds(), 3600)
        minutes, seconds = divmod(rem, 60)
        print(f"Average hold time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    else:
        print("Average hold time: no closed round‐trips to compute hold time.")

if __name__ == '__main__':
    main()
