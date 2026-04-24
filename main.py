import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf

# 1. Konfigurasi Keamanan (GitHub Secrets)
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_report(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

def get_ihsg_report():
    # 2. Ambil List Saham
    try:
        df_list = pd.read_csv('list_saham.csv')
        list_saham = df_list['Ticker'].tolist()
    except Exception:
        print("File list_saham.csv tidak ditemukan!")
        return

    # 3. Download Data (1 hari)
    data = yf.download(list_saham, period="1d", threads=True, group_by='column')
    adj_close = data['Adj Close']
    volume = data['Volume']

    # --- ANALISIS 1: Top 5 Volume (Bersihkan NaN) ---
    # Gunakan .dropna() agar saham tidak aktif tidak muncul
    avg_vol = volume.tail(20).mean().dropna().sort_values(ascending=False).head(5)

    # --- ANALISIS 2: Top 5 Gainers (Bersihkan NaN) ---
    log_returns = np.log(adj_close / adj_close.shift(1))
    # Ambil baris terakhir, buang NaN, lalu urutkan
    top_gainers = log_returns.iloc[-1].dropna().sort_values(ascending=False).head(5)

    # --- ANALISIS 3: Strategi MA 20 ---
    ma20 = adj_close.rolling(window=20).mean()
    ma_trending_up = (ma20.iloc[-1] > ma20.iloc[-2]) & (ma20.iloc[-2] > ma20.iloc[-3])
    dist_pct = ((adj_close - ma20) / ma20) * 100
    approaching_ma = dist_pct.abs().iloc[-1] < dist_pct.abs().iloc[-2]
    
    # Ambil ticker yang memenuhi syarat dan tidak NaN
    ma_signals = adj_close.columns[ma_trending_up & approaching_ma].dropna()[:5]

    # 4. Format Pesan
    report = "🚀 *LAPORAN HARIAN IHSG*\n\n"
    
    report += "📊 *Top 5 Volume (Avg 1d):*\n"
    for ticker, vol in avg_vol.items():
        report += f"- {ticker}: {vol:,.0f}\n"
    
    report += "\n📈 *Top 5 Gainers (Log Return):*\n"
    for ticker, ret in top_gainers.items():
        report += f"- {ticker}: {ret*100:.2f}%\n"
    
    report += "\n🎯 *Sinyal MA 20 (Trending Up & Approaching):*\n"
    if not ma_signals.empty:
        for ticker in ma_signals:
            report += f"- {ticker}\n"
    else:
        report += "- Tidak ada sinyal hari ini.\n"

    send_report(report)

if __name__ == "__main__":
    get_ihsg_report()
