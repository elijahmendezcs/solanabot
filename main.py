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

def log_trade(strategy_name, side, order, reason=None):
    ts = datetime.utcnow().isoformat()
    price = float(order["price"])
    amount = float(order["amount"])
    cost = price * amount
    with open(DATA_FILE, "a", newline="") as f:
        csv.writer(f).writerow([ts, strategy_name, side, price, amount, cost])
    msg = f"{strategy_name}: {side.upper()} {amount:.8f} @ {price:.2f}"
    if reason:
        msg += f" ({reason})"
    send_telegram(msg)

async def main():
    ensure_data_file()
    log = setup_logger()
    exchange = init_exchange()

    # Initialize strategies
    strategies = [cfg["class"](exchange, cfg["params"]) for cfg in STRATEGY_CONFIGS]

    # Slow feed: 5m bars for main strategy execution
    ws_slow = Realtime(symbol=SYMBOL, interval=TIMEFRAME)

    # Fast feed: 1m bars for emergency monitoring
    ws_fast = Realtime(symbol=SYMBOL, interval="1m")

    # Emergency monitor task
    async def monitor_emergency():
        async for bar in ws_fast.ohlcv_stream():
            price = bar[4]
            for strat in strategies:
                sig = None
                # Emergency stop-loss for SMA strategy
                if isinstance(strat, SmaCrossover) and strat.stop_loss_price is not None and price <= strat.stop_loss_price:
                    asset = strat.config["symbol"].split("/")[0]
                    bal = exchange.fetch_balance()["free"].get(asset, 0)
                    if bal > 0:
                        amt = float(exchange.amount_to_precision(strat.config["symbol"], bal))
                        sig = {"side": "sell", "amount": amt, "reason": "stop-loss-emergency"}
                # Additional fast-timeframe checks (e.g., RSI) can be added here

                if sig:
                    if PAPER_TRADING:
                        order = {"price": price, "amount": sig["amount"]}
                        log.info(f"[EMERGENCY][PAPER] {strat.__class__.__name__}: SELL {sig['amount']:.8f} @ {price:.2f}")
                    else:
                        order = exchange.create_market_order(strat.config["symbol"], sig["side"], sig["amount"])
                        log.info(f"[EMERGENCY] {strat.__class__.__name__}: SELL {sig['amount']:.8f} @ {order['price']:.2f}")
                    log_trade(strat.__class__.__name__, sig["side"], order, reason=sig["reason"])

    # Launch emergency monitor
    asyncio.create_task(monitor_emergency())

    # Main loop for slow feed
    max_period = max(getattr(s, "slow", getattr(s, "period", 0)) for s in strategies)
    ohlcv_limit = max_period + 1
    bars = []

    log.info("▶️ Starting dual-feed engine: 5m main feed & 1m emergency monitor")
    async for candle in ws_slow.ohlcv_stream():
        bars.append(candle)
        if len(bars) > ohlcv_limit:
            bars = bars[-ohlcv_limit:]

        last_price = bars[-1][4]
        log.info(f"Heartbeat — last price: {last_price:.2f}")

        # ATR-based regime detection
        current_atr = atr(bars, ATR_PERIOD)
        volatility  = current_atr / last_price
        is_trending  = volatility > ATR_THRESHOLD
        log.info(f"Volatility: {volatility:.3%} → {'Trending' if is_trending else 'Ranging'}")

        for strat in strategies:
            # Regime gating
            if isinstance(strat, SmaCrossover) and not is_trending:
                continue
            if isinstance(strat, RsiStrategy) and is_trending:
                continue

            sig = strat.on_bar(bars)
            if not sig:
                continue

            side, amt = sig["side"], sig["amount"]
            reason    = sig.get("reason")
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

            log_trade(strat.__class__.__name__, side, order, reason=reason)

        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
