# File: tests/test_bollinger.py

import os
import sys
import pytest

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from strategies.bollinger import BollingerStrategy

class DummyExch:
    def amount_to_precision(self, symbol, amt):
        return amt
    def fetch_balance(self):
        return {"free": {"USDT": 100.0, "SOL": 1.0}}

@pytest.fixture
def strat():
    # Use small period and std dev for testing
    return BollingerStrategy(
        DummyExch(),
        {"symbol": "SOL/USDT", "bb_period": 3, "bb_std_dev": 1}
    )


def gen_bars(values):
    """
    Generate OHLCV-like bars where only the close price matters.
    """
    return [[None, None, None, None, v, None] for v in values]


def test_bollinger_buy_and_sell(strat):
    # Create a sequence where price dips below lower band then rises above upper band
    closes = [10, 10, 10, 7, 7, 7, 10, 10, 10]
    bars = gen_bars(closes)

    signals = [strat.on_bar(bars[:i+1]) for i in range(len(bars))]

    # Expect at least one buy and one sell signal
    assert any(sig and sig.get("side") == "buy" for sig in signals), "No BUY signal detected"
    assert any(sig and sig.get("side") == "sell" for sig in signals), "No SELL signal detected"
