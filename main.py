# File: main.py

import asyncio
import os
import csv
from datetime import datetime

from exchange import init_exchange
from logger import setup_logger
from notifications import send_telegram
from config import (
    SYMBOLS, USDT_AMOUNT, TIMEFRAME, PAPER_TRADING,
    FAST_SMA, SLOW_SMA,
    ATR_PERIOD, ATR_THRESHOLD
)
from utils.indicators import atr
from strategies.sma_crossover import SmaCrossover
from strategies.rsi import RsiStrategy
from realtime import Realtime

DATA_FILE = os.path.join("data", "trades.csv")

STRATEGY_CLASSES = [SmaCrossover, RsiStrategy]

def ensure_data_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="") as f:
            csv.writer(f).writerow([
                "timestamp","symbol","strategy","side","price","amount","cost"
            ])

def log_trade(symbol, strategy_name, side, order, reason=None):
    ts = datetime.utcnow().isoformat()
    price  = float(order["price"])
    amount = float(order["amount"])
    cost   = price * amount
    with open(DATA_FILE, "a", newline="") as f:
        csv.writer(f).writerow([ts, symbol, strategy_name, side, price, amount, cost])
    msg = f"{symbol} | {strategy_name}: {side.upper()} {amount:.8f} @ {price:.2f}"
    if reason:
        msg += f" ({reason})"
    send_telegram(msg)

async def run_symbol(symbol):
    log = setup_logger()
    exchange = init_exchange()

    # Instantiate strategies for this symbol
    strategy_objs = []
    for cls in STRATEGY_CLASSES:
        params = {"symbol": symbol, "usdt_amount": USDT_AMOUNT}
        if cls is SmaCrossover:
            params.update({"fast": FAST_SMA, "slow": SLOW_SMA})
        strat = cls(exchange, params)
        strategy_objs.append(strat)

    # Streams: slow for signals, fast for emergencies
    ws_slow = Realtime(symbol=symbol, interval=TIMEFRAME, debug=False)
    ws_fast = Realtime(symbol=symbol, interval="1m", debug=False)

    # Emergency monitor (1m feed)
    async def monitor_emergency():
        async for bar in ws_fast.ohlcv_stream():
            price = bar[4]
            for strat in strategy_objs:
                sig = None
                if isinstance(strat, SmaCrossover) and strat.stop_loss_price is not None:
                    if price <= strat.stop_loss_price:
                        asset = symbol.split("/")[0]
                        bal = exchange.fetch_balance()["free"].get(asset, 0)
                        if bal > 0:
                            amt = float(exchange.amount_to_precision(symbol, bal))
                            sig = {"side": "sell", "amount": amt, "reason": "stop-loss-emergency"}
                if sig:
                    if PAPER_TRADING:
                        order = {"price": price, "amount": sig["amount"]}
                        log.info(f"[EMERGENCY][PAPER][{symbol}] SELL {sig['amount']:.8f} @ {price:.2f}")
                    else:
                        order = exchange.create_market_order(symbol, sig["side"], sig["amount"])
                        log.info(f"[EMERGENCY][{symbol}] SELL {sig['amount']:.8f} @ {order['price']:.2f}")
                    log_trade(symbol, strat.__class__.__name__, sig["side"], order, sig["reason"])

    asyncio.create_task(monitor_emergency())

    # Main loop (5m feed)
    max_period = max(getattr(s, "slow", getattr(s, "period", 0)) for s in strategy_objs)
    ohlcv_limit = max_period + 1
    bars = []

    log.info(f"▶️ Starting engine for {symbol}")
    async for candle in ws_slow.ohlcv_stream():
        bars.append(candle)
        if len(bars) > ohlcv_limit:
            bars = bars[-ohlcv_limit:]

        last_price = bars[-1][4]
        log.info(f"[{symbol}] Heartbeat — last price: {last_price:.2f}")

        current_atr = atr(bars, ATR_PERIOD)
        volatility  = current_atr / last_price
        is_trending = volatility > ATR_THRESHOLD
        log.info(f"[{symbol}] Volatility: {volatility:.3%} → "
                 f"{'Trending' if is_trending else 'Ranging'}")

        for strat in strategy_objs:
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
                log.info(f"[PAPER][{symbol}] {strat.__class__.__name__}: "
                         f"{side.upper()} {amt:.8f} @ {last_price:.2f}")
            else:
                market = exchange.markets[symbol]
                min_amt = market["limits"]["amount"]["min"]
                if amt < min_amt:
                    log.info(f"Skipped {symbol} {side} {amt:.8f} — below min size {min_amt}")
                    continue
                order = exchange.create_market_order(symbol, side, amt)
                log.info(f"[{symbol}] {strat.__class__.__name__}: "
                         f"{side.upper()} {amt:.8f} @ {order['price']:.2f}")

            log_trade(symbol, strat.__class__.__name__, side, order, reason)

        await asyncio.sleep(0)

async def main():
    ensure_data_file()
    tasks = [asyncio.create_task(run_symbol(sym)) for sym in SYMBOLS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
