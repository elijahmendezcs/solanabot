# File: config.py

# ─── Trading Pair & Order Size ────────────────────────────────────────────────
SYMBOL        = "SOL/USD"     # Kraken’s SOL/USD market
USDT_AMOUNT   = 10.0          # USD value per trade (used in backtests)

# Percent of quote balance to risk per trade
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
RSI_OVERSOLD   = 25           # More stringent oversold threshold
RSI_OVERBOUGHT = 75           # More stringent overbought threshold


# ─── Exit Rules for RSI Strategy ─────────────────────────────────────────────
# Take-profit: lock in gains when price moves this far above entry (0.5%)
TP_PCT        = 0.005         # 0.5% take-profit

# Trailing stop: trail entry high by this percent (0.2%)
TRAIL_PCT     = 0.002         # 0.2% trailing stop

# Time-cap: maximum minutes to hold a trade if other exits not triggered
# Using 5m bars, 3 bars = 15 minutes
MAX_HOLD_MINS = 15            # e.g. 3 bars of 5m data


# ─── Loop & Data Settings ───────────────────────────────────────────────────
TIMEFRAME     = "5m"          # Kraken-supported 5-minute bars
OHLCV_LIMIT   = SLOW_SMA + 1  # How many bars to fetch each cycle
LOOP_INTERVAL = 5             # Seconds to wait between cycles
