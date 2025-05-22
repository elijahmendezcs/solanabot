# File: strategies/rsi.py

from .base import BaseStrategy
from config import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    TP_PCT, TRAIL_PCT, MAX_HOLD_MINS
)
from datetime import datetime, timedelta
import statistics

class RsiStrategy(BaseStrategy):
    """
    Mean-reversion RSI strategy with profit-target, trailing stop, time-cap exits,
    and exit-reason tagging for notifications.
    """
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.period      = config.get("rsi_period", RSI_PERIOD)
        self.oversold    = config.get("oversold",   RSI_OVERSOLD)
        self.overbought  = config.get("overbought", RSI_OVERBOUGHT)
        self.symbol      = config["symbol"]
        self.usdt_amount = config["usdt_amount"]

        # State
        self._last_rsi       = None
        self.in_position     = False
        self.position_amount = 0.0
        self.entry_price     = None
        self.entry_time      = None
        self.highest_price   = None

    def compute_rsi(self, closes):
        """
        Wilder's RSI calculation over the last `period` bars.
        """
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
        """
        Called on each new bar. Returns a signal dict:
          {"side": "buy"/"sell", "amount": float, "reason": optional str}
        or None.
        """
        closes = [bar[4] for bar in ohlcv]
        # Not enough data yet
        if len(closes) < self.period + 1:
            return None

        price     = closes[-1]
        now       = datetime.utcnow()
        current_rsi = self.compute_rsi(closes)
        signal    = None

        # --- 1) Exit logic (if in position) ---
        if self.in_position:
            # 1A) Take-profit
            if price >= self.entry_price * (1 + TP_PCT):
                signal = {"side": "sell", "amount": self.position_amount, "reason": "take-profit"}

            # 1B) Trailing stop
            if signal is None:
                self.highest_price = price if self.highest_price is None else max(self.highest_price, price)
                if price <= self.highest_price * (1 - TRAIL_PCT):
                    signal = {"side": "sell", "amount": self.position_amount, "reason": "trailing-stop"}

            # 1C) Time-cap
            if signal is None and (now - self.entry_time) > timedelta(minutes=MAX_HOLD_MINS):
                signal = {"side": "sell", "amount": self.position_amount, "reason": "time-cap"}

            # 1D) RSI cross-down fallback
            if signal is None and self._last_rsi is not None:
                if self._last_rsi > self.overbought and current_rsi <= self.overbought:
                    signal = {"side": "sell", "amount": self.position_amount, "reason": "rsi-cross-down"}

            if signal:
                print(f"Exiting {signal['reason'].upper()} at {price:.2f}")
                # Reset state
                self.in_position     = False
                self._last_rsi       = current_rsi
                self.position_amount = 0.0
                self.entry_price     = None
                self.entry_time      = None
                self.highest_price   = None
                return signal

        # --- 2) Entry logic (if flat) ---
        if not self.in_position and self._last_rsi is not None:
            if self._last_rsi < self.oversold and current_rsi >= self.oversold:
                amount = float(self.exchange.amount_to_precision(
                    self.symbol, self.usdt_amount / price
                ))
                signal = {"side": "buy", "amount": amount}
                # Record entry state
                self.in_position     = True
                self.position_amount = amount
                self.entry_price     = price
                self.entry_time      = now
                self.highest_price   = price
                print(f"Entering BUY at {price:.2f}, amount={amount:.8f}")
                # Update last RSI immediately so we don't re-trigger entry
                self._last_rsi = current_rsi
                return signal

        # Update last RSI for next bar
        self._last_rsi = current_rsi
        return None
