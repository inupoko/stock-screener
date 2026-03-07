import pandas as pd
from data_loader import fetch_nikkei_225_tickers
import json

def generate_dict():
    df = pd.read_csv("jpx_sectors.csv")
    df['コード文字列'] = df['コード'].astype(str)
    
    tickers = fetch_nikkei_225_tickers()
    
    # We want base tickers in string format to match 
    base_codes = [t.replace('.T', '') for t in tickers]
    
    df_base = df[df['コード文字列'].isin(base_codes)].copy()
    
    sector_dict = {}
    for _, row in df_base.iterrows():
        code = str(row['コード文字列']) + '.T'
        sector = row['33業種区分']
        if sector not in sector_dict:
            sector_dict[sector] = []
        sector_dict[sector].append(code)
        
    print(f"Total sectors: {len(sector_dict)}")
    total_stocks = sum(len(v) for v in sector_dict.values())
    print(f"Total stocks mapped: {total_stocks}")
    
    with open('top500_sectors.json', 'w', encoding='utf-8') as f:
        json.dump(sector_dict, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    generate_dict()
