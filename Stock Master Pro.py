import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Stock Master Pro: Ultimate", layout="wide", page_icon="💎")

# --- 2. Sidebar ---
st.sidebar.header("⚙️ ตั้งค่าการวิเคราะห์")
symbol = st.sidebar.text_input("ชื่อหุ้น (Symbol)", value="NVDA").upper()
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1wk", "1mo"])
period = st.sidebar.selectbox("ย้อนหลัง (Period)", ["1y", "2y", "5y", "max"])
run_button = st.sidebar.button("🚀 วิเคราะห์เต็มระบบ")

# --- 3. ฟังก์ชันโหลดข้อมูล (Stable Version) ---
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

# --- 4. ฟังก์ชันคำนวณ Banker Volume (MCDX) ---
def calculate_banker_volume(df):
    rsi_banker = ta.rsi(df['Close'], length=50)
    rsi_hot = ta.rsi(df['Close'], length=40)
    
    # คำนวณค่าพลัง (Sensitivity Adjustment)
    df['Banker_Val'] = (rsi_banker - 50) * 1.5 
    df['HotMoney_Val'] = (rsi_hot - 30) * 0.7
    
    # Clip ค่าให้อยู่ในช่วง 0-20
    df['Banker_Val'] = df['Banker_Val'].clip(lower=0, upper=20)
    df['HotMoney_Val'] = df['HotMoney_Val'].clip(lower=0, upper=20)
    return df

# --- 5. ส่วนแสดงผลหลัก ---
st.title(f"💎 {symbol} Ultimate Analysis")

if run_button:
    with st.spinner(f'กำลังประมวลผลข้อมูลรายใหญ่ {symbol} ...'):
        df = load_data(symbol, period, timeframe)
        
    if df is None or len(df) < 60:
        st.error("❌ ไม่พบข้อมูล หรือข้อมูลน้อยเกินไป")
    else:
        try:
            # --- A. คำนวณ Indicators ทั้งหมด ---
            # 1. Trend
            df['EMA_12'] = df.ta.ema(length=12)
            df['EMA_26'] = df.ta.ema(length=26)
            
            # 2. Momentum & Volume
            df['RSI'] = df.ta.rsi(length=14)
            df['OBV'] = df.ta.obv()
            df['AOBV'] = df['OBV'].rolling(window=30).mean()
            
            # 3. Support/Resistance (Bollinger Bands & High)
            bb = df.ta.bbands(length=20, std=2)
            df = pd.concat([df, bb], axis=1)
            bbl = df.columns[df.columns.str.startswith('BBL')][0]
            bbm = df.columns[df.columns.str.startswith('BBM')][0]
            bbu = df.columns[df.columns.str.startswith('BBU')][0]
            df['High_20'] = df['High'].rolling(20).max()
            
            # 4. Banker Volume
            df = calculate_banker_volume(df)

            # ลบค่าว่าง
            df.dropna(inplace=True)
            last = df.iloc[-1]

            # --- B. คำนวณจุดซื้อ/ขาย 3 ระดับ ---
            buy1, buy2, buy3 = last['EMA_26'], last[bbm], last[bbl]
            sell1, sell2, sell3 = last[bbu], last['High_20'], last['High_20'] * 1.05

            # --- C. สร้างกราฟ 4 ช่อง (Price / Banker / RSI / OBV) ---
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.15, 0.15],
                                subplot_titles=(f"Price & Strategy", "💰 Banker Volume (MCDX)", "Momentum (RSI)", "Volume Flow (OBV)"))

            # Row 1: Price
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                         low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_12'], line=dict(color='#00ff00', width=1), name='EMA 12'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_26'], line=dict(color='#ff0000', width=1), name='EMA 26'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbu], line=dict(color='gray', width=1, dash='dot'), name='Upper Band'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df[bbl], line=dict(color='gray', width=1, dash='dot'), name='Lower Band'), row=1, col=1)

            # Row 2: Banker Volume
            colors = ['red' if b > 10 else ('orange' if b > 5 else 'green') for b in df['Banker_Val']]
            fig.add_trace(go.Bar(x=df.index, y=df['Banker_Val'], name='Banker', marker_color=colors), row=2, col=1)
            fig.add_hline(y=10, line_dash="dot", line_color="white", row=2, col=1)

            # Row 3: RSI
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#aa00ff', width=2), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

            # Row 4: OBV
            fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], line=dict(color='cyan', width=1), name='OBV'), row=4, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['AOBV'], line=dict(color='orange', width=1, dash='dash'), name='AOBV'), row=4, col=1)

            fig.update_layout(height=1000, xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

            # --- D. สรุปผลการวิเคราะห์ (The Dashboard) ---
            st.markdown("### 📊 สรุปสถานะล่าสุด")
            c1, c2, c3, c4 = st.columns(4)
            
            # 1. Trend
            trend_state = "UP 🐂" if last['EMA_12'] > last['EMA_26'] else "DOWN 🐻"
            c1.metric("Trend (EMA)", trend_state)

            # 2. Banker
            banker_score = last['Banker_Val']
            if banker_score > 10: banker_msg = "🔥 เจ้ามือคุม"
            elif banker_score > 5: banker_msg = "⚠️ เก็งกำไร"
            else: banker_msg = "💤 รายย่อย"
            c2.metric("Banker Status", banker_msg)

            # 3. RSI
            rsi_msg = "Overbought ⚠️" if last['RSI'] > 70 else ("Oversold ✅" if last['RSI'] < 30 else "Normal")
            c3.metric("RSI", f"{last['RSI']:.1f}", rsi_msg)

            # 4. OBV
            obv_msg = "Strong 💪" if last['OBV'] > last['AOBV'] else "Weak 💤"
            c4.metric("Volume Flow", obv_msg)

            st.markdown("---")

            # --- E. คำแนะนำและเป้าหมายราคา (Strategy Table) ---
            col_strat1, col_strat2 = st.columns(2)

            with col_strat1:
                st.subheader("🎯 Action Recommendation")
                
                # Logic การตัดสินใจ (รวมทุกเงื่อนไข)
                score = 0
                if last['EMA_12'] > last['EMA_26']: score += 1
                if last['OBV'] > last['AOBV']: score += 1
                if banker_score > 10: score += 2  # ให้คะแนนเจ้ามือเยอะหน่อย
                if last['RSI'] < 70: score += 1

                if score >= 4:
                    st.success(f"🚀 **STRONG BUY** (คะแนน {score}/5)\n\nรายใหญ่เข้า + เทรนด์มา + วอลุ่มแน่น")
                elif score >= 2:
                    st.warning(f"⏸ **WAIT / HOLD** (คะแนน {score}/5)\n\nสัญญาณยังไม่ครบ รอความชัดเจน")
                else:
                    st.error(f"❌ **SELL / AVOID** (คะแนน {score}/5)\n\nเทรนด์ขาลง หรือเจ้ามือทิ้งของ")

            with col_strat2:
                st.subheader("📍 Key Levels (ไม้ตาย)")
                tab1, tab2 = st.tabs(["🛡️ แนวรับ (ซื้อ)", "⚔️ แนวต้าน (ขาย)"])
                
                with tab1:
                    st.markdown(f"""
                    - **ไม้ 1 (Trend):** `{buy1:.2f}` (EMA 26)
                    - **ไม้ 2 (Value):** `{buy2:.2f}` (BB Mid)
                    - **ไม้ 3 (Dip):** `{buy3:.2f}` (BB Low - ของถูก)
                    """)
                
                with tab2:
                    st.markdown(f"""
                    - **เป้า 1 (Quick):** `{sell1:.2f}` (BB High)
                    - **เป้า 2 (High):** `{sell2:.2f}` (High เดิม)
                    - **เป้า 3 (Run):** `{sell3:.2f}` (Breakout +5%)
                    """)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

else:
    st.info("👈 กดปุ่มเพื่อเริ่มวิเคราะห์ (รองรับรายใหญ่ + จุดซื้อขายครบจบในที่เดียว)")
