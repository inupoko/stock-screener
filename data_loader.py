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
    Fetch the list of Nikkei 225 tickers from Wikipedia (or a similar stable source).
    Returns a list of strings in yfinance format (e.g., '7203.T').
    """
    try:
        url = 'https://en.wikipedia.org/wiki/Nikkei_225'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'wikitable', 'id': 'constituents'})
        
        tickers = []
        for row in table.find_all('tr')[1:]: # Skip header
             cols = row.find_all('td')
             if len(cols) > 1:
                ticker = cols[1].text.strip()
                tickers.append(f"{ticker}.T")
        return tickers
    except Exception as e:
        print(f"Error fetching Nikkei 225 tickers: {e}")
        # Fallback to a small sample for testing if fetching fails
        return ['7203.T', '9984.T', '6758.T', '8306.T', '8035.T']

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
