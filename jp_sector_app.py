import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import datetime as dt
from datetime import time as dt_time
import time
import pytz
from jp_sector_data_v2 import fetch_sector_metrics_top500

# ----- ページ設定 -----
# app.py で一括設定するためここでは削除またはコメントアウト
# st.set_page_config(page_title="🇯🇵 全33業種 詳細データテーブル", page_icon="🇯🇵", layout="wide")

def main():
    # ----- キャッシュとデータ取得 -----
    # ユーザーの要望「同期は数分おきでもいい」に基づき、キャッシュの有効期限(ttl)を5分(300秒)に設定します。
    @st.cache_data(ttl=300, show_spinner=False)
    def load_data():
        return fetch_sector_metrics_top500()
    
    # 現在時刻のステータス取得（NY時間の代わりに日本時間）
    def get_market_status():
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        open_time = dt_time(9, 0)
        close_time = dt_time(15, 30)
        
        if now.time() < open_time:
            return "💤 市場オープン前 (前営業日のデータ)"
        elif now.time() <= close_time:
            return "🟢 日本市場 取引時間中 (約5分ごとに自動更新)"
        else:
            return "🔴 日本市場 クローズ (本日の確定データ)"
    
    status_msg = get_market_status()
    
    # 1. 相場天気予報（モックアップ）
    st.markdown("""
    <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border-left: 5px solid #FF5252; margin-bottom: 20px;">
        <p style="color: #9E9E9E; font-size: 14px; margin-bottom: 5px; font-weight: bold;">今日の相場天気予報 (デモ)</p>
        <h3 style="color: #FF5252; margin-top: 0px; margin-bottom: 10px;">☔ ギャップダウン警戒（弱気）</h3>
        <p style="color: #E0E0E0; font-size: 14px; line-height: 1.6;">
            日経先物が日経終値を大きく下回っています。明日は安く寄り付くリスクが高く、ポジション縮小を検討すべき地合いです。地政学リスクとインフレ懸念が市場を二分する中、米国株の堅調と一部セクターの個別材料は買いを誘ったが、日本株全体としては持続的な強さには欠け、明日はギャップダウンへの警戒が必要である。
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    
    st.title("📋 日本株セクター別 騰落ダッシュボード")
    st.info(f"**ステータス:** {status_msg}")
    
    st.markdown("日本を代表する主要約500銘柄（TOPIX 500等）のデータを集計し、33業種別の動向を可視化しています。")
    
    # キャッシュされたデータ取得関数
    @st.cache_data(ttl=300, show_spinner=False)
    def load_data():
        return fetch_sector_metrics_top500()
    
    # 初回ロードのハンドリング
    if 'df_sectors' not in st.session_state:
        st.session_state['df_sectors'] = pd.DataFrame()
        st.session_state['df_heatmap'] = pd.DataFrame()
    
    # バックグラウンド更新のよう見せるための処理
    # キャッシュが切れている場合、st.spinnerを別枠で回しつつ前回データがあればそれを残す
    with st.spinner("最新の市場データを取得または更新しています..."):
        new_sectors, new_heatmap, new_update_time = load_data()
        # 取得成功したらセッションステートを更新する
        if not new_sectors.empty and not new_heatmap.empty:
            st.session_state['df_sectors'] = new_sectors
            st.session_state['df_heatmap'] = new_heatmap
            st.session_state['update_time_str'] = new_update_time
    
    df_sectors = st.session_state['df_sectors']
    df_heatmap = st.session_state['df_heatmap']
    update_time_str = st.session_state.get('update_time_str', "")
    
    if df_sectors.empty or df_heatmap.empty:
        st.error("データの取得に失敗しました。時間をおいてページを再読み込みしてください。")
        st.stop()
    
    
    # ----- 2. ヒートマップ（ツリーマップ）の描画 -----
    col1, col2 = st.columns([1, 1])
    with col1:
        st.header("🗺️ 日本株 全体ヒートマップ (主要約500銘柄)")
    with col2:
        st.markdown(f"<div style='text-align: right; color: gray; font-size: 14px; margin-top: 30px;'>最終更新: {update_time_str}</div>", unsafe_allow_html=True)
        
    st.markdown("ブロックの大きさは「**当日の概算売買代金**」、色は「**前日比の騰落率**」を表しています。")
    
    # PlotlyのTreemapを作成
    fig = px.treemap(
        df_heatmap,
        path=[px.Constant("日本市場 (主要銘柄)"), "Sector", "Name"],
        values="Size",  # 売買代金ベース
        color="Change", # 騰落率ベース
        color_continuous_scale=["#FF0000", "#333333", "#00FF00"], # 赤 -> 黒 -> 緑
        color_continuous_midpoint=0,
        custom_data=["ChangeStr", "Price", "YahooURL"],
        hover_name="Name"
    )
    
    # 見た目の調整
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]}",
        textfont=dict(size=24, family="sans-serif", weight="bold"),
        textposition="middle center", # テキストを中央に配置
        hovertemplate="<b>%{label}</b><br>価格: ¥%{customdata[1]:.1f}<br>騰落率: %{customdata[0]}<extra></extra>"
    )
    
    fig.update_layout(
        margin=dict(t=30, l=10, r=10, b=10),
        coloraxis_showscale=False,
        height=1100 # PCでも横長になりすぎないように高さを増やす
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ----- 3. データテーブルの表示 -----
    col1, col2 = st.columns([1, 1])
    with col1:
        st.header("🏢 全33業種 詳細データテーブル")
    with col2:
        st.markdown(f"<div style='text-align: right; color: gray; font-size: 14px; margin-top: 30px;'>最終更新: {update_time_str}</div>", unsafe_allow_html=True)
    
    with st.expander("💡 テーブルの各項目の見方"):
        st.markdown("""
        - **シグナル**: 波及度や出来高、乖離率から算出した現在のセクターの過熱感や勢いを示します。
          - **🔥 最強の波(全面高)**: 出来高が急増(1.5倍超)し、セクター内銘柄の80%以上が上昇、平均騰落率も+1.0%を超えるときに点灯。強い資金流入を示します。
          - **⚠️ ハリボテ警戒**: セクター平均はプラス(+0.5%超)でも、実際に上昇している銘柄が20%以下のときに点灯。一部の値がさ株だけで指数を押し上げている可能性があります。
          - **⚠️ 加熱警戒**: 25日移動平均を10%以上上回っている状態。短期的な調整（下落）リスクが高まっています。
          - **☔ リバウンド狙い(総悲観)**: セクターの殆ど(90%以上)が下落し、25日線からも10%以上下方乖離している状態。売られすぎからの自律反発が狙える水準です。
          - **👍 堅調**: 大きな過熱感はなく、70%以上の銘柄が着実に上昇している健全な上昇トレンドです。
        - **スコア (0-100)**: 騰落率と波及度（上昇銘柄の割合）を組み合わせた総合的な強さの指標です。
        - **出来高倍率**: 直近25日での平均出来高と比較して、本日の出来高が何倍に膨らんでいるかを示します。（1.0以上なら活況）
        - **25MA乖離**: 25日移動平均線からのプラス・マイナスの乖離率。トレンドの過熱感を図る指標です。
        - **波及度**: そのセクター内で、本日株価が上昇している銘柄の割合(%)です。
        """)
    
    st.dataframe(
        df_sectors,
        column_config={
            "シグナル": st.column_config.TextColumn("シグナル", width=120),
            "セクター": st.column_config.TextColumn("セクター", width=120),
            "代表銘柄": st.column_config.TextColumn("代表銘柄 (売買代金上位)", width=250),
            "構成銘柄数": st.column_config.NumberColumn("↑対象", format="%d社", width=60),
            "スコア": st.column_config.ProgressColumn(
                "スコア", 
                help="総合的な強さのスコア(0-100)", 
                min_value=0, 
                max_value=100, 
                format="%d",
                width=80
            ),
            "騰落率": st.column_config.NumberColumn(
                "ｾｸﾀｰ騰落",
                format="%.2f %%",
                width=80
            ),
            "出来高倍率": st.column_config.NumberColumn(
                "出来高倍率",
                format="%.2f x",
                width=80
            ),
            "25MA乖離": st.column_config.NumberColumn(
                "25MA乖離(平均)",
                format="%+.2f %%",
                width=80
            ),
            "波及度": st.column_config.ProgressColumn(
                "資金の波及度 (Breadth)",
                help="セクター内で前日比プラスの銘柄の割合",
                min_value=0,
                max_value=100,
                format="%d %%",
                width=100
            )
        },
        hide_index=True,
        use_container_width=False, # 固定幅レイアウトを優先して画像のように一覧しやすくする
        width=1200,                # デフォルトの横幅を広く確保
        height=600
    )
    
    # ----- 4. リプレイ＆深掘りUI -----
    st.markdown("---")
    
    # [一時対応] リプレイ機能は動作が不安定なため、一旦非表示にしています。
    # st.header("🎞️ ヒートマップ リプレイ (直近1営業日)")
    # st.markdown("直近1営業日の値動き（15分刻み）をアニメーション再生します。（データ取得に少し時間がかかります）")
    # 
    # if st.button("⏪ データ取得＆リプレイ再生"):
    #     with st.spinner("1日分の詳細データを取得・構築しています... (約10〜30秒)"):
    #         from jp_sector_data_v2 import fetch_intraday_replay_data
    #         frames, times = fetch_intraday_replay_data()
    #         
    #     if not frames:
    #         st.error("データの取得に失敗しました。時間外か、API制限の可能性があります。")
    #     else:
    #         st.success("再生を開始します！")
    #         replay_container = st.empty()
    #         
    #         # Determine fixed color range dynamically based on max/min to keep colors stable
    #         max_val = max(f['Change'].max() for f in frames) if frames else 3.0
    #         min_val = min(f['Change'].min() for f in frames) if frames else -3.0
    #         c_max = max(abs(max_val), abs(min_val))
    #         if pd.isna(c_max) or c_max == 0:
    #             c_max = 3.0
    # 
    #         for frame, ts_str in zip(frames, times):
    #             fig_anim = px.treemap(
    #                 frame,
    #                 path=[px.Constant("日本市場 (主要銘柄)"), "Sector", "Name"],
    #                 values="Size",
    #                 color="Change",
    #                 color_continuous_scale=["#FF0000", "#333333", "#00FF00"],
    #                 color_continuous_midpoint=0,
    #                 range_color=[-c_max, c_max], # Fixed color scale across frames
    #                 custom_data=["ChangeStr", "TradingVal", "Price"], # custom_dataを更新
    #             )
    #             fig_anim.update_traces(
    #                 textinfo="label+text",
    #                 textfont=dict(size=24, family="sans-serif", weight="bold"),
    #                 hovertemplate="<b>%{label}</b><br>騰落率: %{customdata[0]}<br>売買代金: %{customdata[1]:.1f}億円<br>現在値: ¥%{customdata[2]:.1f}<extra></extra>"
    #             )
    #             fig_anim.update_layout(
    #                 title=f"🕒 再生中時刻: {ts_str} (日本時間)",
    #                 margin=dict(t=50, l=10, r=10, b=10),
    #                 coloraxis_showscale=False,
    #                 height=750
    #             )
    #             replay_container.plotly_chart(fig_anim, use_container_width=True)
    #             time.sleep(1.0) # 1秒ごとに次のフレームへ
    
    st.markdown("---")
    st.markdown("#### 🔍 特定のセクターをさらに深掘りする")
    st.write("気になるセクターを選んで、構成されている個別銘柄の値動きを確認します。")
    
    sector_list = [row['セクター'] for _, row in df_sectors.iterrows()]
    
    selected_sector = st.selectbox("セクターを選択", sector_list, label_visibility="collapsed")
    
    if selected_sector:
        current_sector = selected_sector
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"##### 🏢 【{current_sector}】 トップ構成銘柄一覧")
        with col2:
            st.markdown(f"<div style='text-align: right; color: gray; font-size: 12px; margin-top: 5px;'>最終更新: {update_time_str}</div>", unsafe_allow_html=True)
        
        # 最新のデータを再処理して必要な情報を追加
        sector_data = df_heatmap[df_heatmap['Sector'] == current_sector].copy()
        
        # 寄り付きからの騰落率（寄付比）順にソート（デフォルト）
        if 'OpenChange' not in sector_data.columns:
            st.warning("データ更新待ちです。少し待ってから再度お試しください。")
            st.stop()
            
        sector_data = sector_data.sort_values(by='OpenChange', ascending=False).reset_index(drop=True)
        
        # 順位を追加
        sector_data['順位'] = range(1, len(sector_data) + 1)
        
        # 表示用の文字列を結合
        sector_data['銘柄名 (コード)'] = sector_data['Name'] + " (" + sector_data['Ticker'] + ")"
        
        # 売買代金を「億円」単位に変換
        sector_data['TradingValOku'] = sector_data['TradingVal'] / 100000000
        
        # 表示用のデータフレームに整形
        display_df = sector_data[['順位', '銘柄名 (コード)', 'YahooURL', 'Price', 'OpenChange', 'Change', 'TradingValOku', 'Bollinger', '5MADiv']].rename(columns={
            "YahooURL": "リンク",
            "Price": "現在値",
            "OpenChange": "寄付比 ▼",
            "Change": "前日比",
            "TradingValOku": "売買代金",
            "Bollinger": "ﾎﾞﾘﾝｼﾞｬｰ",
            "5MADiv": "5MA乖離率"
        })
        
        # 簡易なテーブル表示（色付け付き）
        # pandas Styler を使った動的ハイライト（ﾎﾞﾘﾝｼﾞｬｰ >= 2.0 or 5MA乖離率 >= 5.0 を黄色に）
        def highlight_cells(val, col_name):
            if pd.isna(val):
                return ''
            try:
                val_float = float(val)
                if col_name == 'ﾎﾞﾘﾝｼﾞｬｰ' and val_float >= 2.0:
                    return 'background-color: rgba(255, 255, 0, 0.3)' # 薄い黄色
                if col_name == '5MA乖離率' and val_float >= 5.0:
                    return 'background-color: rgba(255, 255, 0, 0.3)' # 薄い黄色
            except ValueError:
                pass
            return ''
    
        # st.dataframe は pandas Styler オブジェクトを直接受け取ることができる
        styled_df = display_df.style.map(lambda x: highlight_cells(x, 'ﾎﾞﾘﾝｼﾞｬｰ'), subset=['ﾎﾞﾘﾝｼﾞｬｰ']) \
                                    .map(lambda x: highlight_cells(x, '5MA乖離率'), subset=['5MA乖離率'])
        
        st.markdown("<p style='color: gray; font-size: 14px; margin-bottom: 5px;'>👉 テーブルの行をクリックすると、その銘柄のYahoo!ファイナンスページが開きます。</p>", unsafe_allow_html=True)
        
        event = st.dataframe(
            styled_df,
            column_config={
                "順位": st.column_config.NumberColumn("順位", width=60),
                "銘柄名 (コード)": st.column_config.TextColumn("銘柄名 (コード)", width=220),
                "リンク": st.column_config.LinkColumn("Yahoo!", display_text="🔗 詳細", width=70),
                "現在値": st.column_config.NumberColumn("現在値", format="%.1f", width=80),
                "寄付比 ▼": st.column_config.NumberColumn("寄付比 ▼", format="%+.2f %%", width=100),
                "前日比": st.column_config.NumberColumn("前日比", format="%+.2f %%", width=100),
                "売買代金": st.column_config.NumberColumn("売買代金", format="%.1f 億", width=100),
                "ﾎﾞﾘﾝｼﾞｬｰ": st.column_config.NumberColumn("ﾎﾞﾘﾝｼﾞｬｰ", format="%+.2f σ", width=100),
                "5MA乖離率": st.column_config.NumberColumn("5MA乖離率", format="%+.2f %%", width=100),
            },
            hide_index=True,
            use_container_width=False,
            width=1200,
            on_select="rerun",
            selection_mode="single-row",
            key=f"jp_table_selection_{current_sector}"
        )
        
        # 選択された行があればYahooURLを開く
        selected_rows = []
        if hasattr(event, 'selection'):
            selected_rows = getattr(event, 'selection').get('rows', [])
        elif isinstance(event, dict) and 'selection' in event:
            selected_rows = event['selection'].get('rows', [])
            
        if selected_rows:
            selected_idx = selected_rows[0]
            if 'YahooURL' in sector_data.columns:
                yahoo_url = sector_data.iloc[selected_idx]['YahooURL']
                if pd.notna(yahoo_url) and str(yahoo_url).startswith("http"):
                    st.components.v1.html(
                        f"<script>window.open('{yahoo_url}', '_blank');</script>",
                        height=0,
                    )

if __name__ == "__main__":
    st.set_page_config(page_title="🇯🇵 全33業種 詳細データテーブル", page_icon="🇯🇵", layout="wide")
    main()
