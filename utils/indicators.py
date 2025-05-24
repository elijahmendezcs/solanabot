# File: utils/indicators.py

import statistics

"""
Utility functions for technical indicators.
"""

def true_ranges(bars):
    """
    Compute the True Range for each bar in a list.
    bars: list of [timestamp, open, high, low, close, volume]
    Returns a list of TR values, one per bar (skipping the first).
    """
    trs = []
    for i in range(1, len(bars)):
        _, o, h, l, c, _ = bars[i]
        prev_close = bars[i-1][4]
        tr = max(
            h - l,
            abs(h - prev_close),
            abs(l - prev_close)
        )
        trs.append(tr)
    return trs

def atr(bars, period):
    """
    Calculate the Average True Range over the last `period` bars.
    Returns a float (0.0 if not enough data to compute any TR).
    """
    window = bars[-(period + 1):]
    trs = true_ranges(window)
    if not trs:
        return 0.0
    if len(trs) < period:
        return sum(trs) / len(trs)
    return sum(trs[-period:]) / period

def ema(values, period):
    """
    Compute the Exponential Moving Average over the entire list `values`
    using a smoothing factor α = 2/(period+1). Returns a list of EMA values
    of the same length as `values` (with first EMA = simple average of first
    `period` values).
    """
    if len(values) < period:
        return [None] * len(values)
    emas = []
    sma = sum(values[:period]) / period
    emas.extend([None] * (period - 1))
    emas.append(sma)
    alpha = 2 / (period + 1)
    for price in values[period:]:
        prev = emas[-1]
        next_ema = (price - prev) * alpha + prev
        emas.append(next_ema)
    return emas

def macd_lines(closes, fast_period, slow_period, signal_period):
    """
    Given a list of closing prices, return three equal-length lists:
      (macd_line, signal_line, histogram)
    """
    fast_ema = ema(closes, fast_period)
    slow_ema = ema(closes, slow_period)
    macd_line = [
        f - s if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema)
    ]
    valid = [m for m in macd_line if m is not None]
    sig_vals = ema(valid, signal_period) if len(valid) >= signal_period else []
    signal_line = [None] * (len(macd_line) - len(sig_vals)) + sig_vals
    hist = [
        m - s if (m is not None and s is not None) else None
        for m, s in zip(macd_line, signal_line)
    ]
    return macd_line, signal_line, hist

def bollinger_bands(closes, period=20, num_std_dev=2):
    """
    Compute Bollinger Bands for a list of closing prices.
    Returns three lists: (lower_band, middle_sma, upper_band)
    """
    # Not enough data
    if len(closes) < period:
        return [None] * len(closes), [None] * len(closes), [None] * len(closes)

    # Compute middle band (SMA)
    middle = []
    for i in range(len(closes)):
        if i < period - 1:
            middle.append(None)
        else:
            window = closes[i-period+1:i+1]
            middle.append(sum(window) / period)

    # Compute standard deviation over the same window
    std_dev = []
    for i in range(len(closes)):
        if i < period - 1:
            std_dev.append(None)
        else:
            window = closes[i-period+1:i+1]
            std_dev.append(statistics.pstdev(window))

    # Compute upper and lower bands
    upper = []
    lower = []
    for m, sd in zip(middle, std_dev):
        if m is None or sd is None:
            upper.append(None)
            lower.append(None)
        else:
            upper.append(m + num_std_dev * sd)
            lower.append(m - num_std_dev * sd)

    return lower, middle, upper
