import pandas as pd
import requests
import io
import ssl
import urllib.request

def download_jpx_sectors():
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    try:
        # ignore verif
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx) as response:
            content = response.read()
            
        df = pd.read_excel(io.BytesIO(content))
        df = df[['コード', '銘柄名', '33業種区分']]
        df = df[df['33業種区分'] != '-']
        df.to_csv("jpx_sectors.csv", index=False)
        print(f"Saved {len(df)} tickers to jpx_sectors.csv")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_jpx_sectors()
