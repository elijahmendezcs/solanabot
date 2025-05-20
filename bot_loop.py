# bot_loop.py

import time
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

from sma_signal import init_exchange, fetch_ohlcv, generate_signal

# ─── Configuration ─────────────────────────────────────────────────────────────
SYMBOL            = "SOL/USDT"
FAST_PERIOD       = 10
SLOW_PERIOD       = 30
USDT_AMOUNT       = 10.0
CSV_PATH          = "trades.csv"
LOOP_INTERVAL_SEC = 60
# ────────────────────────────────────────────────────────────────────────────────

def ensure_csv():
    """Create the CSV with headers if it doesn't exist yet."""
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "side", "price", "amount", "cost"])

def main():
    load_dotenv()
    exchange = init_exchange()
    ensure_csv()
    print("▶️ Starting trading loop...")

    while True:
        try:
            # 1) Get just enough bars
            limit = SLOW_PERIOD + 1
            bars  = fetch_ohlcv(symbol=SYMBOL, limit=limit)
            closes = [b[4] for b in bars]

            # 2) Generate signal
            sig   = generate_signal(closes, fast=FAST_PERIOD, slow=SLOW_PERIOD)
            price = closes[-1]

            # 3) Act on signal
            if sig == "buy":
                size = float(exchange.amount_to_precision(SYMBOL, USDT_AMOUNT / price))
                order = exchange.create_market_buy_order(SYMBOL, size)
                cost  = order.get("cost", price * size)
                with open(CSV_PATH, "a", newline="") as f:
                    csv.writer(f).writerow([
                        datetime.utcnow().isoformat(), sig, price, size, cost
                    ])
                print(f"{datetime.utcnow().isoformat()} BUY  {size} @ {price:.2f}")

            elif sig == "sell":
                bal   = exchange.fetch_balance()
                asset = SYMBOL.split("/")[0]
                amt   = bal["free"].get(asset, 0)
                if amt > 0:
                    size  = float(exchange.amount_to_precision(SYMBOL, amt))
                    order = exchange.create_market_sell_order(SYMBOL, size)
                    cost  = order.get("cost", price * size)
                    with open(CSV_PATH, "a", newline="") as f:
                        csv.writer(f).writerow([
                            datetime.utcnow().isoformat(), sig, price, size, cost
                        ])
                    print(f"{datetime.utcnow().isoformat()} SELL {size} @ {price:.2f}")

            else:
                print(f"{datetime.utcnow().isoformat()} No signal")

        except Exception as e:
            # log and continue on error
            print(f"{datetime.utcnow().isoformat()} ERROR:", e)

        # wait for next cycle
        time.sleep(LOOP_INTERVAL_SEC)

if __name__ == "__main__":
    main()
