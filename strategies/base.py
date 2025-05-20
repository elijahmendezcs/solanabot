from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, exchange, config):
        """
        exchange: your exchange client
        config:  dict of strategy‐specific params
        """
        self.exchange = exchange
        self.config   = config

    @abstractmethod
    def on_bar(self, ohlcv):
        """
        Called once per new bar.
        ohlcv: list of [ts,o,h,l,c,v] bars
        Return: a dict like {"side":"buy","amount":0.1} or None
        """
        pass
