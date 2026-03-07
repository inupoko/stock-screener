import yfinance as yf
import pandas as pd
import time
import requests
from jp_sectors_config import JP_SECTORS

def fetch_sector_metrics():
    """
    Fetches data for 33 JP sectors, calculates metrics like Breadth, Volume Ratio, and 25MA Div.
    Returns a pandas DataFrame.
    """
    all_tickers = []
    for t_list in JP_SECTORS.values():
        all_tickers.extend(t_list)
        
    all_tickers = list(set(all_tickers)) # Unique tickers
    print(f"Fetching data for {len(all_tickers)} representative stocks...")
    
    # Download data
    try:
        data = yf.download(all_tickers, period="2mo", progress=False)
    except Exception as e:
        print(f"Error downloading data: {e}")
        return pd.DataFrame()
        
    sector_results = []
    
    # Process each sector
    for sector_name, tickers in JP_SECTORS.items():
        valid_tickers = [t for t in tickers if t in data['Close'].columns]
        
        if not valid_tickers:
            continue
            
        sector_price_changes = []
        sector_25ma_divs = []
        sector_vol_ratios = []
        positive_count = 0
        
        rep_names = []
        
        for ticker in valid_tickers:
            # We get individual stock series
            try:
                close_series = data['Close'][ticker].dropna()
                vol_series = data['Volume'][ticker].dropna()
                
                if len(close_series) < 2:
                    continue
                
                # Close price change
                latest_close = float(close_series.iloc[-1])
                prev_close = float(close_series.iloc[-2])
                price_change_pct = ((latest_close - prev_close) / prev_close) * 100
                sector_price_changes.append(price_change_pct)
                
                if price_change_pct > 0:
                    positive_count += 1
                
                # 25MA Div
                if len(close_series) >= 25:
                    ma25 = close_series.iloc[-25:].mean()
                    ma25_div = ((latest_close - ma25) / ma25) * 100
                    sector_25ma_divs.append(ma25_div)
                    
                # Volume ratio
                if len(vol_series) >= 25:
                    avg_vol_25 = vol_series.iloc[-25:].mean()
                    latest_vol = float(vol_series.iloc[-1])
                    if avg_vol_25 > 0:
                        vol_ratio = latest_vol / avg_vol_25
                        sector_vol_ratios.append(vol_ratio)
                        
                # Representative names (simple fallback if we can't fetch fast)
                name_mapping = {
                    "1332.T": "ニッスイ", "1333.T": "マルハニチロ", "1605.T": "INPEX", 
                    "1662.T": "石油資源開発", "1925.T": "大和ハウス", "1928.T": "積水ハウス",
                    "2502.T": "アサヒ", "2802.T": "味の素", "3402.T": "東レ", "3401.T": "帝人",
                    "3861.T": "王子HD", "3863.T": "日本製紙", "4063.T": "信越化学", "4452.T": "花王",
                    "4502.T": "武田薬品", "4568.T": "第一三共", "5020.T": "ENEOS", "5019.T": "出光興産",
                    "5108.T": "ブリヂストン", "5101.T": "横浜ゴム", "5201.T": "AGC", "5332.T": "TOTO",
                    "5401.T": "日本製鉄", "5411.T": "JFE", "5713.T": "住友鉱", "5802.T": "住友電工",
                    "5938.T": "LIXIL", "3436.T": "SUMCO", "6367.T": "ダイキン", "6273.T": "SMC",
                    "6501.T": "日立", "6758.T": "ソニー", "7203.T": "トヨタ", "7267.T": "ホンダ",
                    "7741.T": "HOYA", "7733.T": "オリンパス", "7974.T": "任天堂", "7832.T": "バンナム",
                    "9503.T": "関西電", "9501.T": "東京電", "9020.T": "JR東", "9022.T": "JR東海",
                    "9101.T": "郵船", "9104.T": "商船三井", "9202.T": "ANA", "9201.T": "JAL",
                    "9301.T": "三菱倉庫", "9364.T": "上組", "9432.T": "NTT", "9433.T": "KDDI",
                    "8058.T": "三菱商", "8031.T": "三井物", "9983.T": "ファストリ", "3382.T": "セブン&アイ",
                    "8306.T": "三菱UFJ", "8316.T": "三井住友", "8604.T": "野村HD", "8601.T": "大和証券",
                    "8766.T": "東京海上", "8750.T": "第一生命", "8591.T": "オリックス", "8697.T": "JPX",
                    "8801.T": "三井不動産", "8802.T": "三菱地所", "6098.T": "リクルート", "4689.T": "LINEヤフー"
                }

                if len(rep_names) < 2:
                    rep_name = name_mapping.get(ticker, ticker.replace(".T", ""))
                    if rep_name not in rep_names:
                        rep_names.append(rep_name)
                        
            except Exception as e:
                pass
                
        # Calculate Sector Averages
        if not sector_price_changes:
            continue
            
        avg_change = sum(sector_price_changes) / len(sector_price_changes)
        breadth = (positive_count / len(valid_tickers)) * 100
        avg_25ma_div = sum(sector_25ma_divs) / len(sector_25ma_divs) if sector_25ma_divs else 0
        avg_vol_ratio = sum(sector_vol_ratios) / len(sector_vol_ratios) if sector_vol_ratios else 0
        
        rep_str = ", ".join(rep_names)
        
        # Calculate a mock score (0-100) based on momentum and breadth
        # Score factors: Change (+5% = 100, -5% = 0), Breadth (100% = +20, 0% = -20)
        base_score = 50 + (avg_change * 10)  # If +2%, base is 70
        breadth_adj = (breadth - 50) * 0.4   # If Breadth 80%, adj is +12
        score = int(max(0, min(100, base_score + breadth_adj)))
        
        # Signal evaluation
        signal = "-"
        if avg_vol_ratio > 1.5 and breadth >= 80 and avg_change > 1.0:
            signal = "🔥 最強の波(全面高)"
        elif breadth <= 20 and avg_change > 0.5:
            signal = "⚠️ ハリボテ警戒"
        elif avg_25ma_div > 10:
            signal = "⚠️ 加熱警戒"
        elif breadth <= 10 and avg_25ma_div < -10:
            signal = "☔ リバウンド狙い(総悲観)"
        elif breadth > 70 and 0.5 < avg_change <= 1.5:
            signal = "👍 堅調"
            
        sector_results.append({
            "シグナル": signal,
            "セクター": sector_name,
            "代表銘柄": rep_str,
            "スコア": score,
            "騰落率": avg_change,
            "出来高倍率": avg_vol_ratio,
            "25MA乖離": avg_25ma_div,
            "波及度": int(breadth)
        })
        
    df = pd.DataFrame(sector_results)
    # Sort by score by default
    if not df.empty:
        df = df.sort_values(by="スコア", ascending=False)
        
    return df

if __name__ == "__main__":
    print("Testing sector data fetching...")
    df = fetch_sector_metrics()
    print(df)
