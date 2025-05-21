# File: profit_report.py
"""
Simple script to calculate total P&L from your live trades log (data/trades.csv).
Usage:
    python3 profit_report.py
"""
import csv
import os

DATA_FILE = os.path.join("data", "trades.csv")

def load_trades(path):
    trades = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            side = row['side']
            price = float(row['price'])
            amount = float(row['amount'])
            cost = float(row['cost'])
            # For buys, cost is negative (spent); for sells, positive (received)
            signed_cost = cost if side.lower() == 'sell' else -cost
            trades.append(signed_cost)
    return trades


def main():
    if not os.path.exists(DATA_FILE):
        print(f"No trades file found at '{DATA_FILE}'. Run the bot and generate some trades first.")
        return

    signed_costs = load_trades(DATA_FILE)
    total_pnl = sum(signed_costs)

    print(f"Total P&L: {total_pnl:.2f} USDT over {len(signed_costs)} trades")

if __name__ == '__main__':
    main()
