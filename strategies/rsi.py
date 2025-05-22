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
    Mean-reversion RSI strategy with profit-target, trailing stop, and time-cap exits.
    """
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        # Strategy parameters
        self.period      = config.get("rsi_period", RSI_PERIOD)
        self.oversold    = config.get("oversold",   RSI_OVERSOLD)
        self.overbought  = config.get("overbought", RSI_OVERBOUGHT)
        self.symbol      = config["symbol"]
        self.usdt_amount = config["usdt_amount"]

        # State variables
        self._last_rsi       = None     # Track previous RSI for cross detection
        self.in_position     = False    # Are we currently long?
        self.position_amount = 0.0      # Amount of asset bought
        self.entry_price     = None     # Price at which we entered
        self.entry_time      = None     # Timestamp of entry
        self.highest_price   = None     # Highest price since entry (for trailing stop)

    def compute_rsi(self, closes):
        """
        Calculate RSI given a list of closing prices.
        Standard Wilder's RSI calculation.
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
        Called on each new bar. Returns a signal dict or None.
        Logic order:
          1) If in position, check exits: take-profit, trailing stop, time-cap, RSI cross.
          2) If flat, check for RSI oversold cross-up to enter.
        """
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.period + 1:
            # Not enough data yet
            return None

        price = closes[-1]
        now = datetime.utcnow()
        signal = None
        current_rsi = self.compute_rsi(closes)

        # --- 1) Exit checks (if currently in position) ---
        if self.in_position:
            # 1A) Profit-target exit
            # Thought: lock in a quick gain when price reaches entry * (1 + TP_PCT)
            if price >= self.entry_price * (1 + TP_PCT):
                signal = {"side": "sell", "amount": self.position_amount}
                reason = "take-profit"

            # 1B) Trailing stop exit
            # Thought: if price dips TRAIL_PCT below highest high after entry, exit
            if signal is None:
                # initialize highest_price on first check
                if self.highest_price is None:
                    self.highest_price = price
                else:
                    self.highest_price = max(self.highest_price, price)
                if price <= self.highest_price * (1 - TRAIL_PCT):
                    signal = {"side": "sell", "amount": self.position_amount}
                    reason = "trailing-stop"

            # 1C) Time-cap exit
            # Thought: avoid stale trades by forcing exit after MAX_HOLD_MINS
            if signal is None and (now - self.entry_time) > timedelta(minutes=MAX_HOLD_MINS):
                signal = {"side": "sell", "amount": self.position_amount}
                reason = "time-cap"

            # 1D) Fallback: RSI overbought cross exit
            # Thought: use original logic as final safety
            if signal is None and self._last_rsi is not None:
                if self._last_rsi > self.overbought and current_rsi <= self.overbought:
                    signal = {"side": "sell", "amount": self.position_amount}
                    reason = "rsi-cross-down"

            # If an exit signal was triggered, reset state
            if signal:
                # Debug: annotate reason in log
                print(f"Exiting {reason} at {price:.2f}")
                self.in_position     = False
                self._last_rsi       = current_rsi
                # Clear entry tracking
                self.position_amount = 0.0
                self.entry_price     = None
                self.entry_time      = None
                self.highest_price   = None
                return signal

        # --- 2) Entry check (if flat) ---
        # Only check for entry if not already in position
        if not self.in_position and self._last_rsi is not None:
            # Thought: enter when RSI crosses up through the oversold level
            if self._last_rsi < self.oversold and current_rsi >= self.oversold:
                amount = float(self.exchange.amount_to_precision(
                    self.symbol, self.usdt_amount / price
                ))
                signal = {"side": "buy", "amount": amount}
                # Record entry details for exits
                self.in_position     = True
                self.position_amount = amount
                self.entry_price     = price
                self.entry_time      = now
                self.highest_price   = price
                # Debug: log entry
                print(f"Entering BUY at {price:.2f}, amount={amount:.8f}")

        # Update last RSI for next bar
        self._last_rsi = current_rsi
        return signal