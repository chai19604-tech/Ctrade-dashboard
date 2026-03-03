import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import numpy as np

# --- 1. SYSTEM CONFIGURATION (หน้าจระดับสถาบัน) ---
st.set_page_config(page_title="Institutional Trading Terminal", layout="wide", page_icon="🏛️")
# วางโค้ดนี้ต่อจาก st.set_page_config(...)
st.markdown("""
<style>
    /* 1. พื้นหลังหลัก - น้ำเงินเข้มไล่เฉด */
    .stApp {
        background: linear-gradient(180deg, #021B39 0%, #000000 100%);
        color: #ffffff;
    }
    
    /* 2. Sidebar */
    [data-testid="stSidebar"] {
        background-color: #01122aa0; /* โปร่งแสงนิดๆ */
        backdrop-filter: blur(10px);
    }

    /* 3. กล่อง Metric */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05); /* กระจกใส */
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px;
        border-radius: 10px;
    }
    
    /* 4. หัวข้อ */
    h1, h2, h3 {
        color: #4da6ff !important; /* ฟ้าสว่าง */
    }
</style>
""", unsafe_allow_html=True)
# Custom CSS: Dark Mode & Professional Typography
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .stMetric { background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 5px solid #00F0FF; }
    h1, h2, h3, h4 { font-family: 'Roboto', sans-serif; color: #e0e0e0; }
    .stAlert { background-color: #262730; color: #ff4b4b; border: 1px solid #444; }
    div[data-testid="stExpander"] div[role="button"] p { font-size: 1.1rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🏛️ QUANT TERMINAL")
    st.caption("Professional Grade Analytics")
    st.markdown("---")
    
    # Input
    symbol = st.text_input("TICKER", value="NVDA").upper()
    col1, col2 = st.columns(2)
    with col1: timeframe = st.selectbox("TF", ["1d", "1wk", "1mo"])
    with col2: period = st.selectbox("RANGE", ["1y", "2y", "5y", "max"])
    
    st.markdown("### ⚙️ SYSTEM")
    refresh_rate = st.slider("Refresh (Sec)", 10, 300, 30)
    risk_free = st.number_input("Risk-Free Rate (%)", value=4.0)
    
    st.success("● SYSTEM ONLINE")

# Auto-Refresh (จำลอง Real-time Data Feed)
st_autorefresh(interval=refresh_rate * 1000, key="datarefresh")

# --- 3. DATA ENGINE (ROBUST) ---
@st.cache_data(ttl=refresh_rate)
def load_data(symbol, period, interval):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty: return None
        if data.index.tz is not None: data.index = data.index.tz_localize(None)
        return data
    except Exception: return None

# --- 4. LOGIC ENGINE (รวมทุกสูตรที่ท่านขอ) ---
def process_data(df, rf_rate):
    # A. Technical Indicators (Core System)
    df['EMA_12'] = df.ta.ema(length=12)
    df['EMA_26'] = df.ta.ema(length=26)
    df['RSI'] = df.ta.rsi(length=14)
    df['OBV'] = df.ta.obv()
    df['AOBV'] = df['OBV'].rolling(window=30).mean()
    
    # B. Banker Volume (MCDX Logic)
    rsi_banker = ta.rsi(df['Close'], length=50)
    df['Banker_Val'] = ((rsi_banker - 50) * 1.5).clip(0, 20)
    
    # C. Volatility & Risk Metrics (Institutional Grade)
    df['Returns'] = df['Close'].pct_change()
    volatility = df['Returns'].std() * np.sqrt(252) * 100
    sharpe = (df['Returns'].mean() * 252 - (rf_rate/100)) / (df['Returns'].std() * np.sqrt(252))
    
    # Max Drawdown
    roll_max = df['Close'].cummax()
    drawdown = (df['Close'] - roll_max) / roll_max
    max_dd = drawdown.min() * 100
    
    # D. Support / Resistance Levels (S1-S3, R1-R3)
    # Bollinger Bands for Dynamic Levels
    bb = df.ta.bbands(length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    
    return df, volatility, sharpe, max_dd

# --- 5. DASHBOARD UI ---
data = load_data(symbol, period, timeframe)

if data is None:
    st.error("⚠️ DATA FEED ERROR: Invalid Symbol or API issue.")
else:
    # Process
    df, vol, sharpe, mdd = process_data(data, risk_free)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Get Column Names for BB
    bbu = df.columns[df.columns.str.startswith('BBU')][0]
    bbm = df.columns[df.columns.str.startswith('BBM')][0]
    bbl = df.columns[df.columns.str.startswith('BBL')][0]
    high_20 = df['High'].rolling(20).max().iloc[-1]

    # --- TOP ROW: FINANCIAL METRICS ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        delta = last['Close'] - prev['Close']
        st.metric("LATEST PRICE", f"{last['Close']:.2f}", f"{delta:.2f} ({(delta/prev['Close'])*100:.2f}%)")
    with c2: st.metric("SHARPE RATIO", f"{sharpe:.2f}", "Risk Adjusted Return")
    with c3: st.metric("VOLATILITY (Yearly)", f"{vol:.2f}%", "Risk Level")
    with c4: st.metric("MAX DRAWDOWN", f"{mdd:.2f}%", "Worst Case Scenario", delta_color="inverse")

    st.markdown("---")

    # --- MAIN LAYOUT: CHARTS (LEFT) vs STRATEGY (RIGHT) ---
    col_chart, col_strat = st.columns([3, 1.2])

    with col_chart:
        # Create 4-Pane Chart (Price, Banker, RSI, OBV)
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.15, 0.2],
                            subplot_titles=("Price Action & EMA System", "💰 Banker Volume (MCDX)", "Momentum (RSI)", "Volume Flow (OBV)"))

        # 1. Price
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], line=dict(color='#00ff00', width=1), name='EMA 12'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], line=dict(color='#ff0000', width=1), name='EMA 26'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df[bbu], line=dict(color='gray', width=0, dash='dot'), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df[bbl], line=dict(color='gray', width=0, dash='dot'), name='Volatility Band'), row=1, col=1)

        # 2. Banker Volume (MCDX)
        colors = ['#FF0000' if v > 10 else '#FFA500' if v > 5 else '#00FF00' for v in df['Banker_Val']]
        fig.add_trace(go.Bar(x=df.index, y=df['Banker_Val'], marker_color=colors, name='Banker Flow'), row=2, col=1)
        fig.add_hline(y=10, line_dash="dot", line_color="white", row=2, col=1)

        # 3. RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#aa00ff', width=2), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_color="red", line_dash="dot", row=3, col=1)
        fig.add_hline(y=30, line_color="green", line_dash="dot", row=3, col=1)

        # 4. OBV
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], line=dict(color='cyan', width=1), name='OBV'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['AOBV'], line=dict(color='orange', width=1, dash='dash'), name='AOBV'), row=4, col=1)

        fig.update_layout(height=1000, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_strat:
        # --- STRATEGY PANEL (LEVELS & SIGNALS) ---
        st.subheader("🤖 EXECUTION PANEL")
        
        # 1. SIGNAL LOGIC
        score = 0
        if last['EMA_12'] > last['EMA_26']: score += 1
        if last['OBV'] > last['AOBV']: score += 1
        if last['Banker_Val'] > 10: score += 2
        if last['RSI'] < 70: score += 1
        
        if score >= 4:
            st.success("🔥 STRONG BUY")
            st.caption("Condition: Trend + Vol + Banker")
        elif score == 0:
            st.error("🩸 STRONG SELL")
            st.caption("Condition: Downtrend")
        elif last['EMA_12'] < last['EMA_26']:
            st.warning("⚠️ SELL / AVOID")
        else:
            st.info("⏸ HOLD / WAIT")
            
        st.markdown("---")
        
        # 2. KEY LEVELS (S1-S3 / R1-R3) - ตารางราคาที่ท่านขอ
        st.subheader("🎯 KEY LEVELS")
        
        # คำนวณ Levels ตาม Logic ที่คุยกัน
        s1, s2, s3 = last['EMA_26'], last[bbm], last[bbl]
        r1, r2, r3 = last[bbu], high_20, high_20 * 1.05
        
        # แสดงผลแบบ Tabular View
        st.markdown("#### 🛡️ SUPPORTS (BUY ZONES)")
        st.info(f"S1 (EMA26): {s1:.2f}")
        st.info(f"S2 (Mid BB): {s2:.2f}")
        st.success(f"S3 (Low BB): {s3:.2f} ⭐ Best Entry")
        
        st.markdown("#### ⚔️ RESISTANCES (TARGETS)")
        st.warning(f"R1 (Top BB): {r1:.2f}")
        st.warning(f"R2 (High): {r2:.2f}")
        st.error(f"R3 (Breakout): {r3:.2f} 🚀")
        
        st.markdown("---")
        
        # 3. BANKER STATUS
        st.subheader("🏦 SMART MONEY")
        banker_pct = (last['Banker_Val'] / 20) * 100
        st.progress(int(banker_pct), text=f"Banker Strength: {last['Banker_Val']:.1f}/20")
        if last['Banker_Val'] > 10:
            st.markdown("**:red[INSTITUTIONAL CONTROL]**")
        else:
            st.markdown("**:green[RETAIL CONTROL]**")

