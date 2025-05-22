# File: utils/indicators.py

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
    Returns a float.
    """
    window = bars[-(period + 1):]
    trs = true_ranges(window)
    if len(trs) < period:
        return sum(trs) / len(trs)  # fallback if not enough data
    return sum(trs[-period:]) / period
