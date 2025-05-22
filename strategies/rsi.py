# File: strategies/rsi.py

from .base import BaseStrategy
from config import RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD
import statistics

class RsiStrategy(BaseStrategy):
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        # Override config with global defaults if not provided
        self.period      = config.get("rsi_period", RSI_PERIOD)
        self.overbought  = config.get("overbought", RSI_OVERBOUGHT)
        self.oversold    = config.get("oversold", RSI_OVERSOLD)
        self.symbol      = config["symbol"]
        self.usdt_amount = config["usdt_amount"]
        # Track last RSI to detect crosses
        self._last_rsi = None

    def compute_rsi(self, closes):
        window = closes[-(self.period + 1):]
        deltas = [window[i] - window[i - 1] for i in range(1, len(window))]
        gains  = [d for d in deltas if d > 0]
        losses = [abs(d) for d in deltas if d < 0]
        avg_gain = sum(gains) / self.period if gains else 0
        avg_loss = sum(losses) / self.period if losses else 0
        if avg_loss == 0:
            return 100
        rs  = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def on_bar(self, ohlcv):
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.period + 1:
            return None

        rsi = self.compute_rsi(closes)
        signal = None

        # Detect crossing **upward** through oversold → BUY
        if self._last_rsi is not None:
            if self._last_rsi >= self.oversold and rsi < self.oversold:
                # oversold breach (but want the bounce back above oversold)
                pass
            if self._last_rsi < self.oversold and rsi >= self.oversold:
                price = closes[-1]
                amount = float(self.exchange.amount_to_precision(
                    self.symbol, self.usdt_amount / price
                ))
                signal = {"side": "buy", "amount": amount}

        # Detect crossing **downward** through overbought → SELL
        if self._last_rsi is not None and signal is None:
            if self._last_rsi <= self.overbought and rsi > self.overbought:
                # overbought breach (but want the bounce back below overbought)
                pass
            if self._last_rsi > self.overbought and rsi <= self.overbought:
                asset = self.symbol.split("/")[0]
                balance = self.exchange.fetch_balance()["free"].get(asset, 0)
                if balance > 0:
                    amt = float(self.exchange.amount_to_precision(self.symbol, balance))
                    signal = {"side": "sell", "amount": amt}

        self._last_rsi = rsi
        return signal
