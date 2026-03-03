import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Stock Master Pro + Banker", layout="wide", page_icon="🏦")

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

# --- ฟังก์ชันคำนวณ Banker Volume (สูตรจำลอง MCDX) ---
def calculate_banker_volume(df):
    # ใช้ RSI 2 ชุดเพื่อวัดพลังของเทรนด์และเงินทุน
    # สูตรนี้เป็นการ Estimate พฤติกรรมเจ้ามือ (ไม่ใช่ข้อมูล Dark Pool จริง)
    rsi_banker = ta.rsi(df['Close'], length=50) # Banker มองยาว
    rsi_hot = ta.rsi(df['Close'], length=40)    # Hot Money มองกลาง
    
    # คำนวณค่าพลัง (Sensitivity Adjustment)
    df['Banker_Val'] = (rsi_banker - 50) * 1.5 
    df['HotMoney_Val'] = (rsi_hot - 30) * 0.7
    
    # Clean ค่าให้ไม่ติดลบ และไม่เกิน 20 (เพื่อให้กราฟสวยเหมือนต้นฉบับ)
    df['Banker_Val'] = df['Banker_Val'].clip(lower=0, upper=20)
    df['HotMoney_Val'] = df['HotMoney_Val'].clip(lower=0, upper=20)
    
    return df

# --- 4. ส่วนแสดงผลหลัก ---
st.title(f"🏦 {symbol} Smart Money Analysis")

if run_button:
    with st.spinner(f'กำลังแกะรอยรายใหญ่ {symbol} ...'):
        df = load_data(symbol, period, timeframe)
        
    if df is None or len(df) < 60:
        st.error("❌ ข้อมูลไม่เพียงพอสำหรับคำนวณ Banker Volume")
    else:
        try:
            # --- คำนวณ Indicators ---
            df['EMA_12'] = df.ta.ema(length=12)
            df['EMA_26'] = df.ta.ema(length=26)
            df['RSI'] = df.ta.rsi(length=14)
            
            # คำนวณ Banker
            df = calculate_banker_volume(df)
            
            # ลบค่าว่าง
            df.dropna(inplace=True)
            last = df.iloc[-1]

            # --- สร้างกราฟ 3 ช่อง (Price / Banker / RSI) ---
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25],
                                subplot_titles=(f"Price Action: {symbol}", "💰 Banker Volume (MCDX Model)", "Momentum (RSI)"))

            # 1. Price & EMA
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                         low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], line=dict(color='#00ff00', width=1), name='EMA 12'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], line=dict(color='#ff0000', width=1), name='EMA 26'), row=1, col=1)

            # 2. Banker Volume (Bar Chart)
            # สร้างสีตามค่า (แดง=เจ้ามือ, เหลือง=เก็งกำไร, เขียว=รายย่อย)
            colors = []
            for b in df['Banker_Val']:
                if b > 10: colors.append('red')      # เจ้ามือเข้าหนัก
                elif b > 5: colors.append('orange')  # เริ่มเข้า
                else: colors.append('green')         # รายย่อย/ไม่มีเจ้า
            
            fig.add_trace(go.Bar(x=df.index, y=df['Banker_Val'], name='Banker Flow', marker_color=colors), row=2, col=1)
            # ขีดเส้นระดับเจ้ามือครองตลาด (>10)
            fig.add_hline(y=10, line_dash="dot", line_color="white", row=2, col=1, annotation_text="Strong Banker")

            # 3. RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#aa00ff', width=2), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

            fig.update_layout(height=900, xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

            # --- 📊 วิเคราะห์รายใหญ่ (Banker Analysis) ---
            st.subheader("🕵️ เจาะลึกพฤติกรรมรายใหญ่")
            c1, c2, c3 = st.columns(3)
            
            banker_score = last['Banker_Val']
            
            with c1:
                st.metric("RSI Status", f"{last['RSI']:.2f}", "Overbought" if last['RSI']>70 else "Neutral")
            
            with c2:
                # แปลความหมายแท่งแดง
                if banker_score > 15:
                    st.metric("Banker Status", "🚀 VERY STRONG", "เจ้ามือคุมตลาด 100%")
                elif banker_score > 10:
                    st.metric("Banker Status", "🔥 STRONG", "เจ้ามือเริ่มดันราคา")
                elif banker_score > 5:
                    st.metric("Banker Status", "⚠️ WEAK", "รายย่อยยังเยอะอยู่")
                else:
                    st.metric("Banker Status", "❌ NONE", "ไม่มีเจ้ามือ")
            
            with c3:
                # คำแนะนำ
                if banker_score > 10 and last['EMA_12'] > last['EMA_26']:
                    st.success("**ACTION: FOLLOW BUY** (ตามน้ำเจ้ามือ)")
                elif banker_score < 5 and last['EMA_12'] < last['EMA_26']:
                    st.error("**ACTION: AVOID** (อย่าเพิ่งรับมีด)")
                else:
                    st.warning("**ACTION: WAIT** (รอความชัดเจน)")

        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("👈 กดปุ่มเพื่อเริ่มวิเคราะห์")
