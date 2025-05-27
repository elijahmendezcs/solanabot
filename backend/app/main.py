import asyncio
import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional

import redis
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# core exchange + live engine
from exchange import init_exchange, fetch_ohlcv
from logger import setup_logger
from notifications import send_telegram
from db import init_db, log_trade_db
from config import (
    SYMBOLS,
    TIMEFRAME,
    USDT_AMOUNT,
    PAPER_TRADING,
    FAST_SMA,
    SLOW_SMA,
    ATR_PERIOD,
    ATR_THRESHOLD,
    MACD_FAST_PERIOD,
    MACD_SLOW_PERIOD,
    MACD_SIGNAL_PERIOD,
    FEE_PCT,
    SLIPPAGE_PCT,
)
from utils.indicators import atr
from strategies.sma_crossover import SmaCrossover
from strategies.rsi import RsiStrategy
from strategies.macd import MacdStrategy
from strategies.bollinger import BollingerStrategy

# backtest endpoints
from backtests.grid_backtest import grid_search_with_winrate
from backtests.backtest_macd import run_backtest_macd

# real-time data feeder
from realtime import Realtime

# ─── FastAPI setup ──────────────────────────────────────────────────────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths & Clients ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "trades.db"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

BOT_STATE_KEY = "bot:state"
DRAWDOWN_KEY = "bot:drawdown_threshold"

# ─── DB helper ───────────────────────────────────────────────────────────────
def get_connection():
    try:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

# ─── Helper to format notifications ───────────────────────────────────────────
def format_message(symbol, strategy_name, side, amount, price, reason=None):
    msg = f"{symbol} | {strategy_name}: {side.upper()} {amount} @ {price:.2f}"
    if reason:
        msg += f" ({reason})"
    return msg

# ─── Real-time engine per-symbol ─────────────────────────────────────────────
async def run_symbol(symbol: str):
    log = setup_logger()
    exchange = init_exchange()

    # instantiate strategies
    strategy_objs = []
    for cls in (SmaCrossover, RsiStrategy, MacdStrategy, BollingerStrategy):
        params = {"symbol": symbol, "usdt_amount": USDT_AMOUNT}
        if cls is SmaCrossover:
            params.update({"fast": FAST_SMA, "slow": SLOW_SMA})
        if cls is MacdStrategy:
            params.update({
                "macd_fast": MACD_FAST_PERIOD,
                "macd_slow": MACD_SLOW_PERIOD,
                "macd_signal": MACD_SIGNAL_PERIOD,
            })
        strategy_objs.append(cls(exchange, params))

    ws_slow = Realtime(symbol=symbol, interval=TIMEFRAME)
    ws_fast = Realtime(symbol=symbol, interval="1m")

    # emergency stop-loss monitor
    async def monitor_emergency():
        async for bar in ws_fast.ohlcv_stream():
            price = bar[4]
            for strat in strategy_objs:
                if getattr(strat, "stop_loss_price", None) and price <= strat.stop_loss_price:
                    asset = symbol.split("/")[0]
                    bal = exchange.fetch_balance()["free"].get(asset, 0)
                    if bal > 0:
                        amt = exchange.amount_to_precision(symbol, bal)
                        cost = price * float(amt)
                        log_trade_db(symbol, strat.__class__.__name__, "sell", price, float(amt), cost, "stop-loss-emergency")
                        send_telegram(format_message(symbol, strat.__class__.__name__, "sell", amt, price, "stop-loss-emergency"))
                        log.info(f"[EMERGENCY][{'PAPER' if PAPER_TRADING else ''}][{symbol}] SELL {amt} @ {price:.2f}")
    asyncio.create_task(monitor_emergency())

    # main loop (slow feed)
    max_period = max(getattr(s, "slow", getattr(s, "period", 0)) for s in strategy_objs)
    ohlcv_limit = max_period + 1
    bars = []

    log.info(f"▶️ Starting engine for {symbol}")
    async for candle in ws_slow.ohlcv_stream():
        bars.append(candle)
        if len(bars) > ohlcv_limit:
            bars = bars[-ohlcv_limit:]

        last_price = bars[-1][4]
        current_atr = atr(bars, ATR_PERIOD)
        volatility = current_atr / last_price if last_price else 0
        is_trending = volatility > ATR_THRESHOLD
        log.info(f"[{symbol}] Volatility: {volatility:.3%} → {'Trending' if is_trending else 'Ranging'}")

        for strat in strategy_objs:
            # regime gating
            if isinstance(strat, SmaCrossover) and not is_trending: continue
            if isinstance(strat, RsiStrategy) and is_trending: continue
            if isinstance(strat, BollingerStrategy) and is_trending: continue

            sig = strat.on_bar(bars)
            if not sig: continue

            side, raw_amt = sig["side"], sig["amount"]
            reason = sig.get("reason")
            price = last_price
            cost = price * float(raw_amt)

            # log + notify
            log_trade_db(symbol, strat.__class__.__name__, side, price, float(raw_amt), cost, reason)
            send_telegram(format_message(symbol, strat.__class__.__name__, side, raw_amt, price, reason))

            if PAPER_TRADING:
                log.info(f"[PAPER][{symbol}] {strat.__class__.__name__}: {side.upper()} {raw_amt} @ {price:.2f}")
            else:
                market = exchange.markets[symbol]
                min_amt = market["limits"]["amount"]["min"]
                amt = float(raw_amt)
                if amt < min_amt:
                    log.info(f"Skipped {symbol} {side} {amt:.8f} — below min {min_amt}")
                    continue
                precise_amt = exchange.amount_to_precision(symbol, amt)
                try:
                    order = exchange.create_market_order(symbol, side, precise_amt)
                    log.info(f"[{symbol}] {strat.__class__.__name__}: {side.upper()} {precise_amt} @ {order['price']:.2f}")
                except Exception as e:
                    log.error(f"Order failed for {symbol} {side} {precise_amt}: {e}")

        await asyncio.sleep(0)

# ─── Bot control loop (with kill-switch) ────────────────────────────────────
bot_pause_event = asyncio.Event()
bot_pause_event.set()
bot_stop_event = asyncio.Event()

async def bot_loop():
    while not bot_stop_event.is_set():
        raw = redis_client.get(DRAWDOWN_KEY)
        if raw:
            thresh = float(raw)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT cost FROM trades ORDER BY timestamp ASC")
            cum = peak = max_dd = 0.0
            for r in cur.fetchall():
                cum += r["cost"]
                peak = max(peak, cum)
                if peak > 0:
                    dd = (peak - cum) / peak
                    max_dd = max(max_dd, dd)
            conn.close()
            if max_dd >= thresh:
                send_telegram(f"Kill-switch: drawdown {max_dd*100:.2f}% ≥ {thresh*100:.2f}%")
                bot_stop_event.set()
                break
        await bot_pause_event.wait()
        await asyncio.sleep(1)

# ─── Startup & Endpoints ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    init_db()
    # launch engine + bot loop
    for sym in SYMBOLS:
        asyncio.create_task(run_symbol(sym))
    asyncio.create_task(bot_loop())

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ohlcv")
def get_ohlcv_endpoint(symbol: str = Query(..., description="e.g. 'SOL/USDT'"), timeframe: str = Query(TIMEFRAME), limit: int = Query(500)):
    try:
        return fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trades")
def list_trades(symbol: Optional[str] = None, strategy: Optional[str] = None, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()
    query, params = "SELECT * FROM trades", []
    if symbol:
        query += " WHERE symbol = ?"; params.append(symbol)
    if strategy:
        query += (" AND" if params else " WHERE") + " strategy = ?"; params.append(strategy)
    query += " ORDER BY timestamp DESC LIMIT ?"; params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/pnl")
def pnl_summary():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, strategy, SUM(cost) AS total_pnl, COUNT(*) AS trade_count
        FROM trades GROUP BY symbol, strategy
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/equity_curve")
def equity_curve(symbol: Optional[str] = Query(None), strategy: Optional[str] = Query(None)):
    conn = get_connection()
    cursor = conn.cursor()
    query, params = "SELECT timestamp, cost FROM trades", []
    if symbol:
        query += " WHERE symbol = ?"; params.append(symbol)
    if strategy:
        query += (" AND" if symbol else " WHERE") + " strategy = ?"; params.append(strategy)
    query += " ORDER BY timestamp ASC"
    cursor.execute(query, params)
    cum, series = 0.0, []
    for row in cursor.fetchall():
        cum += row["cost"]
        series.append({"timestamp": row["timestamp"], "cum_pnl": cum})
    conn.close()
    return series

@app.get("/grid/sma")
def sma_grid(fast: List[int] = Query(...), slow: List[int] = Query(...)):
    key = f"sma:{','.join(map(str, fast))}:{','.join(map(str, slow))}"
    if cached := redis_client.get(key):
        return json.loads(cached)
    res = grid_search_with_winrate(fast, slow, FEE_PCT, SLIPPAGE_PCT)
    redis_client.set(key, json.dumps(res), ex=3600)
    return res

@app.get("/grid/macd")
def macd_grid(fast: List[int] = Query(...), slow: List[int] = Query(...), signal: int = Query(...)):
    key = f"macd:{','.join(map(str, fast))}:{','.join(map(str, slow))}:{signal}"
    if cached := redis_client.get(key):
        return json.loads(cached)
    out = []
    for f in fast:
        for s in slow:
            if s <= f: continue
            r = run_backtest_macd()
            trades = r.get("trades", [])
            wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
            count = len(trades)
            out.append({
                "fast": f, "slow": s, "signal": signal,
                "total_pnl": r.get("total_pnl", 0),
                "trade_count": count,
                "win_rate": wins / count if count else 0
            })
    redis_client.set(key, json.dumps(out), ex=3600)
    return out

@app.post("/bot/start")
def bot_start():
    redis_client.set(BOT_STATE_KEY, "running")
    bot_pause_event.set()
    return {"status": "running"}

@app.post("/bot/pause")
def bot_pause():
    redis_client.set(BOT_STATE_KEY, "paused")
    bot_pause_event.clear()
    return {"status": "paused"}

@app.post("/bot/stop")
def bot_stop():
    redis_client.set(BOT_STATE_KEY, "stopped")
    bot_stop_event.set()
    return {"status": "stopped"}

@app.get("/bot/status")
def bot_status():
    status = redis_client.get(BOT_STATE_KEY) or "unknown"
    return {"status": status.decode() if isinstance(status, bytes) else status}

@app.get("/kill-switch")
def get_kill_switch():
    val = redis_client.get(DRAWDOWN_KEY)
    return {"threshold": float(val) if val else None}

@app.post("/kill-switch")
def set_kill_switch(threshold: float = Query(..., ge=0.0, lt=1.0)):
    redis_client.set(DRAWDOWN_KEY, threshold)
    return {"threshold": threshold}
