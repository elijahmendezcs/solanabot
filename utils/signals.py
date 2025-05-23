# File: utils/signals.py

import statistics

def generate_sma_signal(closes, fast, slow):
    """
    Given a list of closing prices, return "buy", "sell", or None
    based on a simple fast/slow SMA crossover.
    """
    # Need at least slow+1 points to compare yesterday vs today
    if len(closes) < slow + 1:
        return None

    sma_fast_prev = statistics.mean(closes[-(fast+1):-1])
    sma_slow_prev = statistics.mean(closes[-(slow+1):-1])
    sma_fast_now  = statistics.mean(closes[-fast:])
    sma_slow_now  = statistics.mean(closes[-slow:])

    if sma_fast_prev <= sma_slow_prev and sma_fast_now > sma_slow_now:
        return "buy"
    if sma_fast_prev >= sma_slow_prev and sma_fast_now < sma_slow_now:
        return "sell"
    return None
