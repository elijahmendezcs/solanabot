# File: config.py

# ─── Trading Pair & Order Size ────────────────────────────────────────────────
SYMBOL        = "SOL/USD"     # ← switch to Kraken’s live USD market
USDT_AMOUNT   = 10.0          # USD value per trade (used in backtests)

# Percent of USDT balance to risk per trade
ORDER_FRACTION = 0.02         # 2% per trade

# Stop-loss percent from entry price
STOP_LOSS_PCT  = 0.01         # 1% hard stop

# Simulate trading fees and slippage
FEE_PCT       = 0.001         # 0.1% fee per trade
SLIPPAGE_PCT  = 0.0005        # 0.05% slippage per trade

# Paper-trading mode (True = simulate orders, False = place real orders)
PAPER_TRADING = True

# ─── SMA Crossover Settings ──────────────────────────────────────────────────
FAST_SMA = 10                 # “Fast” moving average period
SLOW_SMA = 100                # “Slow” moving average period

# ─── RSI Strategy Settings ───────────────────────────────────────────────────
RSI_PERIOD     = 14           # Period for RSI calculation
RSI_OVERBOUGHT = 70           # RSI threshold to consider overbought
RSI_OVERSOLD   = 30           # RSI threshold to consider oversold

# ─── Loop & Data Settings ───────────────────────────────────────────────────
TIMEFRAME     = "1m"          # Candle timeframe for OHLCV
OHLCV_LIMIT   = SLOW_SMA + 1  # How many bars to fetch each cycle
LOOP_INTERVAL = 5             # Seconds to wait between cycles
