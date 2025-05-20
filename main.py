import time
from exchange import init_exchange, fetch_ohlcv, place_order
from logger import setup_logger
import importlib, os

# load a list of strategies you want to run
from strategies.sma_crossover import SmaCrossover

CONFIG = {
    "symbol":      "SOL/USDT",
    "usdt_amount": 10.0,
    "fast":        10,
    "slow":        30,
}

def main():
    log      = setup_logger()
    exchange = init_exchange()
    strat    = SmaCrossover(exchange, CONFIG)

    log.info("▶️ Starting engine…")
    while True:
        try:
            bars   = fetch_ohlcv(CONFIG["symbol"], timeframe="1m", limit=CONFIG["slow"]+1)
            signal = strat.on_bar(bars)
            if signal:
                order = place_order(CONFIG["symbol"], signal["side"], signal["amount"])
                log.info(f"{signal['side'].upper()} {signal['amount']} @ {order['price']}")
        except Exception as e:
            log.error("Engine error", exc_info=e)
        time.sleep(60)

if __name__ == "__main__":
    main()
