import streamlit as st
import jp_sector_app
import us_sector_app

st.set_page_config(page_title="🌎 グローバルセクターダッシュボード", page_icon="🌎", layout="wide")

tab1, tab2 = st.tabs(["🇯🇵 日本株 (33業種)", "🇺🇸 米国株 (11セクター)"])

with tab1:
    jp_sector_app.main()

with tab2:
    us_sector_app.main()
