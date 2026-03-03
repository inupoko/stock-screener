import yfinance as yf
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
# Rate limiting and general config
DELAY_BETWEEN_REQUESTS = 0.5
MAX_RETRIES = 3

def fetch_nikkei_225_tickers():
    """
    Returns a static list of 100 prominent Nikkei 225 tickers.
    (Due to Wikipedia scraping prevention on cloud environments, 
    a robust static list is used instead).
    """
    # Top 100 prominent Nikkei 225 companies (Trading value & Market cap)
    tickers = [
        "7203.T", "8306.T", "6861.T", "6758.T", "8035.T", "9984.T", "9983.T", "6501.T", "8058.T", "9432.T",
        "4063.T", "8316.T", "8001.T", "7974.T", "4568.T", "9433.T", "8766.T", "6098.T", "6902.T", "4502.T",
        "8411.T", "7267.T", "7741.T", "8031.T", "6981.T", "4519.T", "8053.T", "4901.T", "6273.T", "6594.T",
        "6954.T", "6367.T", "4503.T", "6702.T", "7751.T", "5108.T", "8591.T", "4543.T", "8725.T", "1925.T",
        "9022.T", "6301.T", "4452.T", "9735.T", "6752.T", "7269.T", "6920.T", "4911.T", "8002.T", "2502.T",
        "5401.T", "7201.T", "2914.T", "6503.T", "1928.T", "6326.T", "3382.T", "5020.T", "6869.T", "8604.T",
        "4528.T", "9020.T", "9101.T", "4661.T", "6971.T", "8801.T", "9434.T", "1332.T", "1605.T", "1721.T",
        "1801.T", "1802.T", "1803.T", "1812.T", "1963.T", "8802.T", "2413.T", "2503.T", "2531.T", "2768.T",
        "2801.T", "2802.T", "3099.T", "3289.T", "3401.T", "3402.T", "3405.T", "3407.T", "3861.T", "4005.T",
        "4021.T", "4042.T", "4183.T", "4188.T", "4507.T", "4704.T", "4912.T", "5201.T", "5332.T", "5411.T"
    ]
    return tickers

def fetch_stock_data(ticker_symbol, lookback_days="6mo"):
    """
    Fetches historical and fundamental data for a given ticker using yfinance.
    Calculates required technical indicators.
    """
    for attempt in range(MAX_RETRIES):
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=lookback_days)
            
            if hist.empty:
                return None
            
            # Fundamentals
            info = ticker.info
            
            # Technicals (using pure pandas to avoid pandas_ta/numba python 3.14 issues)
            # 5MA Deviation
            hist['5MA'] = hist['Close'].rolling(window=5).mean()
            hist['5MA_Dev_%'] = ((hist['Close'] - hist['5MA']) / hist['5MA']) * 100
            
            # Bollinger Bands (20, 2)
            hist['20MA'] = hist['Close'].rolling(window=20).mean()
            hist['20STD'] = hist['Close'].rolling(window=20).std()
            hist['BB_Upper'] = hist['20MA'] + (hist['20STD'] * 2)
            hist['BB_Lower'] = hist['20MA'] - (hist['20STD'] * 2)

            # RSI (14)
            delta = hist['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            hist['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = hist['Close'].ewm(span=12, adjust=False).mean()
            ema_26 = hist['Close'].ewm(span=26, adjust=False).mean()
            hist['MACD'] = ema_12 - ema_26
            hist['MACD_Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
                 
            # 寄り付きからの騰落率 (Daily returns from Open)
            hist['Open_to_Close_Return_%'] = ((hist['Close'] - hist['Open']) / hist['Open']) * 100
            
            # 売買代金 (Trading Value = Volume * Close Price, approximation)
            hist['Trading_Value'] = hist['Volume'] * hist['Close']

            # Get the latest row for our screener
            latest_data = hist.iloc[-1]
            
            # Compile the result dictionary
            result = {
                'Ticker': ticker_symbol.replace('.T', ''),
                'Name': info.get('longName', info.get('shortName', 'N/A')),
                'Price': latest_data['Close'],
                # Fundamentals
                'PER': info.get('trailingPE', None),
                'PBR': info.get('priceToBook', None),
                'MarketCap': info.get('marketCap', None),
                'ROE': info.get('returnOnEquity', None),
                'DividendYield_%': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else None,
                # Technicals
                '5MA_Dev_%': latest_data.get('5MA_Dev_%', None),
                'BB_Upper': latest_data.get('BB_Upper', None),
                'BB_Lower': latest_data.get('BB_Lower', None),
                'RSI': latest_data.get('RSI', None),
                'MACD': latest_data.get('MACD', None),
                'Open_to_Close_Return_%': latest_data.get('Open_to_Close_Return_%', None),
                'Volume': latest_data['Volume'],
                'Trading_Value': latest_data.get('Trading_Value', None),
            }
            return result
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429: # Rate limit
                time.sleep((attempt + 1) * 2) # Exponential backoff
            else:
                 return None
        except Exception as e:
            print(f"Error fetching data for {ticker_symbol}: {e}")
            return None
            
        finally:
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    return None

def get_screener_data(tickers=None):
    """
    Main function to orchestrate downloading data for multiple tickers.
    """
    if tickers is None:
        tickers = fetch_nikkei_225_tickers()
    
    # Now fetching all tickers (e.g. 225) instead of a small subset
    data_list = []
    print(f"Fetching data for {len(tickers)} tickers...")
    
    for i, t in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Processing {t}...")
        data = fetch_stock_data(t)
        if data:
            data_list.append(data)
            
    df = pd.DataFrame(data_list)
    return df

if __name__ == "__main__":
    # Test the data loader
    print("Testing DataLoader...")
    df = get_screener_data()
    print("\nSample Data:")
    print(df.head())
    df.to_csv('sample_screener_data.csv', index=False)
    print("\nSaved sample to sample_screener_data.csv")
