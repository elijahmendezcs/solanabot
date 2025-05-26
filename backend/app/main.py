from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from pathlib import Path
import sqlite3
import os
import json
import redis

# ─── CORS ─────────────────────────────────────────────────────────────────────
from fastapi.middleware.cors import CORSMiddleware

# Your existing imports for grid and MACD backtest
from grid_backtest import grid_search_with_winrate
from backtest_macd import run_backtest_macd, DummyExchange as MacdDummyExchange
from strategies.macd import MacdStrategy
from config import SYMBOL, TIMEFRAME, FEE_PCT, SLIPPAGE_PCT, USDT_AMOUNT

app = FastAPI()

# Allow the dashboard (Next.js dev server) to make cross‑origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve path to trades.db
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH  = BASE_DIR / "data" / "trades.db"

# ─── Redis Setup ───────────────────────────────────────────────────────────────
REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client  = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@app.get("/health")
def health():
    return {"status": "ok"}


def get_connection():
    try:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {e}")


@app.get("/trades")
def list_trades(
    symbol: Optional[str]   = None,
    strategy: Optional[str] = None,
    limit:   int            = 100
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
        SELECT
          symbol,
          strategy,
          SUM(cost)    AS total_pnl,
          COUNT(*)     AS trade_count
        FROM trades
        GROUP BY symbol, strategy
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/grid/sma")
def sma_grid(
    fast: List[int] = Query(..., description="Fast SMA periods"),
    slow: List[int] = Query(..., description="Slow SMA periods")
):
    """
    Run SMA grid search with caching.
    """
    # Build a cache key
    key = f"sma:{','.join(map(str,fast))}:{','.join(map(str,slow))}"
    if cached := redis_client.get(key):
        return json.loads(cached)

    # Cache miss → compute
    results = grid_search_with_winrate(fast, slow, FEE_PCT, SLIPPAGE_PCT)
    # Store in Redis for 1h
    redis_client.set(key, json.dumps(results), ex=3600)
    return results


@app.get("/grid/macd")
def macd_grid(
    fast:   List[int] = Query(..., description="MACD fast EMA periods"),
    slow:   List[int] = Query(..., description="MACD slow EMA periods"),
    signal: int       = Query(..., description="MACD signal EMA period")
):
    """
    Run MACD grid search with caching.
    """
    key = f"macd:{','.join(map(str,fast))}:{','.join(map(str,slow))}:{signal}"
    if cached := redis_client.get(key):
        return json.loads(cached)

    out = []
    # You might pre‑fetch bars once, but here we use your runner per combo
    for f in fast:
        for s in slow:
            if s <= f:
                continue
            # Backtest
            res = run_backtest_macd()
            trades = res["trades"]
            wins   = sum(1 for t in trades if t["pnl"] > 0)
            count  = len(trades)
            win_rate = wins / count if count else 0.0

            out.append({
                "fast":       f,
                "slow":       s,
                "signal":     signal,
                "total_pnl":  res["total_pnl"],
                "trade_count": count,
                "win_rate":   win_rate
            })

    redis_client.set(key, json.dumps(out), ex=3600)
    return out
