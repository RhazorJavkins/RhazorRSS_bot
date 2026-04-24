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
    requests.post(url, data=payload)

def get_ihsg_report():
    # Mengambil list saham (pastikan list all_saham sudah terdefinisi/di-scrap)
    # Sebagai contoh, kita gunakan list yang sudah dibersihkan dengan akhiran .JK
    # list_saham = [...] 

    # 2. Download Data Massal (Harga & Volume)
    # Ambil periode 60 hari agar perhitungan MA 20 dan tren 3 hari akurat
    data = yf.download(list_saham, period="60d", threads=True, group_by='column')
    adj_close = data['Adj Close']
    volume = data['Volume']

    # --- ANALISIS 1: 5 Saham Volume Terbanyak (Rata-rata 1 Bulan) ---
    avg_vol = volume.tail(20).mean().sort_values(ascending=False).head(5) [cite: 154]

    # --- ANALISIS 2: 5 Saham Kenaikan Tertinggi (Daily Log Return) ---
    # Log return dihitung menggunakan ln(Pt / Pt-1) [cite: 277]
    log_returns = np.log(adj_close / adj_close.shift(1)) [cite: 384]
    top_gainers = log_returns.iloc[-1].sort_values(ascending=False).head(5)

    # --- ANALISIS 3: Strategi MA 20 (Mendekati MA & Tren Naik 3 Hari) ---
    ma20 = adj_close.rolling(window=20).mean() [cite: 94]
    
    # Syarat A: MA 20 naik selama 3 hari terakhir (t > t-1 > t-2)
    ma_trending_up = (ma20.iloc[-1] > ma20.iloc[-2]) & (ma20.iloc[-2] > ma20.iloc[-3])
    
    # Syarat B: Harga mendekati MA 20 (Jarak absolut hari ini < kemarin) [cite: 106, 107]
    dist_pct = ((adj_close - ma20) / ma20) * 100
    approaching_ma = dist_pct.abs().iloc[-1] < dist_pct.abs().iloc[-2]
    
    # Gabungkan filter dan ambil 5 saham
    ma_signals = adj_close.columns[ma_trending_up & approaching_ma][:5]

    # 3. Format Pesan Telegram
    report = "🚀 *LAPORAN HARIAN IHSG*\n\n"
    
    report += "📊 *Top 5 Volume (Avg 1Mo):*\n"
    for ticker, vol in avg_vol.items():
        report += f"- {ticker}: {vol:,.0f}\n"
    
    report += "\n📈 *Top 5 Gainers (Daily Log Return):*\n"
    for ticker, ret in top_gainers.items():
        report += f"- {ticker}: {ret*100:.2f}%\n"
    
    report += "\n🎯 *Sinyal MA 20 (Trending Up & Approaching):*\n"
    if len(ma_signals) > 0:
        for ticker in ma_signals:
            report += f"- {ticker}\n"
    else:
        report += "- Tidak ada sinyal hari ini.\n"

    send_report(report)

if __name__ == "__main__":
    get_ihsg_report()
