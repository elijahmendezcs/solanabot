# File: tests/test_rsi.py

import pytest
from strategies.rsi import RsiStrategy

class DummyExch:
    def amount_to_precision(self, symbol, amt): return amt
    def fetch_balance(self): return {"free": {"SOL": 1.0}}

@pytest.fixture
def strat():
    return RsiStrategy(
        DummyExch(),
        {"symbol":"SOL/USDT", "usdt_amount":10, "rsi_period":5, "overbought":60, "oversold":40}
    )

def gen_close_series(values):
    return [[None,None,None,None, v, None] for v in values]

def test_rsi_buy_cross(strat):
    # RSI falling then rising through 40
    closes = [50,48,45,42,38,40,42,45]  # crosses up through 40 at index 5->6
    bars = gen_close_series(closes)
    sigs = [strat.on_bar(bars[:i+1]) for i in range(len(bars))]
    # Expect buy only once when cross back above 40
    assert any(s and s["side"]=="buy" for s in sigs)

def test_rsi_sell_cross(strat):
    # RSI rising then falling through 60
    closes = [50,55,58,62,65,60,58]  # crosses down through 60 at index 4->5
    bars = gen_close_series(closes)
    # manually set last_rsi high
    strat._last_rsi = 62
    sigs = [strat.on_bar(bars[:i+1]) for i in range(len(bars))]
    assert any(s and s["side"]=="sell" for s in sigs)
