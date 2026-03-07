import yfinance as yf
import pandas as pd
import json
from datetime import datetime
from datetime import time as dt_time
import pytz

def get_last_update_str(last_trading_date):
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    open_time = dt_time(9, 0)
    close_time = dt_time(15, 30)
    
    if last_trading_date == now.date() and open_time <= now.time() <= close_time:
        return now.strftime("%Y/%m/%d %H:%M")
    else:
        return last_trading_date.strftime("%Y/%m/%d 15:30")

def load_name_mapping():
    try:
        df = pd.read_csv("jpx_sectors.csv")
        df['コード'] = df['コード'].astype(str)
        mapping = dict(zip(df['コード'], df['銘柄名']))
        return mapping
    except Exception as e:
        print(f"Error loading JPX names: {e}")
        return {}

def shorten_company_name(name: str) -> str:
    """Removes common corporate suffixes/prefixes and limits length for heatmap display."""
    remove_words = ["株式会社", "ホールディングス", "フィナンシャルグループ", "フィナンシャル・グループ", "ＨＤ", "HD", "（株）", "(株)", "(?)", "(？)"]
    short_name = name
    for word in remove_words:
        short_name = short_name.replace(word, "")
    
    # Strip whitespace
    short_name = short_name.strip()
    
    # Specific edge cases like "FOOD & LIFE COMPANIES"
    if "FOOD &" in short_name:
        short_name = "FOOD & LIFE"
        
    # Hardcap length for very long names
    if len(short_name) > 8:
        short_name = short_name[:8] + "…"
        
    return short_name

def fetch_sector_metrics_top500():
    try:
        with open('top500_sectors.json', 'r', encoding='utf-8') as f:
            sector_dict = json.load(f)
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), ""
        
    all_tickers = []
    for t_list in sector_dict.values():
        all_tickers.extend(t_list)
        
    all_tickers = list(set(all_tickers))
    
    try:
        data = yf.download(all_tickers, period="2mo", progress=False)
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), ""
        
    if data.empty or 'Close' not in data.columns:
        return pd.DataFrame(), pd.DataFrame(), ""
        
    last_trading_date = pd.to_datetime(data.index[-1]).date()
    update_time_str = get_last_update_str(last_trading_date)
    
    name_map = load_name_mapping()
    sector_results = []
    heatmap_data = []
    
    for sector_name, tickers in sector_dict.items():
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
                trading_val_oku = trading_val / 100000000
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
                
                ticker_code = ticker.replace('.T', '')
                raw_comp_name = name_map.get(ticker_code, ticker_code)
                comp_name = shorten_company_name(raw_comp_name)
                
                yahoo_url = f"https://finance.yahoo.co.jp/quote/{ticker}"
                
                if trading_val > 0:
                    heatmap_data.append({
                        "Sector": sector_name,
                        "Ticker": ticker_code,
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
        top_3_names = [item["Name"] for item in sector_heatmap_items[:3]]
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
        
    return df_sectors, df_heatmap, update_time_str


def fetch_intraday_5m_data(ticker):
    """
    Fetches intraday 5-minute data for a specific ticker to display a candlestick chart.
    """
    try:
        data = yf.download(ticker, period="1d", interval="5m", progress=False)
        if data.empty:
            return pd.DataFrame()
            
        # yf.download with single ticker might return multi-index columns in some pandas versions,
        # but usually it's single index if only one ticker is requested.
        # Let's clean it up to ensure flat columns: Open, High, Low, Close, Volume
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        
        # Ensure we have the required columns
        req_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in req_cols:
            if col not in data.columns:
                return pd.DataFrame()
                
        # Format the index to JST
        if pd.api.types.is_datetime64tz_dtype(data.index):
            # It has timezone, convert to Asia/Tokyo
            data.index = data.index.tz_convert('Asia/Tokyo')
        else:
            # It's naive, localize as UTC then convert to Asia/Tokyo (yfinance usually returns UTC naive or tz-aware)
            # Actually yf returns naive timezone in local time of the exchange usually, or tz-aware for 5m.
            # Safe bet is tz_localize None then tz_localize exchange time.
            try:
                data.index = data.index.tz_localize('Asia/Tokyo')
            except TypeError:
                # Already tz-aware
                data.index = data.index.tz_convert('Asia/Tokyo')
                
        df = data[req_cols].copy()
        df.reset_index(inplace=True)
        # Rename the datetime column to 'Datetime'
        df.rename(columns={df.columns[0]: 'Datetime'}, inplace=True)
        
        return df
        
    except Exception as e:
        print(f"Error fetching 5m data for {ticker}: {e}")
        return pd.DataFrame()

def fetch_intraday_replay_data():
    """
    Fetches intraday data and returns a list of DataFrames (frames) for heatmap animation.
    Uses '1d' period '15m' interval to be fast and lightweight.
    Returns:
        frames (list of pd.DataFrame), times (list of str HH:MM)
    """
    try:
        with open('top500_sectors.json', 'r', encoding='utf-8') as f:
            sector_dict = json.load(f)
    except Exception:
        return [], []
        
    all_tickers = []
    for t_list in sector_dict.values():
        all_tickers.extend(t_list)
    all_tickers = list(set(all_tickers))
    name_map = load_name_mapping()
    
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
        for sector_name, tickers in sector_dict.items():
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
                        
                    ticker_code = ticker.replace('.T', '')
                    raw_comp_name = name_map.get(ticker_code, ticker_code)
                    comp_name = shorten_company_name(raw_comp_name)
                    
                    frame_data.append({
                        "Sector": sector_name,
                        "Ticker": ticker_code,
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
            
            # Format time adjusting for timezone cleanly
            times.append(ts.strftime("%H:%M"))

    # To keep box sizes perfectly stable in the animation, we calculate a single Size score for each ticker based on the last frame
    # and apply it to all frames.
    if frames:
        last_frame = frames[-1].copy()
        ticker_sizes = {}
        
        # approximate trading value from final frame price just to get a stable size distribution
        for _, row in last_frame.iterrows():
            ticker_sizes[row["Ticker"]] = row["Price"] * 1000  # constant volume mock for size
            
        for i, df in enumerate(frames):
            df['Size'] = df['Ticker'].map(ticker_sizes).fillna(1.0)
            frames[i] = df

    return frames, times
