# realtime.py

import aiohttp

class Realtime:
    """
    Async generator for Binance kline (candlestick) data.
    
    Usage:
        ws = Realtime(symbol="BTC/USDT", interval="5m")
        async for bar in ws.ohlcv_stream():
            # bar == [openTime_ms, open, high, low, close, volume]
    """

    def __init__(self, symbol: str, interval: str):
        # symbol e.g. "BTC/USDT"; interval e.g. "5m", "1h", etc.
        self.symbol = symbol.replace("/", "").lower()
        self.interval = interval
        self.url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"

    async def ohlcv_stream(self):
        """
        Connects to Binance WebSocket and yields each *closed* kline as:
        [openTime_ms, open, high, low, close, volume]
        """
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.url) as ws:
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    data = msg.json()
                    k = data.get("k", {})
                    # `x` means the kline is closed
                    if k.get("x"):
                        yield [
                            k["t"],          # open time (ms since epoch)
                            float(k["o"]),   # open
                            float(k["h"]),   # high
                            float(k["l"]),   # low
                            float(k["c"]),   # close
                            float(k["v"]),   # volume
                        ]
