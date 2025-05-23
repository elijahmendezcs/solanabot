# File: strategies/macd.py
from .base import BaseStrategy
from utils.indicators import macd_lines
from config import (
    MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD,
    ORDER_FRACTION, STOP_LOSS_PCT
)

class MacdStrategy(BaseStrategy):
    """
    Basic MACD crossover strategy:
    - Buy when MACD line crosses above signal line (histogram turns positive).
    - Sell when MACD line crosses below signal line (histogram turns negative).
    Includes a hard stop-loss.
    """
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.symbol = config["symbol"]
        self.fast   = config.get("macd_fast", MACD_FAST_PERIOD)
        self.slow   = config.get("macd_slow", MACD_SLOW_PERIOD)
        self.signal = config.get("macd_signal", MACD_SIGNAL_PERIOD)
        self.entry_price     = None
        self.stop_loss_price = None

    def on_bar(self, ohlcv):
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.slow + self.signal:
            return None

        price = closes[-1]

        # Emergency stop-loss
        if self.stop_loss_price and price <= self.stop_loss_price:
            asset = self.symbol.split("/")[0]
            bal   = self.exchange.fetch_balance()["free"].get(asset, 0)
            if bal > 0:
                amt = float(self.exchange.amount_to_precision(self.symbol, bal))
                self.entry_price = self.stop_loss_price = None
                return {"side": "sell", "amount": amt}

        macd_line, signal_line, hist = macd_lines(
            closes, self.fast, self.slow, self.signal
        )
        prev_hist = hist[-2]
        curr_hist = hist[-1]

        # Buy: histogram crosses ≤0 → >0
        if prev_hist is not None and curr_hist is not None:
            if curr_hist > 0 and prev_hist <= 0 and self.entry_price is None:
                quote = self.symbol.split("/")[1]
                quote_bal = self.exchange.fetch_balance()["free"].get(quote, 0)
                usdt_to_spend = quote_bal * ORDER_FRACTION
                amt = float(self.exchange.amount_to_precision(
                    self.symbol, usdt_to_spend / price
                ))
                self.entry_price     = price
                self.stop_loss_price = price * (1 - STOP_LOSS_PCT)
                return {"side": "buy", "amount": amt}

        # Sell: histogram crosses ≥0 → <0
        if prev_hist is not None and curr_hist is not None:
            if curr_hist < 0 and prev_hist >= 0 and self.entry_price is not None:
                asset = self.symbol.split("/")[0]
                bal   = self.exchange.fetch_balance()["free"].get(asset, 0)
                if bal > 0:
                    amt = float(self.exchange.amount_to_precision(self.symbol, bal))
                    self.entry_price = self.stop_loss_price = None
                    return {"side": "sell", "amount": amt}

        return None