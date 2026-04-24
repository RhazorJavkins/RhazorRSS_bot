import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf

# 1. Konfigurasi Keamanan (GitHub Secrets)
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_report(pesan):
    """Mengirim pesan ke Telegram menggunakan library requests."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Gagal mengirim laporan ke Telegram: {e}")

def get_ihsg_report():
    # 2. Persiapan Daftar Saham dari CSV
    try:
        # Skrip ini menggabungkan pembacaan dari file CSV agar lebih efisien 
        df_list = pd.read_csv('list_saham.csv')
        list_saham = df_list['Ticker'].tolist()
    except FileNotFoundError:
        print("Error: File 'list_saham.csv' tidak ditemukan di repositori.")
        return

    # 3. Download Data Massal menggunakan threading [cite: 728, 767]
    data = yf.download(list_saham, period="60d", threads=True, group_by='column')
    
    if data.empty:
        print("Gagal mengambil data dari Yahoo Finance.")
        return

    # Gunakan kolom Adj Close untuk akurasi riset [cite: 886]
    adj_close = data['Adj Close']
    volume = data['Volume']

    # --- ANALISIS 1: 5 Saham Volume Terbanyak (Rata-rata 1 Bulan) ---
    avg_vol = volume.tail(20).mean().sort_values(ascending=False).head(5)

    # --- ANALISIS 2: 5 Saham Kenaikan Tertinggi (Daily Log Return) ---
    # Log return dihitung secara vektorisasi agar cepat [cite: 881]
    log_returns = np.log(adj_close / adj_close.shift(1))
    top_gainers = log_returns.iloc[-1].sort_values(ascending=False).head(5)

    # --- ANALISIS 3: Strategi MA 20 (Trending Up & Approaching) ---
    ma20 = adj_close.rolling(window=20).mean()
    
    # Syarat A: MA 20 naik selama 3 hari terakhir [cite: 882]
    ma_trending_up = (ma20.iloc[-1] > ma20.iloc[-2]) & (ma20.iloc[-2] > ma20.iloc[-3])
    
    # Syarat B: Harga mendekati MA 20 [cite: 883]
    dist_pct = ((adj_close - ma20) / ma20) * 100
    approaching_ma = dist_pct.abs().iloc[-1] < dist_pct.abs().iloc[-2]
    
    ma_signals = adj_close.columns[ma_trending_up & approaching_ma][:5]

    # 4. Format Pesan Telegram
    report = "🚀 *LAPORAN HARIAN IHSG*\n\n"
    
    report += "📊 *Top 5 Volume (Avg 1Mo):*\n"
    for ticker, vol in avg_vol.items():
        report += f"- {ticker}: {vol:,.0f}\n"
    
    report += "\n📈 *Top 5 Gainers (Daily Log Return):*\n"
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
