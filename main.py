# File: main.py

import os
import csv
import time
from datetime import datetime

from exchange import init_exchange, fetch_ohlcv, place_order
from logger import setup_logger
from strategies.sma_crossover import SmaCrossover
from strategies.rsi import RsiStrategy
from config import LOOP_INTERVAL

# Path to the CSV file for logging trades
data_file = os.path.join("data", "trades.csv")

# Strategy configurations: add more entries here as needed
STRATEGY_CONFIGS = [
    {
        "class": SmaCrossover,
        "params": {"symbol": "SOL/USDT", "usdt_amount": 10.0, "fast": 10, "slow": 30},
    },
    {
        "class": RsiStrategy,
        "params": {
            "symbol":      "SOL/USDT",
            "usdt_amount": 10.0,
            "rsi_period":  2,    # super-short RSI
            "overbought":  50,   # mid-point
            "oversold":    50,   # mid-point so RSI is always “crossed"
        },
    },
]


def ensure_data_file():
    """Ensure data/trades.csv exists with a header row."""
    os.makedirs(os.path.dirname(data_file), exist_ok=True)
    if not os.path.exists(data_file):
        with open(data_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "side", "price", "amount", "cost"])


def log_trade(side, order):
    """Append a filled order to data/trades.csv."""
    timestamp = datetime.utcnow().isoformat()
    price     = float(order["price"])
    amount    = float(order["amount"])
    cost      = price * amount

    with open(data_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, side, price, amount, cost])


def main():
    # Prepare the data file
    ensure_data_file()

    log      = setup_logger()
    exchange = init_exchange()

    # Instantiate strategy objects
    strategies = [cfg["class"](exchange, cfg["params"]) for cfg in STRATEGY_CONFIGS]

    # Determine the maximum lookback needed
    max_period = max(
        getattr(s, "slow", 0) if hasattr(s, "slow") else s.config.get("rsi_period", 0)
        for s in strategies
    )
    ohlcv_limit = max_period + 1

    log.info("▶️ Starting multi-strategy engine…")
    while True:
        try:
            bars = fetch_ohlcv("SOL/USDT", timeframe="1m", limit=ohlcv_limit)
            last_price = bars[-1][4]
            log.info(f"Heartbeat — last price: {last_price}")  # log each loop

            for strat in strategies:
                sig = strat.on_bar(bars)
                if sig:
                    side  = sig["side"]
                    amt   = sig["amount"]
                    order = place_order(strat.config["symbol"], side, amt)

                    log.info(f"{strat.__class__.__name__}: {side.upper()} {amt} @ {order['price']}")
                    log_trade(side, order)

        except Exception as e:
            log.error("Engine error", exc_info=e)

        time.sleep(LOOP_INTERVAL)


if __name__ == "__main__":
    main()
