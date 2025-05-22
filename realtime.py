# File: realtime.py

import asyncio
import json
import aiohttp

class Realtime:
    """
    Async OHLCV stream using Binance US public WebSocket.
    Yields one closed candle [timestamp, open, high, low, close, volume].
    Also prints every incoming tick and logs when connected.
    """
    def __init__(self, symbol: str = "SOL/USDT", interval: str = "1m"):
        self.stream_symbol = symbol.replace("/", "").lower()
        self.interval = interval

    async def ohlcv_stream(self):
        url = f"wss://stream.binance.us:9443/ws/{self.stream_symbol}@kline_{self.interval}"
        session = aiohttp.ClientSession()
        try:
            ws = await session.ws_connect(url)
            print("WS connected—streaming kline ticks…")
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    k = data.get("k", {})
                    # Print every tick's latest price
                    current_price = float(k.get("c", 0.0))
                    print(f"Tick → {current_price:.2f}")
                    # Only yield when candle is closed
                    if k.get("x"):
                        yield [
                            k["t"],                  # open time (ms)
                            float(k["o"]),           # open
                            float(k["h"]),           # high
                            float(k["l"]),           # low
                            float(k["c"]),           # close
                            float(k["v"]),           # volume
                        ]
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        finally:
            await session.close()
