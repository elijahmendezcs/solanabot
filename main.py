# File: main.py

import asyncio
import os
import csv
from datetime import datetime

from exchange import init_exchange
from logger import setup_logger
from notifications import send_telegram
from config import (
    SYMBOL, USDT_AMOUNT, TIMEFRAME, PAPER_TRADING,
    ATR_PERIOD, ATR_THRESHOLD
)
from utils.indicators import atr
from strategies.sma_crossover import SmaCrossover
from strategies.rsi import RsiStrategy
from realtime import Realtime

DATA_FILE = os.path.join("data", "trades.csv")

STRATEGY_CONFIGS = [
    {"class": SmaCrossover, "params": {"symbol": SYMBOL, "usdt_amount": USDT_AMOUNT, "fast": 10, "slow": 100}},
    {"class": RsiStrategy,   "params": {"symbol": SYMBOL, "usdt_amount": USDT_AMOUNT}},
]

def ensure_data_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp","strategy","side","price","amount","cost"])

def log_trade(strategy_name, side, order):
    ts = datetime.utcnow().isoformat()
    price  = float(order["price"])
    amount = float(order["amount"])
    cost   = price * amount
    with open(DATA_FILE, "a", newline="") as f:
        csv.writer(f).writerow([ts, strategy_name, side, price, amount, cost])
    send_telegram(f"{strategy_name}: {side.upper()} {amount:.8f} @ {price:.2f}")

async def main():
    ensure_data_file()
    log      = setup_logger()
    exchange = init_exchange()
    ws       = Realtime(symbol=SYMBOL, interval=TIMEFRAME)

    strategies = [cfg["class"](exchange, cfg["params"]) for cfg in STRATEGY_CONFIGS]
    max_period = max(getattr(s, "slow", getattr(s, "period", 0)) for s in strategies)
    ohlcv_limit = max_period + 1

    log.info("▶️ Starting WebSocket-driven engine on Binance US…")
    bars = []

    async for candle in ws.ohlcv_stream():
        # once per closed 1m bar
        bars.append(candle)
        if len(bars) > ohlcv_limit:
            bars = bars[-ohlcv_limit:]

        last_price = bars[-1][4]
        log.info(f"Heartbeat — last price: {last_price:.2f}")

        # ATR‐based regime detection
        current_atr = atr(bars, ATR_PERIOD)
        volatility  = current_atr / last_price
        is_trending  = volatility > ATR_THRESHOLD
        log.info(f"Volatility: {volatility:.3%} → {'Trending' if is_trending else 'Ranging'}")

        # Strategy execution
        for strat in strategies:
            if isinstance(strat, SmaCrossover) and not is_trending:
                continue
            if isinstance(strat, RsiStrategy) and is_trending:
                continue

            sig = strat.on_bar(bars)
            if not sig:
                continue

            side, amt = sig["side"], sig["amount"]
            if PAPER_TRADING:
                order = {"price": last_price, "amount": amt}
                log.info(f"[PAPER] {strat.__class__.__name__}: {side.upper()} {amt:.8f} @ {last_price:.2f}")
            else:
                market  = exchange.markets[SYMBOL]
                min_amt = market["limits"]["amount"]["min"]
                if amt < min_amt:
                    log.info(f"Skipped {side} {amt:.8f} — below min size {min_amt}")
                    continue
                order = exchange.create_market_order(strat.config["symbol"], side, amt)
                log.info(f"{strat.__class__.__name__}: {side.upper()} {amt:.8f} @ {order['price']:.2f}")

            log_trade(strat.__class__.__name__, side, order)

        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
