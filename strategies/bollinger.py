# File: strategies/bollinger.py
from .base import BaseStrategy
from utils.indicators import bollinger_bands
from config import ORDER_FRACTION, STOP_LOSS_PCT

class BollingerStrategy(BaseStrategy):
    """
    Bollinger Bands mean-reversion strategy:
    - Buy when price closes below the lower band.
    - Sell when price closes above the upper band.
    - Includes a hard stop-loss based on STOP_LOSS_PCT.
    """
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.symbol = config["symbol"]
        period = config.get("bb_period")
        self.period = period if period is not None else 20
        std = config.get("bb_std_dev")
        self.num_std_dev = std if std is not None else 2
        self.entry_price = None
        self.stop_loss_price = None

    def on_bar(self, ohlcv):
        """
        Called on each new bar. Returns a signal dict or None.
        """
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.period:
            return None

        price = closes[-1]
        lower, middle, upper = bollinger_bands(closes, self.period, self.num_std_dev)
        lb = lower[-1]
        ub = upper[-1]

        # 1) Hard stop-loss check
        if self.stop_loss_price and price <= self.stop_loss_price:
            asset = self.symbol.split("/")[0]
            bal = self.exchange.fetch_balance()["free"].get(asset, 0)
            if bal > 0:
                amt = float(self.exchange.amount_to_precision(self.symbol, bal))
                self.entry_price = None
                self.stop_loss_price = None
                return {"side": "sell", "amount": amt, "reason": "stop-loss"}

        # 2) Entry: price below lower band
        if lb is not None and price < lb and self.entry_price is None:
            quote = self.symbol.split("/")[1]
            quote_bal = self.exchange.fetch_balance()["free"].get(quote, 0)
            usdt_to_spend = quote_bal * ORDER_FRACTION
            amt = float(self.exchange.amount_to_precision(self.symbol, usdt_to_spend / price))
            self.entry_price = price
            self.stop_loss_price = price * (1 - STOP_LOSS_PCT)
            return {"side": "buy", "amount": amt, "reason": "bb_lower"}

        # 3) Exit: price above upper band
        if ub is not None and price > ub and self.entry_price is not None:
            asset = self.symbol.split("/")[0]
            bal = self.exchange.fetch_balance()["free"].get(asset, 0)
            if bal > 0:
                amt = float(self.exchange.amount_to_precision(self.symbol, bal))
                self.entry_price = None
                self.stop_loss_price = None
                return {"side": "sell", "amount": amt, "reason": "bb_upper"}

        return None
