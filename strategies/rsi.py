# File: strategies/rsi.py

from .base import BaseStrategy
from config import RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD
import statistics

class RsiStrategy(BaseStrategy):
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        # Strategy parameters
        self.period         = config.get("rsi_period", RSI_PERIOD)
        self.overbought     = config.get("overbought", RSI_OVERBOUGHT)
        self.oversold       = config.get("oversold", RSI_OVERSOLD)
        self.symbol         = config["symbol"]
        self.usdt_amount    = config["usdt_amount"]
        # Track last RSI and position state
        self._last_rsi      = None
        self.in_position    = False
        self.position_amount = 0.0  # stored buy size

    def compute_rsi(self, closes):
        window = closes[-(self.period + 1):]
        deltas = [window[i] - window[i - 1] for i in range(1, len(window))]
        gains  = [d for d in deltas if d > 0]
        losses = [abs(d) for d in deltas if d < 0]
        avg_gain = sum(gains) / self.period if gains else 0
        avg_loss = sum(losses) / self.period if losses else 0
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def on_bar(self, ohlcv):
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.period + 1:
            return None

        rsi = self.compute_rsi(closes)
        signal = None

        # ── BUY when flat and RSI crosses up through oversold ──
        if not self.in_position and self._last_rsi is not None:
            if self._last_rsi < self.oversold and rsi >= self.oversold:
                price  = closes[-1]
                amount = float(self.exchange.amount_to_precision(
                    self.symbol, self.usdt_amount / price
                ))
                signal = {"side": "buy", "amount": amount}
                self.in_position = True
                self.position_amount = amount

        # ── SELL when long and RSI crosses down through overbought ──
        if self.in_position and self._last_rsi is not None and signal is None:
            if self._last_rsi > self.overbought and rsi <= self.overbought:
                # use stored buy size instead of querying balance
                amount = self.position_amount
                signal = {"side": "sell", "amount": amount}
                self.in_position = False
                self.position_amount = 0.0

        self._last_rsi = rsi
        return signal
