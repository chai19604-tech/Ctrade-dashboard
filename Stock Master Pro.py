import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Stock Master Pro", layout="wide", page_icon="📈")

# --- 2. Sidebar ---
st.sidebar.header("⚙️ ตั้งค่าการวิเคราะห์")
symbol = st.sidebar.text_input("ชื่อหุ้น (Symbol)", value="NVDA").upper()
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1wk", "1mo"])
period = st.sidebar.selectbox("ย้อนหลัง (Period)", ["1y", "2y", "5y", "max"])
run_button = st.sidebar.button("🚀 วิเคราะห์กราฟ")

# --- 3. ฟังก์ชันโหลดข้อมูล (เปลี่ยนมาใช้ .history เพื่อตารางที่สะอาด) ---
@st.cache_data
def load_data(symbol, period, interval):
    try:
        # ใช้ Ticker.history แทน download เพื่อแก้ปัญหา MultiIndex ถาวร
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        
        # ถ้าไม่มีข้อมูล ให้ return None
        if data.empty:
            return None
            
        # ล้าง Timezone ออกจากวันที่ (แก้ปัญหา Index มั่ว)
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
            
        return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# --- 4. ส่วนแสดงผลหลัก ---
st.title(f"📈 {symbol} Analysis Dashboard")

if run_button:
    with st.spinner(f'กำลังดึงข้อมูล {symbol} ...'):
        df = load_data(symbol, period, timeframe)
        
    if df is None:
        st.error("❌ ไม่พบข้อมูลหุ้นตัวนี้ หรือชื่อหุ้นผิด")
    else:
        # ตรวจสอบว่ามีข้อมูลเพียงพอสำหรับคำนวณ Indicator หรือไม่ (ต้อง > 30 แถว)
        if len(df) < 30:
            st.warning("⚠️ ข้อมูลหุ้นมีน้อยเกินไปสำหรับการคำนวณ Indicator")
        else:
            try:
                # --- คำนวณ Indicators ---
                # สร้าง DataFrame สำรองเพื่อคำนวณก่อน (ป้องกัน Error การเขียนทับ)
                # pandas_ta ต้องการชื่อคอลัมน์เป็น Open, High, Low, Close (ตัวใหญ่) ซึ่ง .history() ให้มาถูกแล้ว
                
                df['EMA_12'] = df.ta.ema(length=12)
                df['EMA_26'] = df.ta.ema(length=26)
                df['RSI'] = df.ta.rsi(length=14)
                df['OBV'] = df.ta.obv()
                df['AOBV'] = df['OBV'].rolling(window=30).mean()
                
                # ลบแถวที่เป็น NaN (ช่วงต้นกราฟที่คำนวณไม่ได้) ออกเพื่อให้กราฟสวย
                df.dropna(inplace=True)

                # --- สร้างกราฟ Plotly ---
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.05, 
                                    row_heights=[0.6, 0.2, 0.2],
                                    subplot_titles=(f"Price & EMA Trend ({symbol})", "RSI Momentum", "Volume Flow (OBV)"))

                # 1. Price
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                             low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], line=dict(color='#00ff00', width=1), name='EMA 12'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], line=dict(color='#ff0000', width=1), name='EMA 26'), row=1, col=1)

                # 2. RSI
                fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#aa00ff', width=2), name='RSI'), row=2, col=1)
                fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

                # 3. OBV
                fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], line=dict(color='cyan', width=1), name='OBV'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['AOBV'], line=dict(color='orange', width=1, dash='dash'), name='AOBV (30)'), row=3, col=1)

                fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

                # --- สรุปผล ---
                st.subheader("📊 ผลการวิเคราะห์")
                col1, col2, col3 = st.columns(3)
                
                last = df.iloc[-1]
                
                # Logic แสดงผล
                trend = "UP 🐂" if last['EMA_12'] > last['EMA_26'] else "DOWN 🐻"
                col1.metric("Trend", trend, delta_color="normal")
                
                rsi_state = "Overbought ⚠️" if last['RSI'] > 70 else ("Oversold ✅" if last['RSI'] < 30 else "Neutral")
                col2.metric("RSI", f"{last['RSI']:.2f}", rsi_state)
                
                vol_state = "Strong 💪" if last['OBV'] > last['AOBV'] else "Weak 💤"
                col3.metric("Volume", vol_state)
                
                st.markdown("---")
                # Final Call
                if (last['EMA_12'] > last['EMA_26']) and (last['OBV'] > last['AOBV']) and (last['RSI'] < 70):
                    st.success("✅ คำแนะนำ: **BUY (ซื้อ)**")
                elif (last['EMA_12'] < last['EMA_26']):
                    st.error("❌ คำแนะนำ: **SELL (ขาย/เลี่ยง)**")
                else:
                    st.warning("⏸ คำแนะนำ: **WAIT (รอ)**")

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")
                st.write("ลองเปลี่ยน Timeframe หรือชื่อหุ้นดูนะครับ")

else:
    st.info("👈 กดปุ่มเพื่อเริ่มวิเคราะห์")
