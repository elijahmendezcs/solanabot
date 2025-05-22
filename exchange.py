# File: exchange.py

from dotenv import load_dotenv
import os
import ccxt


def init_exchange():
    """
    Load API keys from .env and return a CCXT client for the selected exchange.
    Supports 'kraken' and 'binance' (live or testnet via SANDBOX env var).
    """
    load_dotenv()
    ex_name = os.getenv("EXCHANGE", "binance").lower()

    if ex_name == "kraken":
        api_key    = os.getenv("KRAKEN_API_KEY")
        api_secret = os.getenv("KRAKEN_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError("Missing KRAKEN_API_KEY or KRAKEN_API_SECRET in .env")
        exchange = ccxt.kraken({
            'apiKey':          api_key,
            'secret':          api_secret,
            'enableRateLimit': True,
        })

    elif ex_name == "binance":
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
        })
        # Optional: use testnet if SANDBOX env var is set
        if os.getenv("SANDBOX", "").lower() in ("true", "1"):
            exchange.set_sandbox_mode(True)

    else:
        raise ValueError(f"Unsupported EXCHANGE: {ex_name}")

    exchange.load_markets()
    return exchange


def fetch_ohlcv(symbol, timeframe="1m", limit=100):
    """
    Fetch OHLCV bars from the selected exchange.
    Returns a list of [timestamp, open, high, low, close, volume].
    """
    ex = init_exchange()
    return ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


def place_order(symbol, side, amount):
    """
    Place a market order on the selected exchange.
    Only called when PAPER_TRADING=False in config.
    """
    ex = init_exchange()
    side = side.lower()
    if side == "buy":
        return ex.create_market_buy_order(symbol, amount)
    elif side == "sell":
        return ex.create_market_sell_order(symbol, amount)
    else:
        raise ValueError(f"Unknown side '{side}'")
