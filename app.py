import streamlit as st
import pandas as pd
from data_loader import get_screener_data

# Page config
st.set_page_config(page_title="日本株スクリーニングツール", layout="wide")

st.title("📊 日本株スクリーニングツール")

# --- Default setup and state ---
if 'data' not in st.session_state:
    st.session_state['data'] = pd.DataFrame()

# --- Sidebar Filters ---
st.sidebar.header("スクリーニング条件")

# Strategy Selection
strategy = st.sidebar.selectbox(
    "基本戦略プリセット (後日拡張用)",
    ["カスタム", "割安高配当", "短期モメンタム"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("ファンダメンタルズ指標")
per_max = st.sidebar.slider("PER (倍) 以下", min_value=0.0, max_value=100.0, value=15.0, step=1.0)
pbr_max = st.sidebar.slider("PBR (倍) 以下", min_value=0.0, max_value=10.0, value=1.5, step=0.1)
dividend_min = st.sidebar.slider("配当利回り (%) 以上", min_value=0.0, max_value=10.0, value=3.0, step=0.1)
roe_min = st.sidebar.slider("ROE (%) 以上", min_value=-20.0, max_value=50.0, value=8.0, step=1.0)
market_cap_min = st.sidebar.slider("時価総額 (億円) 以上", min_value=0, max_value=100000, value=1000, step=100)

st.sidebar.markdown("---")
st.sidebar.subheader("テクニカル指標")
ma5_dev_max = st.sidebar.slider("5MA乖離率 (%) 以下", min_value=-20.0, max_value=20.0, value=0.0, step=0.5)
rsi_max = st.sidebar.slider("RSI (14) 以下 (割安感)", min_value=0.0, max_value=100.0, value=40.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.subheader("市況指標")
trading_value_min = st.sidebar.slider("売買代金 (億円) 以上", min_value=0, max_value=1000, value=10, step=10)

# Refresh Button
if st.sidebar.button("データ取得 & スクリーニング実行", type="primary"):
    with st.spinner("データを取得・計算しています... (数分かかる場合があります)"):
        # Fetch data
        df = get_screener_data()
        
        if not df.empty:
            # Add MarketCap in Oku-Yen and Trading value in Oku-Yen for filtering convenience
            df['MarketCap_Oku'] = df['MarketCap'] / 100000000
            df['Trading_Value_Oku'] = df['Trading_Value'] / 100000000
            st.session_state['data'] = df
        else:
            st.error("データの取得に失敗しました。")

# --- Main Area Display ---
df = st.session_state['data']

if not df.empty:
    # --- Apply Filters ---
    filtered_df = df.copy()
    
    # Fundamentals
    if pd.notnull(per_max):
        filtered_df = filtered_df[pd.isna(filtered_df['PER']) | (filtered_df['PER'] <= per_max)]
    if pd.notnull(pbr_max):
         filtered_df = filtered_df[pd.isna(filtered_df['PBR']) | (filtered_df['PBR'] <= pbr_max)]
    if pd.notnull(dividend_min):
         filtered_df = filtered_df[pd.isna(filtered_df['DividendYield_%']) | (filtered_df['DividendYield_%'] >= dividend_min)]
    if pd.notnull(roe_min):
         filtered_df = filtered_df[pd.isna(filtered_df['ROE']) | (filtered_df['ROE'] >= roe_min)]
    if pd.notnull(market_cap_min):
         filtered_df = filtered_df[pd.isna(filtered_df['MarketCap_Oku']) | (filtered_df['MarketCap_Oku'] >= market_cap_min)]
         
    # Technicals
    if pd.notnull(ma5_dev_max):
         filtered_df = filtered_df[pd.isna(filtered_df['5MA_Dev_%']) | (filtered_df['5MA_Dev_%'] <= ma5_dev_max)]
    if pd.notnull(rsi_max):
         filtered_df = filtered_df[pd.isna(filtered_df['RSI']) | (filtered_df['RSI'] <= rsi_max)]
         
    # Market
    if pd.notnull(trading_value_min):
         filtered_df = filtered_df[pd.isna(filtered_df['Trading_Value_Oku']) | (filtered_df['Trading_Value_Oku'] >= trading_value_min)]

    # --- Display Results ---
    st.subheader(f"スクリーニング結果: {len(filtered_df)} 銘柄 / 対象 {len(df)} 銘柄")
    
    # Format the dataframe for display
    display_df = filtered_df[['Ticker', 'Name', 'Price', 'PER', 'PBR', 'DividendYield_%', 'ROE', '5MA_Dev_%', 'RSI', 'Open_to_Close_Return_%', 'Trading_Value_Oku']].copy()
    
    # Define formatting styles
    format_dict = {
        'Price': "{:.1f}",
        'PER': "{:.2f}",
        'PBR': "{:.2f}",
        'DividendYield_%': "{:.2f}%",
        'ROE': "{:.1f}%",
        '5MA_Dev_%': "{:.2f}%",
        'RSI': "{:.1f}",
        'Open_to_Close_Return_%': "{:.2f}%",
        'Trading_Value_Oku': "{:.0f}"
    }
    
    st.dataframe(
        display_df.style.format(format_dict, na_rep="-"),
        use_container_width=True,
        height=600
    )
else:
    st.info("👈 サイドバーから「データ取得 & スクリーニング実行」 をクリックしてください。")
