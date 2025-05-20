# exchange.py

from dotenv import load_dotenv
import os
import ccxt

def init_exchange():
    """
    Load API keys from .env and return a sandbox-mode CCXT Binance client.
    """
    load_dotenv()
    api_key    = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("Missing BINANCE_API_KEY or BINANCE_API_SECRET in .env")

    exchange = ccxt.binance({
        'apiKey':          api_key,
        'secret':          api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType':            'spot',
            'adjustForTimeDifference': True,
        },
        'urls': {
            'api': 'https://testnet.binance.vision/api',
            'www': 'https://testnet.binance.vision',
        },
    })
    exchange.set_sandbox_mode(True)
    return exchange

def fetch_ohlcv(symbol, timeframe="1m", limit=100):
    """
    Fetch OHLCV bars from Binance Testnet.
    Returns list of [timestamp, open, high, low, close, volume].
    """
    ex = init_exchange()
    return ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

def place_order(symbol, side, amount):
    """
    Place a market order on Binance Testnet.
    side: "buy" or "sell", amount: how many base‐asset units.
    Returns the CCXT order dict.
    """
    ex = init_exchange()
    side = side.lower()
    if side == "buy":
        return ex.create_market_buy_order(symbol, amount)
    elif side == "sell":
        return ex.create_market_sell_order(symbol, amount)
    else:
        raise ValueError(f"Unknown side '{side}'")
