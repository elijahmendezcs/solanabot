# File: config.py

# ─── Trading Pair & Order Size ────────────────────────────────────────────────
SYMBOL        = "SOL/USDT"    # Which market to trade
USDT_AMOUNT   = 10.0          # (no longer used for sizing, but kept for backtests)

# Percent of USDT balance to risk per trade (e.g. 2% → 0.02)
ORDER_FRACTION = 0.02        

# Stop-loss percent from entry price (e.g. 1% → 0.01)
STOP_LOSS_PCT  = 0.01        

# ─── SMA Crossover Settings ──────────────────────────────────────────────────
FAST_SMA = 15                # “Fast” moving average period
SLOW_SMA = 30                # “Slow” moving average period

# ─── Loop & Data Settings ───────────────────────────────────────────────────
TIMEFRAME     = "1m"         # Candle timeframe for OHLCV
OHLCV_LIMIT   = SLOW_SMA + 1 # How many bars to fetch each cycle
LOOP_INTERVAL = 5            # Seconds to wait between cycles
