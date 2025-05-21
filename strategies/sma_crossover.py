from .base import BaseStrategy
import statistics
from config import ORDER_FRACTION, STOP_LOSS_PCT

class SmaCrossover(BaseStrategy):
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.fast  = config["fast"]
        self.slow  = config["slow"]
        # Track open position details for stop-loss
        self.entry_price     = None
        self.stop_loss_price = None

    def on_bar(self, ohlcv):
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.slow + 1:
            return None

        price = closes[-1]

        # ── 1) Stop-loss check ─────────────────────────────────────────────────
        if self.stop_loss_price is not None and price <= self.stop_loss_price:
            asset = self.config["symbol"].split("/")[0]
            bal   = self.exchange.fetch_balance()["free"].get(asset, 0)
            if bal > 0:
                amt = float(self.exchange.amount_to_precision(self.config["symbol"], bal))
                # Clear stop state
                self.entry_price     = None
                self.stop_loss_price = None
                return {"side": "sell", "amount": amt}

        # ── 2) Compute SMAs ─────────────────────────────────────────────────────
        sma_fast_prev = statistics.mean(closes[-(self.fast+1):-1])
        sma_slow_prev = statistics.mean(closes[-(self.slow+1):-1])
        sma_fast_now  = statistics.mean(closes[-self.fast:])
        sma_slow_now  = statistics.mean(closes[-self.slow:])

        # ── 3) Buy signal (only if flat) ───────────────────────────────────────
        if (self.entry_price is None
            and sma_fast_prev <= sma_slow_prev
            and sma_fast_now > sma_slow_now):

            # size as fraction of USDT balance
            usdt_balance = self.exchange.fetch_balance()["free"].get("USDT", 0)
            usdt_to_spend = usdt_balance * ORDER_FRACTION
            amt = float(self.exchange.amount_to_precision(
                self.config["symbol"],
                usdt_to_spend / price
            ))
            # set entry & stop-loss
            self.entry_price     = price
            self.stop_loss_price = price * (1 - STOP_LOSS_PCT)
            return {"side": "buy", "amount": amt}

        # ── 4) Sell signal ──────────────────────────────────────────────────────
        if (self.entry_price is not None
            and sma_fast_prev >= sma_slow_prev
            and sma_fast_now < sma_slow_now):

            asset = self.config["symbol"].split("/")[0]
            bal   = self.exchange.fetch_balance()["free"].get(asset, 0)
            if bal > 0:
                amt = float(self.exchange.amount_to_precision(self.config["symbol"], bal))
                # clear state
                self.entry_price     = None
                self.stop_loss_price = None
                return {"side": "sell", "amount": amt}

        # ── 5) Otherwise no action ─────────────────────────────────────────────
        return None
