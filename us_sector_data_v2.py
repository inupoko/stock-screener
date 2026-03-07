import yfinance as yf
import pandas as pd

def shorten_company_name(name: str) -> str:
    """Removes common corporate suffixes for US stocks and limits length."""
    remove_words = [" Inc.", " Corp.", " Corporation", " Company", " Holdings", " Group", " PLC", " Ltd.", " N.V.", " Co.", ".com", " Class A", " Class B", " Class C"]
    short_name = name
    for word in remove_words:
        short_name = short_name.replace(word, "")
    
    # Strip whitespace
    short_name = short_name.strip()
    
    # Hardcap length for very long names
    if len(short_name) > 12:
        short_name = short_name[:11] + "…"
        
    return short_name

# Define sectors mapped to comprehensive list of major US tickers (proxy for S&P100 + tech)
SECTOR_DICT = {
    "情報技術 (IT)": ["AAPL", "MSFT", "NVDA", "AVGO", "ADBE", "CRM", "AMD", "ACN", "CSCO", "INTC", "QCOM", "TXN", "IBM", "NOW", "INTU", "AMAT", "MU", "ADI", "LRCX"],
    "金融": ["JPM", "V", "MA", "BAC", "WFC", "SPGI", "AXP", "GS", "MS", "BLK", "C", "CB", "MMC", "PGR", "CME", "SCHW", "AON"],
    "ヘルスケア": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "SYK", "AMGN", "ISRG", "MDT", "ELV", "VRTX", "BMY", "BSX", "ZTS"],
    "一般消費財": ["AMZN", "TSLA", "HD", "TMUS", "MCD", "NKE", "SBUX", "LOW", "BKNG", "TJX", "CMG", "MAR", "ORLY", "HLT"],
    "通信サービス": ["META", "GOOGL", "GOOG", "NFLX", "DIS", "CMCSA", "VZ", "T", "CHTR", "EA"],
    "資本財": ["CAT", "GE", "UNP", "BA", "HON", "RTX", "UPS", "LMT", "DE", "ADP", "CSX", "ETN", "WM", "NOC", "GD", "PCAR"],
    "生活必需品": ["PG", "KO", "WMT", "PEP", "COST", "PM", "MO", "MDLZ", "EL", "CL", "SYY", "KMB"],
    "エネルギー": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "HES", "HAL"],
    "公益事業": ["NEE", "SO", "DUK", "SRE", "AEP", "D", "EXC", "PCG", "XEL", "ED"],
    "不動産": ["PLD", "AMT", "EQIX", "SPG", "CCI", "PSA", "O", "WELL"],
    "素材": ["LIN", "SHW", "NEM", "ECL", "FCX", "APD", "NUE", "CTVA", "DOW", "PPG"]
}

def fetch_us_sector_metrics():
    """Fetches and calculates comprehensive sector metrics for US major stocks."""
    all_tickers = []
    for t_list in SECTOR_DICT.values():
        all_tickers.extend(t_list)
        
    all_tickers = list(set(all_tickers))
    
    try:
        data = yf.download(all_tickers, period="2mo", progress=False)
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()
    
    sector_results = []
    heatmap_data = []
    
    for sector_name, tickers in SECTOR_DICT.items():
        valid_tickers = [t for t in tickers if t in data['Close'].columns]
        
        if not valid_tickers:
            continue
            
        sector_price_changes = []
        sector_25ma_divs = []
        sector_vol_ratios = []
        positive_count = 0
        
        for ticker in valid_tickers:
            try:
                close_series = data['Close'][ticker].dropna()
                open_series = data['Open'][ticker].dropna()
                vol_series = data['Volume'][ticker].dropna()
                
                if len(close_series) < 2:
                    continue
                
                latest_close = float(close_series.iloc[-1])
                prev_close = float(close_series.iloc[-2])
                latest_open = float(open_series.iloc[-1]) if len(open_series) > 0 else latest_close
                
                price_change_pct = ((latest_close - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                open_change_pct = ((latest_close - latest_open) / latest_open) * 100 if latest_open > 0 else 0
                
                latest_vol = float(vol_series.iloc[-1]) if len(vol_series) > 0 else 0
                trading_val = latest_close * latest_vol
                trading_val_oku = trading_val / 100000000  # Display as 億円相当 for consistency or leave as USD 10^8
                trading_val_str = f"{trading_val_oku:.1f}億"
                
                ma5_div = 0
                if len(close_series) >= 5:
                    ma5 = close_series.iloc[-5:].mean()
                    ma5_div = ((latest_close - ma5) / ma5) * 100 if ma5 > 0 else 0
                    
                bollinger = 0
                ma25_div = 0
                if len(close_series) >= 25:
                    ma25 = close_series.iloc[-25:].mean()
                    std25 = close_series.iloc[-25:].std()
                    if std25 > 0:
                        bollinger = (latest_close - ma25) / std25
                    if ma25 > 0:
                        ma25_div = ((latest_close - ma25) / ma25) * 100
                    sector_25ma_divs.append(ma25_div)
                
                ticker_obj = yf.Ticker(ticker)
                raw_comp_name = ticker_obj.info.get('shortName', ticker)
                comp_name = shorten_company_name(raw_comp_name)
                
                yahoo_url = f"https://finance.yahoo.co.jp/quote/{ticker}"
                
                if trading_val > 0:
                    heatmap_data.append({
                        "Sector": sector_name,
                        "Ticker": ticker,
                        "Name": comp_name,
                        "YahooURL": yahoo_url,
                        "Change": price_change_pct,
                        "ChangeStr": f"{price_change_pct:+.2f}%",
                        "OpenChange": open_change_pct,
                        "OpenChangeStr": f"{open_change_pct:+.2f}%",
                        "TradingVal": trading_val,
                        "TradingValStr": trading_val_str,
                        "Bollinger": bollinger,
                        "BollingerStr": f"{bollinger:+.2f}σ",
                        "5MADiv": ma5_div,
                        "5MADivStr": f"{ma5_div:+.2f}%",
                        "Size": trading_val,
                        "Price": latest_close
                    })
                
                sector_price_changes.append(price_change_pct)
                if price_change_pct > 0:
                    positive_count += 1
                
                if len(vol_series) >= 25:
                    avg_vol_25 = vol_series.iloc[-25:].mean()
                    if avg_vol_25 > 0:
                        sector_vol_ratios.append(latest_vol / avg_vol_25)
                        
            except Exception as e:
                pass
                
        if not sector_price_changes:
            continue
            
        avg_change = sum(sector_price_changes) / len(sector_price_changes)
        breadth = (positive_count / len(valid_tickers)) * 100
        avg_25ma_div = sum(sector_25ma_divs) / len(sector_25ma_divs) if len(sector_25ma_divs) > 0 else 0
        avg_vol_ratio = sum(sector_vol_ratios) / len(sector_vol_ratios) if len(sector_vol_ratios) > 0 else 0
        
        sector_heatmap_items = [item for item in heatmap_data if item["Sector"] == sector_name]
        sector_heatmap_items.sort(key=lambda x: x["Size"], reverse=True)
        top_3_names = [item["Ticker"] for item in sector_heatmap_items[:3]]
        rep_str = ", ".join(top_3_names) if top_3_names else "-"
        
        base_score = 50 + (avg_change * 10)  
        breadth_adj = (breadth - 50) * 0.4   
        score = int(max(0, min(100, base_score + breadth_adj)))
        
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
            "構成銘柄数": len(valid_tickers),
            "スコア": score,
            "騰落率": avg_change,
            "出来高倍率": avg_vol_ratio,
            "25MA乖離": avg_25ma_div,
            "波及度": int(breadth)
        })
        
    df_sectors = pd.DataFrame(sector_results)
    if not df_sectors.empty:
        df_sectors = df_sectors.sort_values(by="スコア", ascending=False)
        
    df_heatmap = pd.DataFrame(heatmap_data)
        
    return df_sectors, df_heatmap


def fetch_us_intraday_replay_data():
    """Fetches US intraday data for replay animation."""
    all_tickers = []
    for t_list in SECTOR_DICT.values():
        all_tickers.extend(t_list)
    all_tickers = list(set(all_tickers))
    
    try:
        data = yf.download(all_tickers, period="5d", interval="15m", progress=False)
    except Exception:
        return [], []
        
    frames = []
    times = []
    
    if 'Close' not in data.columns:
        return [], []
        
    close_data = data['Close']
    
    dates = pd.Series(close_data.index.date).unique()
    if len(dates) == 0:
        return [], []
    
    last_date = dates[-1]
    last_day_mask = close_data.index.date == last_date
    intraday_indices = close_data.index[last_day_mask]
    prev_indices = close_data.index[~last_day_mask]
    
    if len(intraday_indices) == 0:
        return [], []
        
    for ts in intraday_indices:
        frame_data = []
        for sector_name, tickers in SECTOR_DICT.items():
            valid_tickers = [t for t in tickers if t in close_data.columns]
            
            for ticker in valid_tickers:
                try:
                    ticker_curr_val = close_data[ticker].loc[ts]
                    if pd.isna(ticker_curr_val):
                        continue
                        
                    # Find previous close
                    prev_close = None
                    if len(prev_indices) > 0:
                        ticker_prev_vals = close_data[ticker].loc[prev_indices].dropna()
                        if len(ticker_prev_vals) > 0:
                            prev_close = ticker_prev_vals.iloc[-1]
                    
                    if prev_close is None:
                        first_ts = intraday_indices[0]
                        prev_close = close_data[ticker].loc[first_ts]
                        
                    if prev_close and prev_close > 0:
                        change = ((ticker_curr_val - prev_close) / prev_close) * 100
                    else:
                        change = 0
                        
                    # Note: We skip fetching ticker.info here for speed in intraday loop, just use ticker
                    # or an abbreviated ticker if needed. Let's just use ticker for the replay animation to avoid API spam.
                    comp_name = ticker
                    
                    frame_data.append({
                        "Sector": sector_name,
                        "Ticker": ticker,
                        "Name": comp_name,
                        "Change": float(change),
                        "ChangeStr": f"{change:+.2f}%",
                        "Size": 1.0, 
                        "Price": float(ticker_curr_val)
                    })
                except Exception:
                    pass
        
        df_frame = pd.DataFrame(frame_data)
        if not df_frame.empty:
            frames.append(df_frame)
            times.append(ts.strftime("%H:%M (NY)"))

    if frames:
        last_frame = frames[-1].copy()
        ticker_sizes = {}
        for _, row in last_frame.iterrows():
            ticker_sizes[row["Ticker"]] = row["Price"] * 1000 
            
        for i, df in enumerate(frames):
            df['Size'] = df['Ticker'].map(ticker_sizes).fillna(1.0)
            frames[i] = df

    return frames, times

if __name__ == "__main__":
    df_s, df_h = fetch_us_sector_metrics()
    print("Sectors:", len(df_s))
    print("Heatmap:", len(df_h))
