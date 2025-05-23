# File: db.py
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("data", "trades.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    cost REAL NOT NULL,
    reason TEXT
);
"""

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()


def log_trade_db(symbol, strategy, side, price, amount, cost, reason=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ts = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO trades (timestamp, symbol, strategy, side, price, amount, cost, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ts, symbol, strategy, side, price, amount, cost, reason)
    )
    conn.commit()
    conn.close()
