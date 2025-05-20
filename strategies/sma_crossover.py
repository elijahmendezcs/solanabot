from .base import BaseStrategy
import statistics

class SmaCrossover(BaseStrategy):
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.fast = config["fast"]
        self.slow = config["slow"]

    def on_bar(self, ohlcv):
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.slow + 1:
            return None
        sma_fast_prev = statistics.mean(closes[-(self.fast+1):-1])
        sma_slow_prev = statistics.mean(closes[-(self.slow+1):-1])
        sma_fast_now  = statistics.mean(closes[-self.fast:])
        sma_slow_now  = statistics.mean(closes[-self.slow:])
        if sma_fast_prev <= sma_slow_prev and sma_fast_now > sma_slow_now:
            # buy
            price = closes[-1]
            amt   = float(self.exchange.amount_to_precision(self.config["symbol"],
                                                            self.config["usdt_amount"]/price))
            return {"side":"buy","amount":amt}
        if sma_fast_prev >= sma_slow_prev and sma_fast_now < sma_slow_now:
            # sell
            asset = self.config["symbol"].split("/")[0]
            bal   = self.exchange.fetch_balance()["free"].get(asset, 0)
            if bal > 0:
                amt = float(self.exchange.amount_to_precision(self.config["symbol"], bal))
                return {"side":"sell","amount":amt}
        return None
