# fetch_price.py

from dotenv import load_dotenv
import os, ccxt

# 1) Load API keys
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
secret  = os.getenv("BINANCE_API_SECRET")
if not api_key or not secret:
    raise ValueError("Missing Binance API credentials in .env")

# 2) Build the CCXT Binance (Testnet) client
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

# 3) Fetch the ticker for SOL/USDT
ticker = exchange.fetch_ticker("SOL/USDT")

# 4) Print out bid, ask, and last price
print(f"Bid:  {ticker['bid']}")
print(f"Ask:  {ticker['ask']}")
print(f"Last: {ticker['last']}")
