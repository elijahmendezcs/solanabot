# fetch_binance_balance.py

from dotenv import load_dotenv
import os
import ccxt

def main():
    # 1) Load env vars
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY")
    secret  = os.getenv("BINANCE_API_SECRET")
    if not api_key or not secret:
        raise ValueError("Missing BINANCE_API_KEY or BINANCE_API_SECRET in .env")

    # 2) Instantiate CCXT Binance in TESTNET spot mode with time sync
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

    # 3) Fetch balances
    balance = exchange.fetch_balance()
    free_map  = balance.get('free',  {})
    used_map  = balance.get('used',  {})
    total_map = balance.get('total', {})

    print("🎯 Your Binance Testnet Balances:")
    for symbol, total in total_map.items():
        # Only print assets with a nonzero total
        if total and total > 0:
            free  = free_map.get(symbol, 0)
            used  = used_map.get(symbol, 0)
            print(f"  • {symbol:6s}  free={free:>10}  used={used:>10}  total={total:>10}")

if __name__ == "__main__":
    main()
