import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าเว็บ (Page Config) ---
st.set_page_config(page_title="Stock Master Pro", layout="wide", page_icon="📈")

# --- 2. Sidebar สำหรับตั้งค่า ---
st.sidebar.header("⚙️ ตั้งค่าการวิเคราะห์")
symbol = st.sidebar.text_input("ชื่อหุ้น (Symbol)", value="NVDA").upper()
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1wk", "1mo"])
period = st.sidebar.selectbox("ย้อนหลัง (Period)", ["1y", "2y", "5y", "max"])

# ปุ่มกดเพื่อเริ่มวิเคราะห์
run_button = st.sidebar.button("🚀 วิเคราะห์กราฟ")

# --- 3. ฟังก์ชันโหลดข้อมูล (Caching เพื่อความเร็ว) ---
@st.cache_data
def load_data(symbol, period, interval):
    try:
        data = yf.download(symbol, period=period, interval=interval)
        return data
    except Exception as e:
        return None

# --- 4. ส่วนแสดงผลหลัก ---
st.title(f"📈 {symbol} Analysis Dashboard")

if run_button:
    with st.spinner('กำลังดึงข้อมูลจากตลาดโลก...'):
        df = load_data(symbol, period, timeframe)
        
    if df is None or df.empty:
        st.error("❌ ไม่พบข้อมูลหุ้นตัวนี้ หรือชื่อหุ้นผิด")
    else:
        # --- คำนวณ Indicators ---
        df['EMA_12'] = df.ta.ema(length=12)
        df['EMA_26'] = df.ta.ema(length=26)
        df['RSI'] = df.ta.rsi(length=14)
        df['OBV'] = df.ta.obv()
        df['AOBV'] = df['OBV'].rolling(window=30).mean()
        
        # --- สร้างกราฟสวยๆ ด้วย Plotly (Interactive) ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            row_heights=[0.6, 0.2, 0.2],
                            subplot_titles=(f"Price & EMA Trend ({symbol})", "RSI Momentum", "Volume Flow (OBV)"))

        # ส่วนที่ 1: Candlestick & EMA
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                     low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], line=dict(color='green', width=1), name='EMA 12'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], line=dict(color='red', width=1), name='EMA 26'), row=1, col=1)

        # ส่วนที่ 2: RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=2), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

        # ส่วนที่ 3: OBV
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], line=dict(color='blue', width=1), name='OBV'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['AOBV'], line=dict(color='orange', width=1, dash='dash'), name='AOBV (30)'), row=3, col=1)

        # ปรับแต่งกราฟให้สวยงามบนมือถือ
        fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_dark")
        
        # แสดงกราฟ
        st.plotly_chart(fig, use_container_width=True)

        # --- ส่วนสรุปสัญญาณ (Signal Summary) ---
        st.subheader("📊 ผลการวิเคราะห์ล่าสุด")
        col1, col2, col3 = st.columns(3)
        
        last_row = df.iloc[-1]
        
        # Signal 1: Trend
        trend_status = "BULLISH 🐂" if last_row['EMA_12'] > last_row['EMA_26'] else "BEARISH 🐻"
        col1.metric("Trend (EMA)", trend_status, delta_color="normal")
        
        # Signal 2: RSI
        rsi_val = round(last_row['RSI'], 2)
        rsi_status = "Overbought ⚠️" if rsi_val > 70 else ("Oversold ✅" if rsi_val < 30 else "Neutral")
        col2.metric("Momentum (RSI)", f"{rsi_val}", rsi_status)
        
        # Signal 3: OBV
        obv_status = "Strong Volume 💪" if last_row['OBV'] > last_row['AOBV'] else "Weak Volume 💤"
        col3.metric("Volume Flow", obv_status)

        # Final Verdict
        st.markdown("---")
        if (last_row['EMA_12'] > last_row['EMA_26']) and (last_row['OBV'] > last_row['AOBV']) and (last_row['RSI'] < 70):
            st.success("✅ คำแนะนำ: **BUY (ซื้อ)** - ทุกระบบยืนยันแนวโน้มขาขึ้น")
        elif (last_row['EMA_12'] < last_row['EMA_26']):
            st.error("❌ คำแนะนำ: **SELL / WAIT (ขาย/รอ)** - แนวโน้มเป็นขาลง")
        else:
            st.warning("⏸ คำแนะนำ: **WAIT (รอ)** - สัญญาณยังขัดแย้งกัน")

else:
    st.info("👈 กดปุ่ม 'วิเคราะห์กราฟ' ที่แถบด้านซ้ายเพื่อเริ่มต้น")