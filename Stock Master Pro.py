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

# --- 3. ฟังก์ชันโหลดข้อมูล ---
@st.cache_data
def load_data(symbol, period, interval):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty: return None
        if data.index.tz is not None: data.index = data.index.tz_localize(None)
        return data
    except Exception as e:
        return None

# --- 4. ส่วนแสดงผลหลัก ---
st.title(f"📈 {symbol} Analysis Dashboard")

if run_button:
    with st.spinner(f'กำลังวิเคราะห์ {symbol} ...'):
        df = load_data(symbol, period, timeframe)
        
    if df is None:
        st.error("❌ ไม่พบข้อมูลหุ้นตัวนี้")
    elif len(df) < 30:
        st.warning("⚠️ ข้อมูลหุ้นมีน้อยเกินไป")
    else:
        try:
            # --- คำนวณ Indicators ---
            df['EMA_12'] = df.ta.ema(length=12)
            df['EMA_26'] = df.ta.ema(length=26)
            df['RSI'] = df.ta.rsi(length=14)
            df['OBV'] = df.ta.obv()
            df['AOBV'] = df['OBV'].rolling(window=30).mean()
            
            # Bollinger Bands (ใช้ดูแนวรับแนวต้าน)
            bb = df.ta.bbands(length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            # ตั้งชื่อตัวแปรให้เรียกง่ายๆ (ชื่อ column จาก pandas_ta อาจยาว)
            bbl = df.columns[df.columns.str.startswith('BBL')][0]
            bbm = df.columns[df.columns.str.startswith('BBM')][0]
            bbu = df.columns[df.columns.str.startswith('BBU')][0]

            # High เดิม 20 วัน (Resistance)
            df['High_20'] = df['High'].rolling(20).max()

            # ลบค่า NaN
            df.dropna(inplace=True)
            last = df.iloc[-1]

            # --- คำนวณจุดซื้อ/ขาย 3 ระดับ ---
            # จุดซื้อ (Supports)
            buy1 = last['EMA_26']
            buy2 = last[bbm] # เส้นกลาง
            buy3 = last[bbl] # เส้นล่าง (ถูกสุด)

            # จุดขาย (Resistances)
            sell1 = last[bbu] # เส้นบน
            sell2 = last['High_20'] # ยอดเดิม
            sell3 = last['High_20'] * 1.05 # ยอดเดิม + 5% (Breakout)

            # --- สร้างกราฟ ---
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2],
                                subplot_titles=(f"Price Strategy: {symbol}", "RSI", "Volume Flow"))

            # Price & Bands
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                         low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], line=dict(color='#00ff00', width=1), name='EMA 12'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], line=dict(color='#ff0000', width=1), name='EMA 26'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbu], line=dict(color='gray', width=1, dash='dot'), name='Upper Band'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbl], line=dict(color='gray', width=1, dash='dot'), name='Lower Band'), row=1, col=1)

            # RSI & OBV
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#aa00ff', width=2), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], line=dict(color='cyan', width=1), name='OBV'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['AOBV'], line=dict(color='orange', width=1, dash='dash'), name='AOBV'), row=3, col=1)

            fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

            # --- 📊 แสดงผลวิเคราะห์ ---
            st.subheader("🎯 กลยุทธ์การเทรด (Strategy)")
            
            # Logic สัญญาณหลัก
            trend_up = last['EMA_12'] > last['EMA_26']
            vol_up = last['OBV'] > last['AOBV']
            rsi_ok = last['RSI'] < 70

            if trend_up and vol_up and rsi_ok:
                st.success(f"✅ SIGNAL: **BUY (ซื้อ)** - ราคา {last['Close']:.2f}")
                st.caption("เทรนด์ขาขึ้น + วอลุ่มเข้า + ราคายังไม่แพงเกินไป")
            elif not trend_up:
                st.error(f"❌ SIGNAL: **SELL / AVOID (ขาย/เลี่ยง)** - ราคา {last['Close']:.2f}")
                st.caption("เทรนด์เป็นขาลง (EMA 12 < 26) รอให้กลับตัวก่อนค่อยเข้า")
            else:
                st.warning(f"⏸ SIGNAL: **WAIT (รอ)** - ราคา {last['Close']:.2f}")
                st.caption("สัญญาณขัดแย้งกัน (อาจจะพักตัว หรือวอลุ่มหาย)")

            st.markdown("---")

            # --- ตารางเป้าหมายราคา (The Magic Table) ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("### 🛡️ แนวรับ (จุดรอซื้อ)")
                st.info(f"**ไม้ที่ 1:** {buy1:.2f} (EMA 26)")
                st.info(f"**ไม้ที่ 2:** {buy2:.2f} (Middle Band)")
                st.success(f"**ไม้ที่ 3:** {buy3:.2f} (Lower Band - ของถูก)")
            
            with c2:
                st.markdown("### ⚔️ แนวต้าน (เป้าขาย)")
                st.warning(f"**เป้าที่ 1:** {sell1:.2f} (Upper Band)")
                st.warning(f"**เป้าที่ 2:** {sell2:.2f} (High เดิม)")
                st.error(f"**เป้าที่ 3:** {sell3:.2f} (Breakout +5%)")

        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("👈 กดปุ่มเพื่อเริ่มวิเคราะห์")
