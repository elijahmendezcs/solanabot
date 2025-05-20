# config.py

# ─── Trading Pair & Order Size ────────────────────────────────────────────────
SYMBOL       = "SOL/USDT"    # Which market to trade
USDT_AMOUNT  = 10.0          # USD value per trade

# ─── SMA Crossover Settings ──────────────────────────────────────────────────
FAST_SMA = 10                # “Fast” moving average period
SLOW_SMA = 30                # “Slow” moving average period

# ─── Loop & Data Settings ───────────────────────────────────────────────────
TIMEFRAME     = "1m"         # Candle timeframe for OHLCV
OHLCV_LIMIT   = SLOW_SMA + 1 # How many bars to fetch each cycle
LOOP_INTERVAL = 60           # Seconds to wait between cycles
