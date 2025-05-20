# sma_signal.py

from dotenv import load_dotenv
import os
import ccxt
import statistics

def init_exchange():
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY")
    secret  = os.getenv("BINANCE_API_SECRET")
    if not api_key or not secret:
        raise ValueError("Missing Binance API credentials in .env")
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
            'adjustForTimeDifference': True,
        },
        'urls': {
            'api': 'https://testnet.binance.vision/api',
            'www': 'https://testnet.binance.vision',
        },
    })
    exchange.set_sandbox_mode(True)
    return exchange

def fetch_ohlcv(symbol="SOL/USDT", timeframe="1m", limit=100):
    """
    Return a list of [ timestamp, open, high, low, close, volume ] bars.
    """
    exchange = init_exchange()
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

def compute_sma(data, period):
    """
    Compute the simple moving average of the last `period` values in data.
    """
    if len(data) < period:
        raise ValueError(f"Not enough data to compute SMA for period {period}")
    return statistics.mean(data[-period:])

def generate_signal(closes, fast=10, slow=30):
    """
    Simple SMA crossover:
      - BUY  when SMA_fast crosses above SMA_slow
      - SELL when SMA_fast crosses below SMA_slow
      - otherwise return None
    """
    if len(closes) < slow + 1:
        return None

    sma_fast_prev = compute_sma(closes[:-1], fast)
    sma_slow_prev = compute_sma(closes[:-1], slow)
    sma_fast_now  = compute_sma(closes,      fast)
    sma_slow_now  = compute_sma(closes,      slow)

    # cross above → buy
    if sma_fast_prev <= sma_slow_prev and sma_fast_now > sma_slow_now:
        return "buy"
    # cross below → sell
    if sma_fast_prev >= sma_slow_prev and sma_fast_now < sma_slow_now:
        return "sell"
    return None
