import asyncio
from datetime import datetime

from exchange import init_exchange
from logger import setup_logger
from notifications import send_telegram
from db import init_db, log_trade_db
from config import (
    SYMBOLS, USDT_AMOUNT, TIMEFRAME, PAPER_TRADING,
    FAST_SMA, SLOW_SMA,
    ATR_PERIOD, ATR_THRESHOLD,
    MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD
)
from utils.indicators import atr
from strategies.sma_crossover import SmaCrossover
from strategies.rsi import RsiStrategy
from strategies.macd import MacdStrategy
from strategies.bollinger import BollingerStrategy
from realtime import Realtime


def format_message(symbol, strategy_name, side, amount, price, reason=None):
    msg = f"{symbol} | {strategy_name}: {side.upper()} {amount} @ {price:.2f}"
    if reason:
        msg += f" ({reason})"
    return msg


async def run_symbol(symbol):
    log = setup_logger()
    exchange = init_exchange()

    # Instantiate strategies for this symbol
    strategy_objs = []
    for cls in [SmaCrossover, RsiStrategy, MacdStrategy, BollingerStrategy]:
        params = {"symbol": symbol, "usdt_amount": USDT_AMOUNT}
        if cls is SmaCrossover:
            params.update({"fast": FAST_SMA, "slow": SLOW_SMA})
        if cls is MacdStrategy:
            params.update({
                "macd_fast": MACD_FAST_PERIOD,
                "macd_slow": MACD_SLOW_PERIOD,
                "macd_signal": MACD_SIGNAL_PERIOD,
            })
        strat = cls(exchange, params)
        strategy_objs.append(strat)

    # Streams: slow for signals, fast for emergency monitor
    ws_slow = Realtime(symbol=symbol, interval=TIMEFRAME)
    ws_fast = Realtime(symbol=symbol, interval="1m")

    async def monitor_emergency():
        async for bar in ws_fast.ohlcv_stream():
            price = bar[4]
            for strat in strategy_objs:
                sig = None
                if hasattr(strat, 'stop_loss_price') and strat.stop_loss_price is not None:
                    if price <= strat.stop_loss_price:
                        asset = symbol.split("/")[0]
                        bal = exchange.fetch_balance()["free"].get(asset, 0)
                        if bal > 0:
                            amt = exchange.amount_to_precision(symbol, bal)
                            sig = {"side": "sell", "amount": amt, "reason": "stop-loss-emergency"}
                if sig:
                    cost = price * float(sig["amount"])
                    log_trade_db(symbol, strat.__class__.__name__, sig["side"], price, float(sig["amount"]), cost, sig.get("reason"))
                    msg = format_message(symbol, strat.__class__.__name__, sig["side"], sig["amount"], price, sig.get("reason"))
                    send_telegram(msg)
                    log.info(f"[EMERGENCY][{'PAPER' if PAPER_TRADING else ''}][{symbol}] {sig['side'].upper()} {sig['amount']} @ {price:.2f} ({sig.get('reason')})")

    asyncio.create_task(monitor_emergency())

    # Main loop (5m feed)
    max_period = max(getattr(s, 'slow', getattr(s, 'period', 0)) for s in strategy_objs)
    ohlcv_limit = max_period + 1
    bars = []

    log.info(f"▶️ Starting engine for {symbol}")
    async for candle in ws_slow.ohlcv_stream():
        bars.append(candle)
        if len(bars) > ohlcv_limit:
            bars = bars[-ohlcv_limit:]

        last_price = bars[-1][4]
        log.info(f"[{symbol}] Heartbeat — last price: {last_price:.2f}")

        # Regime detection
        current_atr = atr(bars, ATR_PERIOD)
        volatility = current_atr / last_price if last_price else 0
        is_trending = volatility > ATR_THRESHOLD
        log.info(f"[{symbol}] Volatility: {volatility:.3%} → {'Trending' if is_trending else 'Ranging'}")

        for strat in strategy_objs:
            # Regime-based gating
            if isinstance(strat, SmaCrossover) and not is_trending:
                continue
            if isinstance(strat, RsiStrategy) and is_trending:
                continue
            if isinstance(strat, BollingerStrategy) and is_trending:
                continue

            sig = strat.on_bar(bars)
            if not sig:
                continue

            side, raw_amt = sig['side'], sig['amount']
            reason = sig.get('reason')
            price = last_price

            # Log to DB and notify
            cost = price * float(raw_amt)
            log_trade_db(symbol, strat.__class__.__name__, side, price, float(raw_amt), cost, reason)
            msg = format_message(symbol, strat.__class__.__name__, side, raw_amt, price, reason)
            send_telegram(msg)

            if PAPER_TRADING:
                log.info(f"[PAPER][{symbol}] {strat.__class__.__name__}: {side.upper()} {raw_amt} @ {price:.2f} ({reason or ''})")
            else:
                # Enforce minimum size
                market = exchange.markets[symbol]
                min_amt = market['limits']['amount']['min']
                amt = float(raw_amt)
                if amt < min_amt:
                    log.info(f"Skipped {symbol} {side} {amt:.8f} — below min size {min_amt}")
                    continue
                # Format to exchange precision
                precise_amt = exchange.amount_to_precision(symbol, amt)
                try:
                    order = exchange.create_market_order(symbol, side, precise_amt)
                    log.info(f"[{symbol}] {strat.__class__.__name__}: {side.upper()} {precise_amt} @ {order['price']:.2f}")
                except Exception as e:
                    log.error(f"Order placement failed for {symbol} {side} {precise_amt}: {e}")

        await asyncio.sleep(0)


async def main():
    init_db()
    tasks = [asyncio.create_task(run_symbol(sym)) for sym in SYMBOLS]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
