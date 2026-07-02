import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Set page to wide layout
st.set_page_config(layout="wide", page_title="Multi-Ticker Financial Dashboard v2.1")

# 1. Fetch System-Wide Market Context (VIX Status)
@st.cache_data(ttl=300)
def get_vix_data():
    try:
        vix = yf.Ticker("^VIX").history(period="1mo")
        if not vix.empty and len(vix) >= 2:
            current_vix = vix['Close'].iloc[-1]
            vix_change = ((vix['Close'].iloc[-1] - vix['Close'].iloc[-2]) / vix['Close'].iloc[-2]) * 100
            return current_vix, vix_change
    except Exception:
        pass
    return 0.0, 0.0

# 2. Extract Full Company Name Profile safely
@st.cache_data(ttl=3600)
def get_company_full_name(ticker):
    try:
        stock = yf.Ticker(ticker)
        if hasattr(stock, 'info') and stock.info and "longName" in stock.info:
            return stock.info["longName"]
    except Exception:
        pass
    return f"{ticker} Corporation"

# Helper: Fetch Beta from yfinance info
@st.cache_data(ttl=3600)
def get_beta(ticker):
    try:
        stock = yf.Ticker(ticker)
        if hasattr(stock, 'info') and stock.info and "beta" in stock.info:
            beta = stock.info["beta"]
            if beta is not None and not pd.isna(beta):
                return float(beta)
    except Exception:
        pass
    return None

# Helper: Fetch Mean Price Target from yfinance info
@st.cache_data(ttl=3600)
def get_mean_price_target(ticker):
    try:
        stock = yf.Ticker(ticker)
        if hasattr(stock, 'info') and stock.info:
            for key in ["targetMeanPrice", "target_mean_price", "meanPriceTarget", "mean_price_target"]:
                if key in stock.info and stock.info[key] is not None and not pd.isna(stock.info[key]):
                    return float(stock.info[key])
    except Exception:
        pass
    return None

# 3. Fetch and Process Ticker Technical Data
@st.cache_data(ttl=300)
def get_ticker_dashboard(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if df.empty or len(df) < 200:
            return None, None

        df = df.dropna(subset=['Open', 'High', 'Low', 'Close']).copy()

        # Compute Moving Averages
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        df['SMA_200'] = ta.sma(df['Close'], length=200)

        # Momentum Indicators
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MACD_Line'] = ta.ema(df['Close'], length=12) - ta.ema(df['Close'], length=26)
        df['Signal_Line'] = ta.ema(df['MACD_Line'], length=9)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        try:
            df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        except Exception:
            df['VWAP'] = df['Close']

        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
        df['Vol_SMA20'] = df['Vol_SMA20'].ffill().bfill()
        df['Vol_Breakout'] = df['Volume'] > (df['Vol_SMA20'] * 1.5)

        df['Resistance'] = df['High'].rolling(window=20).max()
        df['Support'] = df['Low'].rolling(window=20).min()

        # Weekly volume metrics
        df['Week'] = df.index.isocalendar().week
        df['Year'] = df.index.year
        df['YearWeek'] = df['Year'].astype(str) + '-W' + df['Week'].astype(str).str.zfill(2)

        # Last complete week volume
        last_week = df['YearWeek'].iloc[-1]
        last_week_data = df[df['YearWeek'] == last_week]
        last_weekly_volume = int(last_week_data['Volume'].sum()) if not last_week_data.empty else 0

        # Average weekly volume (last 12 weeks)
        unique_weeks = df['YearWeek'].unique()
        if len(unique_weeks) >= 2:
            recent_weeks = unique_weeks[-12:] if len(unique_weeks) >= 12 else unique_weeks
            weekly_volumes = []
            for w in recent_weeks:
                w_data = df[df['YearWeek'] == w]
                if not w_data.empty:
                    weekly_volumes.append(int(w_data['Volume'].sum()))
            avg_weekly_volume = int(sum(weekly_volumes) / len(weekly_volumes)) if weekly_volumes else 0
        else:
            avg_weekly_volume = last_weekly_volume

        df = df.ffill().bfill()

        current_price = float(df['Close'].iloc[-1])

        # Index-proof YTD computation block matrix
        current_year = pd.Timestamp.now().year
        ytd_df = df[df.index.year == current_year]
        ytd_change = 0.0
        if not ytd_df.empty:
            for i in range(len(ytd_df)):
                base_close = ytd_df['Close'].iloc[i]
                if pd.notna(base_close) and base_close > 0:
                    ytd_change = ((current_price - float(base_close)) / float(base_close)) * 100
                    break

        daily_change = ((current_price - float(df['Close'].iloc[-2])) / float(df['Close'].iloc[-2])) * 100
        weekly_change = ((current_price - float(df['Close'].iloc[-5])) / float(df['Close'].iloc[-5])) * 100

        # Fetch Beta
        beta_val = get_beta(ticker)

        # Fetch Mean Price Target
        mean_target = get_mean_price_target(ticker)

        metrics = {
            "price": current_price,
            "daily_change": daily_change,
            "weekly_change": weekly_change,
            "ytd_change": ytd_change,
            "rsi": float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0,
            "atr": float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else 0.0,
            "vol_breakout": bool(df['Vol_Breakout'].iloc[-1]),
            "support": float(df['Support'].iloc[-1]),
            "resistance": float(df['Resistance'].iloc[-1]),
            "vwap": float(df['VWAP'].iloc[-1]),
            "sma_20": float(df['SMA_20'].iloc[-1]),
            "sma_50": float(df['SMA_50'].iloc[-1]),
            "sma_200": float(df['SMA_200'].iloc[-1]),
            "last_weekly_volume": last_weekly_volume,
            "avg_weekly_volume": avg_weekly_volume,
            "beta": beta_val,
            "mean_target": mean_target
        }
        return df, metrics
    except Exception:
        return None, None

# 4. Compile Summary Table for All Watchlist Tickers
def generate_watchlist_summary(tickers):
    summary_data = []
    for t in tickers:
        try:
            df_t, metrics = get_ticker_dashboard(t)
            if metrics is not None and df_t is not None:
                summary_data.append({
                    "Ticker": t,
                    "Price ($)": round(metrics["price"], 1),
                    "Daily Chg (%)": round(metrics["daily_change"], 1),
                    "Weekly Chg (%)": round(metrics["weekly_change"], 1),
                    "YTD Chg (%)": round(metrics["ytd_change"], 1),
                    "RSI (14)": round(metrics["rsi"], 1),
                    "20 SMA ($)": round(metrics["sma_20"], 1),
                    "50 SMA ($)": round(metrics["sma_50"], 1),
                    "200 SMA ($)": round(metrics["sma_200"], 1),
                    "Support ($)": round(metrics["support"], 1),
                    "Resistance ($)": round(metrics["resistance"], 1),
                    "Last Wk Vol": metrics["last_weekly_volume"],
                    "Avg Wk Vol": metrics["avg_weekly_volume"],
                    "VWAP ($)": round(metrics["vwap"], 1),
                    "ATR ($)": round(metrics["atr"], 1),
                    "Beta": round(metrics["beta"], 1) if metrics["beta"] is not None else "N/A",
                    "Mean Target ($)": round(metrics["mean_target"], 1) if metrics["mean_target"] is not None else "N/A",
                    "Vol Breakout": "🚨 YES" if metrics["vol_breakout"] else "🟢 No"
                })
        except Exception:
            pass
    return pd.DataFrame(summary_data)

# 5. Convert a (possibly styled) DataFrame into a scrollable HTML table block
def styler_to_scrollable_html(styler_or_df, max_height="420px"):
    """Render a pandas Styler (or plain DataFrame) as a self-contained,
    scrollable HTML <table> block that can be embedded in the exported report.
    Cell colors/backgrounds applied via .style.apply()/.style.map() are preserved
    because Styler.to_html() bakes them in as inline CSS."""
    if isinstance(styler_or_df, pd.DataFrame):
        styler_or_df = styler_or_df.style
    try:
        styler_or_df = styler_or_df.hide(axis="index")
    except Exception:
        try:
            styler_or_df = styler_or_df.hide_index()
        except Exception:
            pass
    try:
        table_html = styler_or_df.to_html()
    except Exception:
        # Fallback: plain (unstyled) table if the Styler ever fails to render
        table_html = styler_or_df.data.to_html(index=False) if hasattr(styler_or_df, "data") else "<p>Table unavailable.</p>"
    return f'<div class="table-scroll" style="max-height:{max_height};">{table_html}</div>'


# 6. Build one self-contained HTML report covering Sections 1-4 for the Download Dashboard button
def generate_full_dashboard_html(active_ticker, full_company_name, metrics, vix_val, vix_pct,
                                  snapshot_html, plot_html, section3_html, legend3_html,
                                  section4_html, legend4_html, nasdaq_status_note=""):
    generated_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    css = """
    <style>
        body { background:#0e1117; color:#fafafa; font-family:'Segoe UI', Arial, sans-serif;
               margin:0; padding:24px 32px 60px 32px; }
        h1 { font-size:26px; margin-bottom:4px; }
        h2 { font-size:20px; margin-top:40px; border-bottom:1px solid #333; padding-bottom:6px; }
        .subtitle { color:#9aa0a6; margin-bottom:20px; }
        .metrics-row { display:flex; gap:16px; flex-wrap:wrap; margin:20px 0 30px 0; }
        .metric-card { background:#1c1f26; border:1px solid #30343c; border-radius:10px;
                        padding:14px 18px; min-width:180px; }
        .metric-card .label { font-size:12px; color:#9aa0a6; text-transform:uppercase; letter-spacing:.03em; }
        .metric-card .value { font-size:22px; font-weight:700; margin-top:4px; }
        .table-scroll { overflow:auto; max-width:100%; border:1px solid #30343c; border-radius:8px;
                         margin:12px 0 20px 0; background:#12151a; }
        table { border-collapse:collapse; width:100%; font-size:13px; }
        th, td { padding:6px 10px; text-align:left; white-space:nowrap; }
        thead th { position:sticky; top:0; background:#20242c; color:#fafafa; z-index:2;
                   border-bottom:2px solid #333; }
        tbody tr:nth-child(odd) { background:#161a20; }
        tbody tr:nth-child(even) { background:#12151a; }
        .legend-box { font-size:13px; color:#d0d0d0; line-height:1.9; margin:10px 0 24px 0; }
        .note { color:#f0ad4e; font-style:italic; margin:8px 0; }
        .footer { margin-top:50px; color:#666; font-size:12px; border-top:1px solid #333; padding-top:14px; }
        .plotly-wrap { border:1px solid #30343c; border-radius:8px; padding:6px; background:#12151a; }
    </style>
    """

    metrics_html = f"""
    <div class="metrics-row">
        <div class="metric-card"><div class="label">Current Price</div><div class="value">${metrics['price']:.1f}</div></div>
        <div class="metric-card"><div class="label">Daily Change</div><div class="value">{metrics['daily_change']:.1f}%</div></div>
        <div class="metric-card"><div class="label">Weekly Change</div><div class="value">{metrics['weekly_change']:.1f}%</div></div>
        <div class="metric-card"><div class="label">YTD Change</div><div class="value">{metrics['ytd_change']:.1f}%</div></div>
        <div class="metric-card"><div class="label">RSI (14-Day)</div><div class="value">{metrics['rsi']:.1f}</div></div>
        <div class="metric-card"><div class="label">VIX</div><div class="value">{vix_val:.1f} ({vix_pct:.1f}%)</div></div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Swingboard - {active_ticker} - {generated_at}</title>
{css}
</head>
<body>
<h1>Financial Intelligence Workspace - {full_company_name}</h1>
<div class="subtitle">Ticker: <b>{active_ticker}</b> &nbsp;|&nbsp; Report generated: {generated_at}</div>

{metrics_html}

<h2>1. Active Ticker Technical Snapshot ({active_ticker})</h2>
{snapshot_html}

<h2>2. Interactive Technical Analysis Trend Plots</h2>
<div class="plotly-wrap">{plot_html}</div>

<h2>3. Full Watchlist Comparative Summary</h2>
{section3_html}
<div class="legend-box">{legend3_html}</div>

<h2>4. NASDAQ 100 - Breakout Screener</h2>
<div class="note">{nasdaq_status_note}</div>
{section4_html}
<div class="legend-box">{legend4_html}</div>

<div class="footer">Generated by Swingboard Multi-Ticker Financial Dashboard. Data source: Yahoo Finance via yfinance. For informational purposes only - not investment advice.</div>
</body>
</html>
"""
    return html


SECTION_LEGEND_HTML = """
🟢 <span style='color:#10ac84'>Price &ge; LTP</span> &nbsp;|&nbsp; 🔴 <span style='color:#ff6b6b'>Price &lt; LTP</span><br>
🟢 <span style='color:#155724'>Positive % Change</span> &nbsp;|&nbsp; 🔴 <span style='color:#721c24'>Negative % Change</span><br>
🔴 <span style='color:#dc3545'>RSI &gt; 70 or &lt; 30</span> &nbsp;|&nbsp; 🟢 <span style='color:#28a745'>RSI Normal (30-70)</span><br>
🟢 <span style='color:#10ac84'>Last Wk Vol &gt; Avg</span> &nbsp;|&nbsp; 🔴 <span style='color:#ff6b6b'>Last Wk Vol &le; Avg</span><br>
🟣 <span style='color:#6c5ce7'>VWAP</span> &nbsp;|&nbsp; 🟠 <span style='color:#e17055'>ATR</span><br>
<i>SMA/Support/Resistance shades: Darker = farther from current price</i><br>
🔴 Beta &gt; 1.2 (High Volatility) | 🟡 Beta 0.8-1.2 (Moderate) | 🟢 Beta &lt; 0.8 (Low Volatility)<br>
🟢 Mean Target &gt; Price (Upside) | 🔴 Mean Target &lt; Price (Downside) | 🟡 Mean Target = Price
"""

# NASDAQ 100 tickers (top holdings)
NASDAQ_100_TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "NVDA", "AVGO", "PEP",
    "COST", "CSCO", "ADBE", "NFLX", "TXN", "QCOM", "TMUS", "INTC", "AMD", "INTU",
    "HON", "AMAT", "SBUX", "BKNG", "ADP", "MDLZ", "GILD", "LRCX", "MU", "ISRG",
    "VRTX", "REGN", "PANW", "SNPS", "KLAC", "ABNB", "FTNT", "CDNS", "MELI", "CTAS",
    "NXPI", "PYPL", "MAR", "ASML", "CSX", "ORLY", "MNST", "MRVL", "ROP", "DXCM",
    "AEP", "KDP", "TEAM", "MCHP", "ADSK", "LULU", "PAYX", "KHC", "MRNA", "EXC",
    "XEL", "PCAR", "ODFL", "CTSH", "CEG", "TTD", "FAST", "WBD", "CSGP", "VRSK",
    "ANSS", "EA", "FANG", "ODFL", "CPRT", "SWKS", "DLTR", "BIDU", "SIRI", "EBAY"
]

# --- UI Sidebar Layout Configurations ---
st.sidebar.header("📁 Ticker List Settings")

# Load default tickers: prefer watchlist2.csv if found, else fallback
DEFAULT_FALLBACK = ["AAPL", "MSFT", "NVDA", "AMD", "SPY"]
WATCHLIST2_PATH = "watchlist2.csv"

default_tickers = DEFAULT_FALLBACK.copy()
watchlist2_loaded = False

if os.path.exists(WATCHLIST2_PATH):
    try:
        df_wl2 = pd.read_csv(WATCHLIST2_PATH).dropna(how='all')
        if not df_wl2.empty:
            parsed = df_wl2.iloc[:, 0].astype(str).str.strip().str.upper().tolist()
            parsed = [t for t in parsed if t and t != 'NAN' and t != '']
            if parsed:
                default_tickers = parsed
                watchlist2_loaded = True
                st.sidebar.success(f"✅ Loaded default watchlist from **watchlist2.csv** ({len(default_tickers)} tickers)")
    except Exception as e:
        st.sidebar.warning(f"⚠️ watchlist2.csv found but could not be read: {e}")
        st.sidebar.info("Falling back to built-in default tickers.")
else:
    st.sidebar.info("ℹ️ No watchlist2.csv found. Using built-in default tickers.")

ticker_list = default_tickers.copy()

uploaded_file = st.sidebar.file_uploader("Upload Tickers List CSV", type=["csv"])
if uploaded_file is not None:
    try:
        df_uploaded = pd.read_csv(uploaded_file).dropna(how='all')
        if not df_uploaded.empty:
            parsed_tickers = df_uploaded.iloc[:, 0].astype(str).str.strip().str.upper().tolist()
            parsed_tickers = [t for t in parsed_tickers if t and t != 'NAN' and t != '']
            if parsed_tickers:
                ticker_list = parsed_tickers
                st.sidebar.success(f"Loaded {len(ticker_list)} custom tickers!")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

selected_ticker = st.sidebar.selectbox("Select Asset Ticker to Analyse:", options=ticker_list)
manual_add = st.sidebar.text_input("Or query a ticker manually:").strip().upper()
active_ticker = manual_add if manual_add else selected_ticker

vix_val, vix_pct = get_vix_data()
st.sidebar.markdown("---")
st.sidebar.header("⚠️ Global Market VIX Status")
st.sidebar.metric(label="Volatility Index (VIX)", value=f"{vix_val:.1f}", delta=f"{vix_pct:.1f}%")

# --- Main App Presentation Screen ---
full_company_name = get_company_full_name(active_ticker)

if active_ticker:
    df, metrics = get_ticker_dashboard(active_ticker)

    if df is not None:
        st.title(f"📊 Financial Intelligence Workspace — {full_company_name}")
        st.caption("⬇️ A full HTML export (all sections + scrollable tables) is available at the bottom of this page once everything has loaded.")

        # Top Card Metrics Row Elements
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Current Price", f"${metrics['price']:.1f}", f"Daily: {metrics['daily_change']:.1f}%")
        m_col2.metric("Weekly Trend", f"{metrics['weekly_change']:.1f}%")
        m_col3.metric("YTD Performance", f"{metrics['ytd_change']:.1f}%")

        rsi_val = metrics['rsi']
        rsi_status = "Normal"
        if rsi_val >= 70: rsi_status = "Overbought"
        elif rsi_val <= 30: rsi_status = "Oversold"
        m_col4.metric("RSI (14-Day)", f"{rsi_val:.1f}", f"Status: {rsi_status}")

        st.markdown("---")

        # SEQUENCE 1: Snapshot table view block layout
        st.subheader(f"📋 1. Active Ticker Technical Snapshot ({active_ticker})")

        snapshot_df = pd.DataFrame({
            "Metric Category": [
                "Moving Averages", "Moving Averages", "Moving Averages",
                "Levels & Volatility", "Levels & Volatility", "Levels & Volatility", "Levels & Volatility", "Levels & Volatility", "Levels & Volatility",
                "Volume Metrics", "Volume Metrics", "Volume Metrics"
            ],
            "Technical Indicator Name": [
                "20-Day Simple Moving Average (SMA)", "50-Day Simple Moving Average (SMA)", "200-Day Simple Moving Average (SMA)",
                "Support Level (20-Day Local Low)", "Resistance Level (20-Day Local High)", "Average True Range (14-Day ATR)", "Volume Weighted Average Price (VWAP)", "Beta", "Mean Price Target",
                "Last Weekly Volume", "Avg Weekly Volume (12W)", "Volume Spike Analysis"
            ],
            "Calculated Value": [
                f"${metrics['sma_20']:.1f}", f"${metrics['sma_50']:.1f}", f"${metrics['sma_200']:.1f}",
                f"${metrics['support']:.1f}", f"${metrics['resistance']:.1f}", f"${metrics['atr']:.1f}", f"${metrics['vwap']:.1f}",
                f"{metrics['beta']:.1f}" if metrics['beta'] is not None else "N/A",
                f"${metrics['mean_target']:.1f}" if metrics['mean_target'] is not None else "N/A",
                f"{metrics['last_weekly_volume']:,}", f"{metrics['avg_weekly_volume']:,}",
                "🚨 Breakout Triggered!" if metrics['vol_breakout'] else "🟢 Standard Volume Ranges"
            ]
        })

        def style_category(val):
            if val == "Moving Averages": return 'color: #ff9f43; font-weight: bold;'
            elif val == "Levels & Volatility": return 'color: #54a0ff; font-weight: bold;'
            elif val == "Volume Metrics": return 'color: #10ac84; font-weight: bold;'
            return ''

        styled_snapshot = snapshot_df.style.map(style_category, subset=['Metric Category'])
        st.dataframe(styled_snapshot, use_container_width=True, hide_index=True)
        snapshot_export_html = styler_to_scrollable_html(styled_snapshot, max_height="360px")

        st.markdown("---")

        # SEQUENCE 2: Technical Chart Plotly workspace layout
        st.subheader("📈 2. Interactive Technical Analysis Trend Plots")

        plot_dates = df.index.strftime('%Y-%m-%d').tolist()

        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.06, 
            row_heights=[0.5, 0.23, 0.27],
            subplot_titles=("Price Action & Moving Averages", "Volume Profile", "MACD & RSI Momentum")
        )

        # Row 1: Price + Candlestick + MAs + Support/Resistance
        fig.add_trace(go.Candlestick(
            x=plot_dates, 
            open=df['Open'], 
            high=df['High'], 
            low=df['Low'], 
            close=df['Close'], 
            name="Price Candle",
            increasing_line_color='#10ac84',
            decreasing_line_color='#ff6b6b'
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=plot_dates, y=df['SMA_20'], name="20 SMA", line=dict(color='orange', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_dates, y=df['SMA_50'], name="50 SMA", line=dict(color='blue', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_dates, y=df['SMA_200'], name="200 SMA", line=dict(color='red', width=1.5, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_dates, y=df['VWAP'], name="VWAP", line=dict(color='purple', width=1.5, dash='dot')), row=1, col=1)

        # Support & Resistance as horizontal reference bands
        fig.add_trace(go.Scatter(
            x=plot_dates, y=df['Support'], 
            name="Support", line=dict(color='green', width=1, dash='dash'), 
            opacity=0.5, showlegend=True
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=plot_dates, y=df['Resistance'], 
            name="Resistance", line=dict(color='red', width=1, dash='dash'), 
            opacity=0.5, showlegend=True
        ), row=1, col=1)

        # Row 2: Volume + Volume SMA
        colors = ['#10ac84' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ff6b6b' for i in range(len(df))]
        fig.add_trace(go.Bar(
            x=plot_dates, y=df['Volume'], name="Volume", 
            marker_color=colors, opacity=0.7
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=plot_dates, y=df['Vol_SMA20'], name="Vol SMA 20", 
            line=dict(color='white', width=1.5)
        ), row=2, col=1)

        # Row 3: MACD (top of row 3) + RSI (bottom of row 3)
        # We use a secondary y-axis for RSI within row 3
        fig.add_trace(go.Scatter(x=plot_dates, y=df['MACD_Line'], name="MACD Line", line=dict(color='blue', width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=plot_dates, y=df['Signal_Line'], name="Signal Line", line=dict(color='orange', width=1.5)), row=3, col=1)
        fig.add_trace(go.Bar(x=plot_dates, y=df['MACD_Line'] - df['Signal_Line'], name="MACD Histogram", marker_color='gray', opacity=0.5), row=3, col=1)

        # RSI on secondary y-axis for row 3
        fig.add_trace(go.Scatter(
            x=plot_dates, y=df['RSI'], name="RSI (14)", 
            line=dict(color='magenta', width=1.5),
            yaxis='y4'
        ))

        # Layout configuration
        fig.update_layout(
            title=f"{active_ticker} — Full Technical Chart",
            xaxis_rangeslider_visible=False,
            height=900,
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified',
            yaxis4=dict(
                title="RSI",
                overlaying='y3',
                side='right',
                range=[0, 100],
                showgrid=False
            )
        )

        # Add RSI reference lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)

        st.plotly_chart(fig, use_container_width=True)
        plot_export_html = fig.to_html(full_html=False, include_plotlyjs='cdn', default_height="900px")

        st.markdown("---")

        # SEQUENCE 3: Watchlist Summary Table
        st.subheader("📋 3. Full Watchlist Comparative Summary")

        summary_df = generate_watchlist_summary(ticker_list)
        section3_export_html = "<p>No watchlist data available for summary generation.</p>"
        if not summary_df.empty:
            # Fetch LTP for all tickers in summary
            ltp_map = {}
            for t in summary_df['Ticker'].tolist():
                try:
                    stock = yf.Ticker(t)
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        ltp_map[t] = float(hist['Close'].iloc[-1])
                except:
                    ltp_map[t] = None

            def format_volume_millions(val):
                """Format volume in millions (e.g. 1.4 M)"""
                if pd.isna(val) or val == 0:
                    return "0.0 M"
                return f"{val / 1_000_000:.1f} M"

            def get_price_shade_color(value, price, max_diff):
                """
                Return a color shade based on how far the value is from price.
                Higher difference = darker shade.
                """
                if pd.isna(value) or pd.isna(price) or price == 0:
                    return 'color: #888888;'
                diff = abs(value - price)
                # Normalize diff against max_diff to get intensity 0-1
                if max_diff <= 0:
                    intensity = 0
                else:
                    intensity = min(diff / max_diff, 1.0)

                # Interpolate between light gray and dark black/charcoal
                # Start: #888888 (light gray), End: #1a1a1a (very dark)
                r = int(136 - intensity * (136 - 26))  # 136 -> 26
                g = int(136 - intensity * (136 - 26))
                b = int(136 - intensity * (136 - 26))

                return f'color: rgb({r},{g},{b}); font-weight: bold;'

            def apply_section3_styling(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)

                # Compute max differences for SMA/Support/Resistance columns for shade scaling
                price_col = df['Price ($)']

                # SMA columns shade
                sma_cols = ['20 SMA ($)', '50 SMA ($)', '200 SMA ($)']
                for col in sma_cols:
                    max_diff = (df[col] - price_col).abs().max()
                    for idx in df.index:
                        styles.loc[idx, col] = get_price_shade_color(df.loc[idx, col], df.loc[idx, 'Price ($)'], max_diff)

                # Support & Resistance shade
                sr_cols = ['Support ($)', 'Resistance ($)']
                for col in sr_cols:
                    max_diff = (df[col] - price_col).abs().max()
                    for idx in df.index:
                        styles.loc[idx, col] = get_price_shade_color(df.loc[idx, col], df.loc[idx, 'Price ($)'], max_diff)

                for idx in df.index:
                    ticker = df.loc[idx, 'Ticker']
                    ltp = ltp_map.get(ticker)

                    if ltp is not None:
                        price = df.loc[idx, 'Price ($)']
                        # Color Price row based on LTP comparison
                        if price < ltp:
                            styles.loc[idx, 'Price ($)'] = 'color: #ff6b6b; font-weight: bold;'
                        else:
                            styles.loc[idx, 'Price ($)'] = 'color: #10ac84; font-weight: bold;'

                    # Light background for % columns
                    for col in ['Daily Chg (%)', 'Weekly Chg (%)', 'YTD Chg (%)']:
                        val = df.loc[idx, col]
                        if val > 0:
                            styles.loc[idx, col] = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                        elif val < 0:
                            styles.loc[idx, col] = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
                        else:
                            styles.loc[idx, col] = 'background-color: #fff3cd; color: #856404; font-weight: 600;'

                    # RSI coloring: Red when above 70 or below 30
                    rsi_val = df.loc[idx, 'RSI (14)']
                    if rsi_val > 70 or rsi_val < 30:
                        styles.loc[idx, 'RSI (14)'] = 'color: #dc3545; font-weight: bold;'
                    else:
                        styles.loc[idx, 'RSI (14)'] = 'color: #28a745;'

                    # Volume columns: Green if Last Wk Vol > Avg Wk Vol
                    last_vol = df.loc[idx, 'Last Wk Vol']
                    avg_vol = df.loc[idx, 'Avg Wk Vol']
                    if last_vol > avg_vol:
                        styles.loc[idx, 'Last Wk Vol'] = 'color: #10ac84; font-weight: bold;'
                    else:
                        styles.loc[idx, 'Last Wk Vol'] = 'color: #ff6b6b;'

                    styles.loc[idx, 'Avg Wk Vol'] = 'color: #54a0ff;'

                    # Bold text for VWAP and ATR
                    styles.loc[idx, 'VWAP ($)'] = 'font-weight: bold; color: #6c5ce7;'
                    styles.loc[idx, 'ATR ($)'] = 'font-weight: bold; color: #e17055;'

                    # Beta styling
                    beta_val = df.loc[idx, 'Beta']
                    if isinstance(beta_val, (int, float)):
                        if beta_val > 1.2:
                            styles.loc[idx, 'Beta'] = 'color: #dc3545; font-weight: bold;'
                        elif beta_val < 0.8:
                            styles.loc[idx, 'Beta'] = 'color: #10ac84; font-weight: bold;'
                        else:
                            styles.loc[idx, 'Beta'] = 'color: #fdcb6e; font-weight: bold;'
                    else:
                        styles.loc[idx, 'Beta'] = 'color: #888888;'

                    # Mean Target styling: Green if target > price, Red if target < price
                    target_val = df.loc[idx, 'Mean Target ($)']
                    if isinstance(target_val, (int, float)):
                        price = df.loc[idx, 'Price ($)']
                        if target_val > price:
                            styles.loc[idx, 'Mean Target ($)'] = 'color: #10ac84; font-weight: bold;'
                        elif target_val < price:
                            styles.loc[idx, 'Mean Target ($)'] = 'color: #ff6b6b; font-weight: bold;'
                        else:
                            styles.loc[idx, 'Mean Target ($)'] = 'color: #fdcb6e; font-weight: bold;'
                    else:
                        styles.loc[idx, 'Mean Target ($)'] = 'color: #888888;'

                    # Breakout styling
                    if df.loc[idx, 'Vol Breakout'] == "🚨 YES":
                        styles.loc[idx, 'Vol Breakout'] = 'background-color: #ff6b6b; color: white; font-weight: bold;'

                return styles

            # Format volume columns to millions for display
            display_df = summary_df.copy()
            display_df['Last Wk Vol'] = display_df['Last Wk Vol'].apply(format_volume_millions)
            display_df['Avg Wk Vol'] = display_df['Avg Wk Vol'].apply(format_volume_millions)

            styled_summary = display_df.style.apply(apply_section3_styling, axis=None)
            st.dataframe(styled_summary, use_container_width=True, hide_index=True)
            section3_export_html = styler_to_scrollable_html(styled_summary, max_height="480px")
        else:
            st.warning("No watchlist data available for summary generation.")

        # --- Color Legend for Section 3 ---
        st.markdown("---")
        st.markdown("**📊 Color Legend:**")
        price_legend_col1, pct_legend_col2, rsi_legend_col3, vol_legend_col4, vwap_atr_legend_col5 = st.columns(5)
        with price_legend_col1:
            st.markdown("🟢 <span style='color:#10ac84'>**Price ≥ LTP**</span>", unsafe_allow_html=True)
            st.markdown("🔴 <span style='color:#ff6b6b'>**Price < LTP**</span>", unsafe_allow_html=True)
        with pct_legend_col2:
            st.markdown("🟢 <span style='color:#155724'>**Positive % Change**</span>", unsafe_allow_html=True)
            st.markdown("🔴 <span style='color:#721c24'>**Negative % Change**</span>", unsafe_allow_html=True)
        with rsi_legend_col3:
            st.markdown("🔴 <span style='color:#dc3545'>**RSI > 70 or < 30**</span>", unsafe_allow_html=True)
            st.markdown("🟢 <span style='color:#28a745'>**RSI Normal (30-70)**</span>", unsafe_allow_html=True)
        with vol_legend_col4:
            st.markdown("🟢 <span style='color:#10ac84'>**Last Wk Vol > Avg**</span>", unsafe_allow_html=True)
            st.markdown("🔴 <span style='color:#ff6b6b'>**Last Wk Vol ≤ Avg**</span>", unsafe_allow_html=True)
        with vwap_atr_legend_col5:
            st.markdown("🟣 <span style='color:#6c5ce7'>**VWAP**</span>", unsafe_allow_html=True)
            st.markdown("🟠 <span style='color:#e17055'>**ATR**</span>", unsafe_allow_html=True)
        st.markdown("*SMA/Support/Resistance shades: Darker = farther from current price*")
        st.markdown("🔴 **Beta > 1.2 (High Volatility)** | 🟡 **Beta 0.8–1.2 (Moderate)** | 🟢 **Beta < 0.8 (Low Volatility)**")
        st.markdown("🟢 **Mean Target > Price (Upside)** | 🔴 **Mean Target < Price (Downside)** | 🟡 **Mean Target = Price**")

        st.markdown("---")

        # SEQUENCE 4: NASDAQ 100 Breakout Screener
        st.subheader("📋 4. NASDAQ 100 — Breakout Screener")

        # CSV upload for NASDAQ tickers
        nasdaq_csv = st.file_uploader("📁 Upload NASDAQ Stocks CSV (optional)", type=["csv"], key="nasdaq_csv_upload")

        nasdaq_tickers = NASDAQ_100_TICKERS.copy()
        if nasdaq_csv is not None:
            try:
                df_nasdaq_upload = pd.read_csv(nasdaq_csv).dropna(how='all')
                if not df_nasdaq_upload.empty:
                    parsed_nasdaq = df_nasdaq_upload.iloc[:, 0].astype(str).str.strip().str.upper().tolist()
                    parsed_nasdaq = [t for t in parsed_nasdaq if t and t != 'NAN' and t != '']
                    if parsed_nasdaq:
                        nasdaq_tickers = parsed_nasdaq
                        st.success(f"Loaded {len(nasdaq_tickers)} tickers from uploaded NASDAQ CSV!")
            except Exception as e:
                st.error(f"Error reading NASDAQ CSV: {e}")

        # Show Analysis button with session state persistence
        if 'show_nasdaq_analysis' not in st.session_state:
            st.session_state.show_nasdaq_analysis = False

        def toggle_nasdaq_analysis():
            st.session_state.show_nasdaq_analysis = True

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            st.button("▶️ Show Analysis", on_click=toggle_nasdaq_analysis, type="primary", use_container_width=True)
        with col_btn2:
            if st.session_state.show_nasdaq_analysis:
                st.button("🔄 Refresh", on_click=toggle_nasdaq_analysis, type="secondary")

        section4_export_html = "<p>NASDAQ breakout screener has not been generated yet — click \u201cShow Analysis\u201d in the app before exporting to include this table.</p>"
        nasdaq_status_note = "\u26A0\uFE0F NASDAQ analysis was not generated for this export (click \u201cShow Analysis\u201d in the app first)."

        if st.session_state.show_nasdaq_analysis:
            with st.spinner("Fetching NASDAQ data... This may take a moment."):
                nasdaq_df = generate_watchlist_summary(nasdaq_tickers)

            if not nasdaq_df.empty:
                # Sort: Breakout stocks first, then by Price descending
                nasdaq_df['Breakout_Sort'] = nasdaq_df['Vol Breakout'].apply(lambda x: 0 if x == "🚨 YES" else 1)
                nasdaq_df = nasdaq_df.sort_values(by=['Breakout_Sort', 'Price ($)'], ascending=[True, False]).drop(columns=['Breakout_Sort'])
                nasdaq_df = nasdaq_df.reset_index(drop=True)

                # Get LTP (Last Traded Price) for each ticker to compare with VWAP
                nasdaq_ltp_map = {}
                for t in nasdaq_df['Ticker'].tolist():
                    try:
                        stock = yf.Ticker(t)
                        hist = stock.history(period="1d")
                        if not hist.empty:
                            nasdaq_ltp_map[t] = float(hist['Close'].iloc[-1])
                    except:
                        nasdaq_ltp_map[t] = None

                def get_price_shade_color_nasdaq(value, price, max_diff):
                    """
                    Return a color shade based on how far the value is from price.
                    Higher difference = darker shade.
                    """
                    if pd.isna(value) or pd.isna(price) or price == 0:
                        return 'color: #888888;'
                    diff = abs(value - price)
                    if max_diff <= 0:
                        intensity = 0
                    else:
                        intensity = min(diff / max_diff, 1.0)

                    r = int(136 - intensity * (136 - 26))
                    g = int(136 - intensity * (136 - 26))
                    b = int(136 - intensity * (136 - 26))

                    return f'color: rgb({r},{g},{b}); font-weight: bold;'

                def apply_nasdaq_styling(df):
                    styles = pd.DataFrame('', index=df.index, columns=df.columns)

                    price_col = df['Price ($)']

                    # SMA columns shade
                    sma_cols = ['20 SMA ($)', '50 SMA ($)', '200 SMA ($)']
                    for col in sma_cols:
                        max_diff = (df[col] - price_col).abs().max()
                        for idx in df.index:
                            styles.loc[idx, col] = get_price_shade_color_nasdaq(df.loc[idx, col], df.loc[idx, 'Price ($)'], max_diff)

                    # Support & Resistance shade
                    sr_cols = ['Support ($)', 'Resistance ($)']
                    for col in sr_cols:
                        max_diff = (df[col] - price_col).abs().max()
                        for idx in df.index:
                            styles.loc[idx, col] = get_price_shade_color_nasdaq(df.loc[idx, col], df.loc[idx, 'Price ($)'], max_diff)

                    for idx in df.index:
                        ticker = df.loc[idx, 'Ticker']
                        ltp = nasdaq_ltp_map.get(ticker)

                        if ltp is not None:
                            price = df.loc[idx, 'Price ($)']
                            # Color Price row based on LTP comparison
                            if price < ltp:
                                styles.loc[idx, 'Price ($)'] = 'color: #ff6b6b; font-weight: bold;'
                            else:
                                styles.loc[idx, 'Price ($)'] = 'color: #10ac84; font-weight: bold;'

                        # Light background for % columns
                        for col in ['Daily Chg (%)', 'Weekly Chg (%)', 'YTD Chg (%)']:
                            val = df.loc[idx, col]
                            if val > 0:
                                styles.loc[idx, col] = 'background-color: #d4edda; color: #155724; font-weight: 600;'
                            elif val < 0:
                                styles.loc[idx, col] = 'background-color: #f8d7da; color: #721c24; font-weight: 600;'
                            else:
                                styles.loc[idx, col] = 'background-color: #fff3cd; color: #856404; font-weight: 600;'

                        # RSI coloring: Red when above 70 or below 30
                        rsi_val = df.loc[idx, 'RSI (14)']
                        if rsi_val > 70 or rsi_val < 30:
                            styles.loc[idx, 'RSI (14)'] = 'color: #dc3545; font-weight: bold;'
                        else:
                            styles.loc[idx, 'RSI (14)'] = 'color: #28a745;'

                        # Volume columns: Green if Last Wk Vol > Avg Wk Vol
                        last_vol = df.loc[idx, 'Last Wk Vol']
                        avg_vol = df.loc[idx, 'Avg Wk Vol']
                        if last_vol > avg_vol:
                            styles.loc[idx, 'Last Wk Vol'] = 'color: #10ac84; font-weight: bold;'
                        else:
                            styles.loc[idx, 'Last Wk Vol'] = 'color: #ff6b6b;'

                        styles.loc[idx, 'Avg Wk Vol'] = 'color: #54a0ff;'

                        # Bold text for VWAP and ATR
                        styles.loc[idx, 'VWAP ($)'] = 'font-weight: bold; color: #6c5ce7;'
                        styles.loc[idx, 'ATR ($)'] = 'font-weight: bold; color: #e17055;'

                        # Beta styling
                        beta_val = df.loc[idx, 'Beta']
                        if isinstance(beta_val, (int, float)):
                            if beta_val > 1.2:
                                styles.loc[idx, 'Beta'] = 'color: #dc3545; font-weight: bold;'
                            elif beta_val < 0.8:
                                styles.loc[idx, 'Beta'] = 'color: #10ac84; font-weight: bold;'
                            else:
                                styles.loc[idx, 'Beta'] = 'color: #fdcb6e; font-weight: bold;'
                        else:
                            styles.loc[idx, 'Beta'] = 'color: #888888;'

                        # Mean Target styling: Green if target > price, Red if target < price
                        target_val = df.loc[idx, 'Mean Target ($)']
                        if isinstance(target_val, (int, float)):
                            price = df.loc[idx, 'Price ($)']
                            if target_val > price:
                                styles.loc[idx, 'Mean Target ($)'] = 'color: #10ac84; font-weight: bold;'
                            elif target_val < price:
                                styles.loc[idx, 'Mean Target ($)'] = 'color: #ff6b6b; font-weight: bold;'
                            else:
                                styles.loc[idx, 'Mean Target ($)'] = 'color: #fdcb6e; font-weight: bold;'
                        else:
                            styles.loc[idx, 'Mean Target ($)'] = 'color: #888888;'

                        # Breakout styling
                        if df.loc[idx, 'Vol Breakout'] == "🚨 YES":
                            styles.loc[idx, 'Vol Breakout'] = 'background-color: #ff6b6b; color: white; font-weight: bold;'

                    return styles

                # Format volume columns to millions for display
                display_nasdaq_df = nasdaq_df.copy()
                display_nasdaq_df['Last Wk Vol'] = display_nasdaq_df['Last Wk Vol'].apply(format_volume_millions)
                display_nasdaq_df['Avg Wk Vol'] = display_nasdaq_df['Avg Wk Vol'].apply(format_volume_millions)

                styled_nasdaq = display_nasdaq_df.style.apply(apply_nasdaq_styling, axis=None)
                st.dataframe(styled_nasdaq, use_container_width=True, hide_index=True)
                section4_export_html = styler_to_scrollable_html(styled_nasdaq, max_height="480px")
                nasdaq_status_note = f"NASDAQ breakout screener generated for {len(nasdaq_df)} tickers."

                # --- Color Legend for Section 4 ---
                st.markdown("---")
                st.markdown("**📊 Color Legend:**")
                nasdaq_price_legend_col1, nasdaq_pct_legend_col2, nasdaq_rsi_legend_col3, nasdaq_vol_legend_col4, nasdaq_vwap_atr_legend_col5 = st.columns(5)
                with nasdaq_price_legend_col1:
                    st.markdown("🟢 <span style='color:#10ac84'>**Price ≥ LTP**</span>", unsafe_allow_html=True)
                    st.markdown("🔴 <span style='color:#ff6b6b'>**Price < LTP**</span>", unsafe_allow_html=True)
                with nasdaq_pct_legend_col2:
                    st.markdown("🟢 <span style='color:#155724'>**Positive % Change**</span>", unsafe_allow_html=True)
                    st.markdown("🔴 <span style='color:#721c24'>**Negative % Change**</span>", unsafe_allow_html=True)
                with nasdaq_rsi_legend_col3:
                    st.markdown("🔴 <span style='color:#dc3545'>**RSI > 70 or < 30**</span>", unsafe_allow_html=True)
                    st.markdown("🟢 <span style='color:#28a745'>**RSI Normal (30-70)**</span>", unsafe_allow_html=True)
                with nasdaq_vol_legend_col4:
                    st.markdown("🟢 <span style='color:#10ac84'>**Last Wk Vol > Avg**</span>", unsafe_allow_html=True)
                    st.markdown("🔴 <span style='color:#ff6b6b'>**Last Wk Vol ≤ Avg**</span>", unsafe_allow_html=True)
                with nasdaq_vwap_atr_legend_col5:
                    st.markdown("🟣 <span style='color:#6c5ce7'>**VWAP**</span>", unsafe_allow_html=True)
                    st.markdown("🟠 <span style='color:#e17055'>**ATR**</span>", unsafe_allow_html=True)
                st.markdown("*SMA/Support/Resistance shades: Darker = farther from current price*")
                st.markdown("🔴 **Beta > 1.2 (High Volatility)** | 🟡 **Beta 0.8–1.2 (Moderate)** | 🟢 **Beta < 0.8 (Low Volatility)**")
                st.markdown("🟢 **Mean Target > Price (Upside)** | 🔴 **Mean Target < Price (Downside)** | 🟡 **Mean Target = Price**")

                st.caption(f"Showing {len(nasdaq_df)} NASDAQ stocks | 🚨 Breakout stocks listed first | Price colored vs real-time LTP")
            else:
                st.warning("Unable to fetch NASDAQ data. Please check your connection.")
                section4_export_html = "<p>Unable to fetch NASDAQ data at export time. Please check your connection and try again.</p>"
                nasdaq_status_note = "\u26A0\uFE0F NASDAQ data fetch failed for this export."
        else:
            st.info("👆 Click 'Show Analysis' to load the NASDAQ 100 breakout screener data.")

        # --- Full Dashboard HTML Export (Sections 1-4, with scrollable HTML tables) ---
        st.markdown("---")
        st.subheader("📥 Export Full Dashboard")
        st.caption("Generates one self-contained HTML file with every section above — snapshot, interactive chart, "
                    "and the watchlist / NASDAQ tables as real, scrollable HTML tables (not screenshots).")

        full_dashboard_html = generate_full_dashboard_html(
            active_ticker=active_ticker,
            full_company_name=full_company_name,
            metrics=metrics,
            vix_val=vix_val,
            vix_pct=vix_pct,
            snapshot_html=snapshot_export_html,
            plot_html=plot_export_html,
            section3_html=section3_export_html,
            legend3_html=SECTION_LEGEND_HTML,
            section4_html=section4_export_html,
            legend4_html=SECTION_LEGEND_HTML,
            nasdaq_status_note=nasdaq_status_note,
        )

        st.download_button(
            label="⬇️ Download Dashboard (HTML)",
            data=full_dashboard_html,
            file_name=f"Swingboard_{active_ticker}_{pd.Timestamp.now().strftime('%Y-%m-%d')}.html",
            mime="text/html",
            use_container_width=True,
        )

    else:
        st.title(f"📊 Financial Intelligence Workspace — {full_company_name}")
        st.error(f"❌ Unable to fetch sufficient data for **{active_ticker}**. Please verify the ticker symbol.")
else:
    st.title(f"📊 Financial Intelligence Workspace — {full_company_name}")
    st.info("👈 Please select or enter a ticker symbol from the sidebar to begin analysis.")