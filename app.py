import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Set page to wide layout
st.set_page_config(layout="wide", page_title="Multi-Ticker Financial Dashboard")

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
            "avg_weekly_volume": avg_weekly_volume
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
                    "Price ($)": round(metrics["price"], 2),
                    "Daily Chg (%)": round(metrics["daily_change"], 2),
                    "Weekly Chg (%)": round(metrics["weekly_change"], 2),
                    "YTD Chg (%)": round(metrics["ytd_change"], 2),
                    "RSI (14)": round(metrics["rsi"], 1),
                    "20 SMA ($)": round(metrics["sma_20"], 2),
                    "50 SMA ($)": round(metrics["sma_50"], 2),
                    "200 SMA ($)": round(metrics["sma_200"], 2),
                    "Support ($)": round(metrics["support"], 2),
                    "Resistance ($)": round(metrics["resistance"], 2),
                    "Last Wk Vol": metrics["last_weekly_volume"],
                    "Avg Wk Vol": metrics["avg_weekly_volume"],
                    "VWAP ($)": round(metrics["vwap"], 2),
                    "ATR ($)": round(metrics["atr"], 2),
                    "Vol Breakout": "🚨 YES" if metrics["vol_breakout"] else "🟢 No"
                })
        except Exception:
            pass
    return pd.DataFrame(summary_data)

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
st.sidebar.metric(label="Volatility Index (VIX)", value=f"{vix_val:.2f}", delta=f"{vix_pct:.2f}%")

# --- Main App Presentation Screen ---
full_company_name = get_company_full_name(active_ticker)
st.title(f"📊 Financial Intelligence Workspace — {full_company_name}")

if active_ticker:
    df, metrics = get_ticker_dashboard(active_ticker)

    if df is not None:
        # Top Card Metrics Row Elements
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Current Price", f"${metrics['price']:.2f}", f"Daily: {metrics['daily_change']:.2f}%")
        m_col2.metric("Weekly Trend", f"{metrics['weekly_change']:.2f}%")
        m_col3.metric("YTD Performance", f"{metrics['ytd_change']:.2f}%")

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
                "Levels & Volatility", "Levels & Volatility", "Levels & Volatility", "Levels & Volatility",
                "Volume Metrics", "Volume Metrics", "Volume Metrics"
            ],
            "Technical Indicator Name": [
                "20-Day Simple Moving Average (SMA)", "50-Day Simple Moving Average (SMA)", "200-Day Simple Moving Average (SMA)",
                "Support Level (20-Day Local Low)", "Resistance Level (20-Day Local High)", "Average True Range (14-Day ATR)", "Volume Weighted Average Price (VWAP)",
                "Last Weekly Volume", "Avg Weekly Volume (12W)", "Volume Spike Analysis"
            ],
            "Calculated Value": [
                f"${metrics['sma_20']:.2f}", f"${metrics['sma_50']:.2f}", f"${metrics['sma_200']:.2f}",
                f"${metrics['support']:.2f}", f"${metrics['resistance']:.2f}", f"${metrics['atr']:.2f}", f"${metrics['vwap']:.2f}",
                f"{metrics['last_weekly_volume']:,}", f"{metrics['avg_weekly_volume']:,}",
                "🚨 Breakout Triggered!" if metrics['vol_breakout'] else "🟢 Standard Volume Ranges"
            ]
        })

        def style_category(val):
            if val == "Moving Averages": return 'color: #ff9f43; font-weight: bold;'
            elif val == "Levels & Volatility": return 'color: #54a0ff; font-weight: bold;'
            elif val == "Volume Metrics": return 'color: #10ac84; font-weight: bold;'
            return ''

        st.dataframe(snapshot_df.style.map(style_category, subset=['Metric Category']), use_container_width=True, hide_index=True)

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

        st.markdown("---")

        # SEQUENCE 3: Watchlist Summary Table
        st.subheader("📋 3. Full Watchlist Comparative Summary")

        summary_df = generate_watchlist_summary(ticker_list)
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

            def apply_section3_styling(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)

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

                    # Bold text for VWAP and ATR
                    styles.loc[idx, 'VWAP ($)'] = 'font-weight: bold; color: #6c5ce7;'
                    styles.loc[idx, 'ATR ($)'] = 'font-weight: bold; color: #e17055;'

                    # Breakout styling
                    if df.loc[idx, 'Vol Breakout'] == "🚨 YES":
                        styles.loc[idx, 'Vol Breakout'] = 'background-color: #ff6b6b; color: white; font-weight: bold;'

                return styles

            styled_summary = summary_df.style.apply(apply_section3_styling, axis=None)
            st.dataframe(styled_summary, use_container_width=True, hide_index=True)
        else:
            st.warning("No watchlist data available for summary generation.")

        st.markdown("---")

        # SEQUENCE 4: NASDAQ 100 Breakout Screener
        st.subheader("📋 4. NASDAQ 100 — Breakout Screener (Ordered by Status)")

        with st.spinner("Fetching NASDAQ 100 data... This may take a moment."):
            nasdaq_df = generate_watchlist_summary(NASDAQ_100_TICKERS)

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

            def apply_nasdaq_styling(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)

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

                    # Bold text for VWAP and ATR
                    styles.loc[idx, 'VWAP ($)'] = 'font-weight: bold; color: #6c5ce7;'
                    styles.loc[idx, 'ATR ($)'] = 'font-weight: bold; color: #e17055;'

                    # Breakout styling
                    if df.loc[idx, 'Vol Breakout'] == "🚨 YES":
                        styles.loc[idx, 'Vol Breakout'] = 'background-color: #ff6b6b; color: white; font-weight: bold;'

                return styles

            styled_nasdaq = nasdaq_df.style.apply(apply_nasdaq_styling, axis=None)
            st.dataframe(styled_nasdaq, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(nasdaq_df)} NASDAQ 100 stocks | 🚨 Breakout stocks listed first | Price colored vs real-time LTP")
        else:
            st.warning("Unable to fetch NASDAQ 100 data. Please check your connection.")

    else:
        st.error(f"❌ Unable to fetch sufficient data for **{active_ticker}**. Please verify the ticker symbol.")
else:
    st.info("👈 Please select or enter a ticker symbol from the sidebar to begin analysis.")
