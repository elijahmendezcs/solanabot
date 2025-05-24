import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from grid_backtest import grid_search, grid_search_with_winrate
from backtest_macd import DummyExchange as MacdDummyExchange
from strategies.macd import MacdStrategy
from strategies.bollinger import BollingerStrategy
from backtest_bollinger import DummyExchange as BollDummyExchange
from exchange import fetch_ohlcv
from config import SYMBOL, TIMEFRAME, FEE_PCT, SLIPPAGE_PCT, USDT_AMOUNT

st.set_page_config(layout="wide", page_title="SolanaBot Parameter Explorer")
st.title("📈 SolanaBot Strategy Explorer")

mode = st.sidebar.selectbox(
    "Select mode", ["SMA Grid", "MACD Grid", "Bollinger Grid"]
)

if mode == "SMA Grid":
    st.sidebar.header("SMA Parameters")
    fast_range = st.sidebar.slider("Fast SMA range", 5, 50, (5, 30), step=5)
    slow_range = st.sidebar.slider("Slow SMA range", 50, 200, (50, 120), step=10)

    fast_list = list(range(fast_range[0], fast_range[1] + 1, 5))
    slow_list = list(range(slow_range[0], slow_range[1] + 1, 10))

    results_pnl = grid_search(fast_list, slow_list, FEE_PCT, SLIPPAGE_PCT)
    results_wr  = grid_search_with_winrate(fast_list, slow_list, FEE_PCT, SLIPPAGE_PCT)

    df_pnl = (
        pd.DataFrame(results_pnl)
        .pivot(index="fast", columns="slow", values="total_pnl")
    )
    df_wr = (
        pd.DataFrame(results_wr)
        .pivot(index="fast", columns="slow", values="win_rate")
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Total P&L Heatmap")
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(
            df_pnl,
            annot=True,
            fmt=".1f",
            cmap="viridis",
            linewidths=0.5,
            linecolor="white",
            annot_kws={"size": 6},
            cbar_kws={"label": "Total P&L (USDT)"},
            ax=ax,
        )
        ax.set_xlabel("Slow SMA")
        ax.set_ylabel("Fast SMA")
        st.pyplot(fig)

    with col2:
        st.subheader("Win Rate Heatmap")
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(
            df_wr,
            annot=True,
            fmt=".2f",
            cmap="YlGnBu",
            linewidths=0.5,
            linecolor="white",
            annot_kws={"size": 6},
            cbar_kws={"label": "Win Rate"},
            ax=ax,
        )
        ax.set_xlabel("Slow SMA")
        ax.set_ylabel("Fast SMA")
        st.pyplot(fig)

elif mode == "MACD Grid":
    st.sidebar.header("MACD Parameters")
    fast_range = st.sidebar.slider("Fast EMA range", 4, 30, (8, 20), step=2)
    slow_range = st.sidebar.slider("Slow EMA range", 10, 80, (26, 60), step=2)
    signal     = st.sidebar.slider("Signal EMA", 4, 20, 9, step=1)

    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)

    data = []
    for fast in range(fast_range[0], fast_range[1] + 1, 2):
        for slow in range(slow_range[0], slow_range[1] + 1, 2):
            if slow <= fast:
                continue
            dummy = MacdDummyExchange()
            strat = MacdStrategy(dummy, {
                "symbol": SYMBOL,
                "usdt_amount": USDT_AMOUNT,
                "macd_fast": fast,
                "macd_slow": slow,
                "macd_signal": signal,
            })

            pnls = []
            position = None
            entry_cost = None

            for i, bar in enumerate(bars):
                sig = strat.on_bar(bars[: i + 1])
                price = bar[4]
                if sig and sig["side"] == "buy" and position is None:
                    slipped    = price * (1 + SLIPPAGE_PCT)
                    entry_cost = slipped * (1 + FEE_PCT)
                    position   = True
                elif sig and sig["side"] == "sell" and position:
                    slipped  = price * (1 - SLIPPAGE_PCT)
                    proceeds = slipped * (1 - FEE_PCT)
                    pnls.append(proceeds - entry_cost)
                    position = None

            if position:
                price    = bars[-1][4]
                slipped  = price * (1 - SLIPPAGE_PCT)
                proceeds = slipped * (1 - FEE_PCT)
                pnls.append(proceeds - entry_cost)

            total    = sum(pnls)
            wins     = sum(1 for p in pnls if p > 0)
            win_rate = wins / len(pnls) if pnls else 0.0
            data.append({
                "fast": fast,
                "slow": slow,
                "total_pnl": total,
                "win_rate": win_rate,
            })

    df_macd = pd.DataFrame(data)
    df_pnl_m = df_macd.pivot(index="fast", columns="slow", values="total_pnl")
    df_wr_m  = df_macd.pivot(index="fast", columns="slow", values="win_rate")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"MACD P&L (signal={signal})")
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(
            df_pnl_m,
            annot=True,
            fmt=".1f",
            cmap="viridis",
            linewidths=0.5,
            linecolor="white",
            annot_kws={"size": 6},
            cbar_kws={"label": "Total P&L (USDT)"},
            ax=ax,
        )
        ax.set_xlabel("Slow EMA")
        ax.set_ylabel("Fast EMA")
        st.pyplot(fig)

    with col2:
        st.subheader(f"MACD Win Rate (signal={signal})")
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(
            df_wr_m,
            annot=True,
            fmt=".2f",
            cmap="YlGnBu",
            linewidths=0.5,
            linecolor="white",
            annot_kws={"size": 6},
            cbar_kws={"label": "Win Rate"},
            ax=ax,
        )
        ax.set_xlabel("Slow EMA")
        ax.set_ylabel("Fast EMA")
        st.pyplot(fig)

else:  # Bollinger Grid
    st.sidebar.header("Bollinger Bands Parameters")
    period_range = st.sidebar.slider("BB Period range", 5, 100, (20, 20), step=1)
    std_range    = st.sidebar.slider("Std Dev range", 1, 3, (2, 2), step=1)

    bars = fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=500)
    dummy = BollDummyExchange()
    data = []
    for period in range(period_range[0], period_range[1] + 1):
        for std in range(std_range[0], std_range[1] + 1):
            strat = BollingerStrategy(dummy, {"symbol": SYMBOL, "bb_period": period, "bb_std_dev": std})
            pnls = []
            position = None
            entry_cost = None
            for i, bar in enumerate(bars):
                sig = strat.on_bar(bars[: i + 1])
                price = bar[4]
                if sig and sig["side"] == "buy" and position is None:
                    slipped    = price * (1 + SLIPPAGE_PCT)
                    entry_cost = slipped * (1 + FEE_PCT)
                    position   = True
                elif sig and sig["side"] == "sell" and position:
                    slipped  = price * (1 - SLIPPAGE_PCT)
                    proceeds = slipped * (1 - FEE_PCT)
                    pnls.append(proceeds - entry_cost)
                    position = None
            if position:
                price    = bars[-1][4]
                slipped  = price * (1 - SLIPPAGE_PCT)
                proceeds = slipped * (1 - FEE_PCT)
                pnls.append(proceeds - entry_cost)

            total    = sum(pnls)
            wins     = sum(1 for p in pnls if p > 0)
            win_rate = wins / len(pnls) if pnls else 0.0
            data.append({"period": period, "std_dev": std, "total_pnl": total, "win_rate": win_rate})

    df = pd.DataFrame(data)
    df_pnl = df.pivot(index="period", columns="std_dev", values="total_pnl")
    df_wr  = df.pivot(index="period", columns="std_dev", values="win_rate")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Bollinger Bands P&L Heatmap")
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(
            df_pnl,
            annot=True,
            fmt=".1f",
            cmap="viridis",
            linewidths=0.5,
            linecolor="white",
            annot_kws={"size": 6},
            cbar_kws={"label": "Total P&L (USDT)"},
            ax=ax,
        )
        ax.set_xlabel("Std Dev")
        ax.set_ylabel("Period")
        st.pyplot(fig)

    with col2:
        st.subheader("Bollinger Bands Win Rate Heatmap")
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(
            df_wr,
            annot=True,
            fmt=".2f",
            cmap="YlGnBu",
            linewidths=0.5,
            linecolor="white",
            annot_kws={"size": 6},
            cbar_kws={"label": "Win Rate"},
            ax=ax,
        )
        ax.set_xlabel("Std Dev")
        ax.set_ylabel("Period")
        st.pyplot(fig)
