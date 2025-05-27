from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from pathlib import Path
import sqlite3
import os
import json
import redis
import asyncio

# ─── CORS ─────────────────────────────────────────────────────────────────────
from fastapi.middleware.cors import CORSMiddleware

# Data fetch
from exchange import fetch_ohlcv

# Grid & MACD backtests
from backtests.grid_backtest import grid_search_with_winrate
from backtests.backtest_macd import run_backtest_macd, DummyExchange as MacdDummyExchange
from strategies.macd import MacdStrategy

# Notifications (Telegram alerts)
import notifications

# Config defaults
from config import SYMBOL, TIMEFRAME, FEE_PCT, SLIPPAGE_PCT, USDT_AMOUNT

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Paths & Redis ────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parents[2]
DB_PATH      = BASE_DIR / "data" / "trades.db"
REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Bot state & thresholds
BOT_STATE_KEY       = "bot:state"       # "running", "paused", "stopped"
DRAWDOWN_KEY        = "bot:drawdown_threshold"  # e.g. 0.15 for 15%


def get_connection():
    try:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.get("/trades")
def list_trades(
    symbol:    Optional[str] = None,
    strategy:  Optional[str] = None,
    limit:     int            = 100
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


@app.get("/equity_curve")
def equity_curve(
    symbol:    Optional[str] = Query(None, description="Filter by symbol, e.g. 'SOL/USDT'"),
    strategy:  Optional[str] = Query(None, description="Filter by strategy class name")
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
        ts   = row["timestamp"]
        cost = row["cost"]
        cum += cost
        series.append({"timestamp": ts, "cum_pnl": cum})

    conn.close()
    return series


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


# ─── Bot Control Endpoints ────────────────────────────────────────────────────

@app.post("/bot/start")
def bot_start():
    redis_client.set(BOT_STATE_KEY, "running")
    return {"status": "running"}

@app.post("/bot/pause")
def bot_pause():
    redis_client.set(BOT_STATE_KEY, "paused")
    return {"status": "paused"}

@app.post("/bot/stop")
def bot_stop():
    redis_client.set(BOT_STATE_KEY, "stopped")
    return {"status": "stopped"}

@app.get("/bot/status")
def bot_status():
    state = redis_client.get(BOT_STATE_KEY) or "unknown"
    return {"status": state}

# ─── Kill-Switch Endpoints ───────────────────────────────────────────────────

@app.get("/kill-switch")
def get_kill_switch():
    """Get current drawdown threshold (decimal)."""
    val = redis_client.get(DRAWDOWN_KEY)
    return {"threshold": float(val) if val else None}

@app.post("/kill-switch")
def set_kill_switch(
    threshold: float = Query(..., description="Drawdown threshold as decimal, e.g. 0.15 for 15%")
):
    """Set a global drawdown kill-switch threshold."""
    if threshold <= 0 or threshold >= 1:
        raise HTTPException(status_code=400, detail="Threshold must be between 0 and 1")
    redis_client.set(DRAWDOWN_KEY, threshold)
    return {"threshold": threshold}


# ─── Bot Control State & Loop ─────────────────────────────────────────────────

bot_pause_event = asyncio.Event()
bot_pause_event.set()  # when clear() means "paused", set() means "running"
bot_stop_event  = asyncio.Event()

async def bot_loop():
    """
    A minimal loop that you can later replace with your actual
    live-engine logic. It now includes a drawdown check.
    """
    while not bot_stop_event.is_set():
        # Check kill-switch drawdown
        raw_thresh = redis_client.get(DRAWDOWN_KEY)
        if raw_thresh:
            thresh = float(raw_thresh)
            # compute drawdown from trades
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT cost FROM trades ORDER BY timestamp ASC")
            cum = 0.0
            peak = 0.0
            max_dd = 0.0
            for row in cur.fetchall():
                cum += row['cost']
                peak = max(peak, cum)
                if peak > 0:
                    dd = (peak - cum) / peak
                    max_dd = max(max_dd, dd)
            conn.close()
            if max_dd >= thresh:
                # Trigger kill-switch
                notifications.send_telegram(
                    f"Kill-switch triggered: drawdown at {max_dd*100:.2f}% >= threshold {thresh*100:.2f}%"
                )
                bot_stop_event.set()
                break

        await bot_pause_event.wait()         # block while paused
        # <-- here you'd call your live-engine's iteration, e.g. run_one_cycle()
        await asyncio.sleep(1)               # throttle loop

# Kick off loop on startup
@app.on_event("startup")
async def start_bot_background_task():
    asyncio.create_task(bot_loop())
