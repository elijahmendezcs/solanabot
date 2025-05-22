# File: main.py

import os
import csv
import time
from datetime import datetime

from exchange import init_exchange, fetch_ohlcv, place_order
from logger import setup_logger
from notifications import send_telegram
from config import LOOP_INTERVAL, PAPER_TRADING, TIMEFRAME
from strategies.sma_crossover import SmaCrossover
from strategies.rsi import RsiStrategy

# Path to the CSV file for logging trades
_data_file = os.path.join("data", "trades.csv")

# Strategy configurations: SMA crossover and RSI
STRATEGY_CONFIGS = [
    {
        "class": SmaCrossover,
        "params": {"symbol": "SOL/USDT", "usdt_amount": 10.0, "fast": 10, "slow": 100},
    },
    {
        "class": RsiStrategy,
        "params": {"symbol": "SOL/USDT", "usdt_amount": 10.0},
    },
]

def ensure_data_file():
    os.makedirs(os.path.dirname(_data_file), exist_ok=True)
    if not os.path.exists(_data_file):
        with open(_data_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "strategy", "side", "price", "amount", "cost"])


def log_trade(strategy_name: str, side: str, order: dict):
    timestamp = datetime.utcnow().isoformat()
    price     = float(order["price"])
    amount    = float(order["amount"])
    cost      = price * amount

    with open(_data_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, strategy_name, side, price, amount, cost])

    send_telegram(f"{strategy_name}: {side.upper()} {amount} @ {price:.2f}")


def main():
    ensure_data_file()

    log      = setup_logger()
    exchange = init_exchange()

    strategies = [cfg["class"](exchange, cfg["params"]) for cfg in STRATEGY_CONFIGS]
    max_period = max(
        getattr(s, "slow", getattr(s, "period", 0)) for s in strategies
    )
    ohlcv_limit = max_period + 1

    log.info("▶️ Starting multi-strategy engine…")
    while True:
        try:
            bars = fetch_ohlcv("SOL/USDT", timeframe=TIMEFRAME, limit=ohlcv_limit)
            last_price = bars[-1][4]
            log.info(f"Heartbeat — last price: {last_price}")

            for strat in strategies:
                sig = strat.on_bar(bars)
                if not sig:
                    continue

                side, amt = sig["side"], sig["amount"]
                if PAPER_TRADING:
                    order = {"price": last_price, "amount": amt}
                    log.info(f"[PAPER] {strat.__class__.__name__}: {side.upper()} {amt} @ {last_price}")
                else:
                    order = place_order(strat.config["symbol"], side, amt)
                    log.info(f"{strat.__class__.__name__}: {side.upper()} {amt} @ {order['price']}")

                log_trade(strat.__class__.__name__, side, order)

        except Exception as e:
            log.error("Engine error", exc_info=e)
            send_telegram(f"Engine error: {e}")

        time.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    main()
