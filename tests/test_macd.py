# File: tests/test_macd.py

import os
import sys

# Ensure project root is on PYTHONPATH so `import strategies` works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from strategies.macd import MacdStrategy

class DummyExch:
    def amount_to_precision(self, symbol, amt):
        return amt
    def fetch_balance(self):
        return {"free": {"USDT": 100.0, "SOL": 1.0}}

@pytest.fixture
def strat():
    return MacdStrategy(
        DummyExch(),
        {
            "symbol": "SOL/USDT",
            "usdt_amount": 10,
            "macd_fast": 2,
            "macd_slow": 4,
            "macd_signal": 2
        }
    )

def gen_bars(values):
    # Create OHLCV-like bars where only the close matters
    return [[None, None, None, None, v, None] for v in values]

def test_macd_buy_and_sell(strat):
    # First downtrend to drive histogram ≤0, then uptrend to cross >0, then pull back to cross <0
    closes = [10, 9, 8, 7, 6, 7, 8, 7, 6]
    bars = gen_bars(closes)

    signals = [strat.on_bar(bars[:i+1]) for i in range(len(bars))]

    assert any(sig and sig["side"] == "buy"  for sig in signals), "No BUY signal detected"
    assert any(sig and sig["side"] == "sell" for sig in signals), "No SELL signal detected"
