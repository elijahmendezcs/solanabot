# place_order.py

from dotenv import load_dotenv
import os, ccxt

def main():
    # 1) Load API creds
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY")
    secret  = os.getenv("BINANCE_API_SECRET")
    if not api_key or not secret:
        raise ValueError("Missing Binance API credentials in .env")

    # 2) Instantiate Testnet client
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

    # 3) Fetch the latest price
    ticker = exchange.fetch_ticker("SOL/USDT")
    last_price = ticker['last']
    print(f"Current SOL/USDT price: {last_price}")

    # 4) Compute size for $1 USDT
    usdt_amount = 10.0
    sol_amount = usdt_amount / last_price
    # Round down to acceptable precision (e.g. 6 decimals)
    sol_amount = exchange.amount_to_precision("SOL/USDT", sol_amount)
    print(f"Buying {sol_amount} SOL for {usdt_amount} USDT")

    # 5) Place market buy order
    order = exchange.create_market_buy_order("SOL/USDT", float(sol_amount))
    print("Order response:")
    print(order)

if __name__ == "__main__":
    main()
