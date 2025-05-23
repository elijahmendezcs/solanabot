# File: config.py

# ─── Trading Pair & Order Size ────────────────────────────────────────────────
SYMBOL        = "SOL/USDT"     # Binance US spot pair
USDT_AMOUNT   = 10.0           # USD value per trade (used in backtests)

# Percent of quote balance to risk per trade
ORDER_FRACTION = 0.02          # 2% per trade

# Stop-loss percent from entry price
STOP_LOSS_PCT  = 0.01          # 1% hard stop

# Simulate trading fees and slippage
FEE_PCT       = 0.001          # 0.1% fee per trade
SLIPPAGE_PCT  = 0.0005         # 0.05% slippage per trade

# Paper-trading mode (True = simulate orders, False = place real orders)
PAPER_TRADING = True


# ─── SMA Crossover Settings ──────────────────────────────────────────────────
FAST_SMA = 10                  # “Fast” moving average period
SLOW_SMA = 100                 # “Slow” moving average period


# ─── RSI Strategy Settings ───────────────────────────────────────────────────
RSI_PERIOD     = 14            # Period for RSI calculation
RSI_OVERSOLD   = 25            # More stringent oversold threshold
RSI_OVERBOUGHT = 75            # More stringent overbought threshold


# ─── Exit Rules for RSI Strategy ─────────────────────────────────────────────
TP_PCT        = 0.005          # 0.5% take-profit
TRAIL_PCT     = 0.002          # 0.2% trailing stop
MAX_HOLD_MINS = 15             # e.g. 3 bars of 5m data


# ─── ATR‐Based Regime Detection ────────────────────────────────────────────────
ATR_PERIOD     = 14            # Bars for ATR calculation
ATR_THRESHOLD  = 0.005         # ATR / price > 0.5% → trending


# ─── Loop & Data Settings ───────────────────────────────────────────────────
TIMEFRAME     = "5m"           # 5-minute bars for stable heartbeats
OHLCV_LIMIT   = SLOW_SMA + 1
LOOP_INTERVAL = 5              # Seconds to wait between cycles

# Debug settings
DEBUG = False                   # Toggle debug prints in realtime feed
