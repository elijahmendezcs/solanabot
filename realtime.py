# File: realtime.py

import ccxt.pro as ccxtpro

class Realtime:
    """
    Async OHLCV stream using CCXT Pro's WebSocket watch_ohlcv on Binance US.
    """
    def __init__(self, exchange_name: str = "binanceus"):
        # Instantiate the CCXT Pro client for Binance US
        self.ex = getattr(ccxtpro, exchange_name)({
            'enableRateLimit': True,
        })

    async def ohlcv_stream(self, symbol: str, timeframe: str):
        """
        Async generator yielding the most recently closed candle.
        """
        await self.ex.load_markets()
        while True:
            candles = await self.ex.watch_ohlcv(symbol, timeframe)
            yield candles[-1]
