# File: strategies/rsi.py
from .base import BaseStrategy
import statistics

class RsiStrategy(BaseStrategy):
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.period      = config["rsi_period"]
        self.overbought  = config["overbought"]
        self.oversold    = config["oversold"]
        self.symbol      = config["symbol"]
        self.usdt_amount = config["usdt_amount"]

    def compute_rsi(self, closes):
        # Grab the last period+1 closes to compute deltas
        window = closes[-(self.period + 1):]
        deltas = [window[i] - window[i - 1] for i in range(1, len(window))]
        gains  = [d for d in deltas if d > 0]
        losses = [abs(d) for d in deltas if d < 0]
        avg_gain = sum(gains) / self.period if gains else 0
        avg_loss = sum(losses) / self.period if losses else 0
        if avg_loss == 0:
            return 100
        rs  = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def on_bar(self, ohlcv):
        closes = [bar[4] for bar in ohlcv]
        if len(closes) < self.period + 1:
            return None
        rsi = self.compute_rsi(closes)
        # Buy signal when RSI crosses below oversold
        if rsi < self.oversold:
            price = closes[-1]
            amount = float(self.exchange.amount_to_precision(
                self.symbol, self.usdt_amount / price
            ))
            return {"side": "buy", "amount": amount}
        # Sell signal when RSI crosses above overbought
        if rsi > self.overbought:
            asset = self.symbol.split("/")[0]
            balance = self.exchange.fetch_balance()["free"].get(asset, 0)
            if balance > 0:
                amount = float(self.exchange.amount_to_precision(self.symbol, balance))
                return {"side": "sell", "amount": amount}
        return None