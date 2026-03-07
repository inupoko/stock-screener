with open("jp_sector_app.py", "r") as f:
    code = f.read()

code = code.replace("jp_sector_data_v2", "us_sector_data_v2")
code = code.replace("fetch_sector_metrics_top500", "fetch_us_sector_metrics")
code = code.replace("fetch_intraday_replay_data", "fetch_us_intraday_replay_data")
code = code.replace("日本", "米国")
code = code.replace("🇯🇵", "🇺🇸")
code = code.replace("33業種", "11業種")
code = code.replace("Asia/Tokyo", "US/Eastern")
code = code.replace("time(9, 0)", "time(9, 30)")
code = code.replace("time(15, 30)", "time(16, 0)")
code = code.replace("価格: ¥", "価格: $")
code = code.replace("売買代金Oku", "売買代金Mil")

with open("us_sector_app.py", "w") as f:
    f.write(code)
