# backend/app/main.py

import sys
from pathlib import Path

# ─── add project root to PYTHONPATH so "import exchange" etc. works ─────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import os
import json
import sqlite3
import asyncio
import redis

from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware

# ─── your existing imports ───────────────────────────────────────────────────
from exchange import fetch_ohlcv
from grid_backtest import grid_search_with_winrate
from backtest_macd import run_backtest_macd, DummyExchange as MacdDummyExchange
from strategies.macd import MacdStrategy
from config import SYMBOL, TIMEFRAME, FEE_PCT, SLIPPAGE_PCT, USDT_AMOUNT

# ─── app + CORS ───────────────────────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths & Redis client ────────────────────────────────────────────────────
DB_PATH     = ROOT / "data" / "trades.db"
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client= redis.Redis.from_url(REDIS_URL, decode_responses=True)

def get_connection():
    try:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")

# ─── HEALTH ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}

# ─── OHLCV ───────────────────────────────────────────────────────────────────
@app.get("/ohlcv")
def get_ohlcv(
    symbol:    str = Query(..., description="Trading pair symbol, e.g. 'SOL/USDT'"),
    timeframe: str = Query(TIMEFRAME, description="Timeframe string, e.g. '5m'"),
    limit:     int = Query(500, description="Number of bars to fetch")
):
    try:
        return fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching OHLCV: {e}")

# ─── TRADES ──────────────────────────────────────────────────────────────────
@app.get("/trades")
def list_trades(
    symbol:   Optional[str] = None,
    strategy: Optional[str] = None,
    limit:    int            = 100
):
    conn   = get_connection()
    cursor = conn.cursor()

    query, params = "SELECT * FROM trades", []
    filters = []
    if symbol:
        filters.append("symbol = ?");   params.append(symbol)
    if strategy:
        filters.append("strategy = ?"); params.append(strategy)
    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── PNL SUMMARY ─────────────────────────────────────────────────────────────
@app.get("/pnl")
def pnl_summary():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT symbol, strategy,
               SUM(cost)    AS total_pnl,
               COUNT(*)     AS trade_count
        FROM trades
        GROUP BY symbol, strategy
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── EQUITY CURVE ─────────────────────────────────────────────────────────────
@app.get("/equity_curve")
def equity_curve(
    symbol:   Optional[str] = Query(None, description="Filter by symbol, e.g. 'SOL/USDT'"),
    strategy: Optional[str] = Query(None, description="Filter by strategy class name")
):
    conn   = get_connection()
    cursor = conn.cursor()

    query, params = "SELECT timestamp, cost FROM trades", []
    filters = []
    if symbol:
        filters.append("symbol = ?");   params.append(symbol)
    if strategy:
        filters.append("strategy = ?"); params.append(strategy)
    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY timestamp ASC"
    cursor.execute(query, params)

    cum    = 0.0
    series = []
    for row in cursor.fetchall():
        cum += row["cost"]
        series.append({"timestamp": row["timestamp"], "cum_pnl": cum})

    conn.close()
    return series

# ─── SMA GRID ────────────────────────────────────────────────────────────────
@app.get("/grid/sma")
def sma_grid(
    fast: List[int] = Query(..., description="Fast SMA periods"),
    slow: List[int] = Query(..., description="Slow SMA periods")
):
    key = f"sma:{','.join(map(str,fast))}:{','.join(map(str,slow))}"
    if cached := redis_client.get(key):
        return json.loads(cached)

    results = grid_search_with_winrate(fast, slow, FEE_PCT, SLIPPAGE_PCT)
    redis_client.set(key, json.dumps(results), ex=3600)
    return results

# ─── MACD GRID ───────────────────────────────────────────────────────────────
@app.get("/grid/macd")
def macd_grid(
    fast:   List[int] = Query(..., description="MACD fast EMA periods"),
    slow:   List[int] = Query(..., description="MACD slow EMA periods"),
    signal: int       = Query(..., description="MACD signal EMA period")
):
    key = f"macd:{','.join(map(str,fast))}:{','.join(map(str,slow))}:{signal}"
    if cached := redis_client.get(key):
        return json.loads(cached)

    out = []
    for f in fast:
        for s in slow:
            if s <= f:
                continue
            res    = run_backtest_macd()
            trades = res["trades"]
            wins   = sum(1 for t in trades if t.get("pnl", 0) > 0)
            count  = len(trades)
            win_rate = wins / count if count else 0.0

            out.append({
                "fast":        f,
                "slow":        s,
                "signal":      signal,
                "total_pnl":   res.get("total_pnl", 0),
                "trade_count": count,
                "win_rate":    win_rate
            })

    redis_client.set(key, json.dumps(out), ex=3600)
    return out

# ─── BOT CONTROL LOOP ────────────────────────────────────────────────────────
bot_pause_event = asyncio.Event()
bot_pause_event.set()   # when clear() ⇒ paused, set() ⇒ running
bot_stop_event  = asyncio.Event()

async def bot_loop():
    # replace this sleep with your real "run one iteration" call
    while not bot_stop_event.is_set():
        await bot_pause_event.wait()   # blocks when paused
        # e.g. await run_one_cycle()
        await asyncio.sleep(1)

@app.on_event("startup")
async def start_bot_background_task():
    asyncio.create_task(bot_loop())

# ─── BOT CONTROL ENDPOINTS ──────────────────────────────────────────────────
@app.post("/bot/start")
async def start_bot():
    bot_pause_event.set()
    return {"status": "running"}

@app.post("/bot/pause")
async def pause_bot():
    bot_pause_event.clear()
    return {"status": "paused"}

@app.post("/bot/stop")
async def stop_bot():
    bot_stop_event.set()
    bot_pause_event.set()   # un‐block if paused
    return {"status": "stopped"}

@app.get("/bot/status")
async def status_bot():
    if bot_stop_event.is_set():
        state = "stopped"
    elif not bot_pause_event.is_set():
        state = "paused"
    else:
        state = "running"
    return {"status": state}
