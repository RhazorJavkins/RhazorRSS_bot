import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf

# 1. Konfigurasi Keamanan (GitHub Secrets) [cite: 179, 757, 789]
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_report(pesan):
    """Mengirim pesan ke Telegram menggunakan library requests[cite: 165, 743]."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Gagal mengirim laporan: {e}")

def get_ihsg_report():
    # 2. Persiapan Daftar Saham dari CSV [cite: 814, 829, 881]
    try:
        df_list = pd.read_csv('list_saham.csv')
        list_saham = df_list['Ticker'].tolist()
    except FileNotFoundError:
        print("Error: File 'list_saham.csv' tidak ditemukan di repositori.")
        return

    # 3. Download Data Massal (Harga & Volume) [cite: 573, 585, 712]
    # Menggunakan threading agar proses 900+ saham selesai dalam hitungan menit [cite: 188, 629, 751]
    data = yf.download(list_saham, period="60d", threads=True, group_by='column')
    
    if data.empty:
        print("Gagal mengambil data dari Yahoo Finance.")
        return

    adj_close = data['Adj Close']
    volume = data['Volume']

    # --- ANALISIS 1: 5 Saham Volume Terbanyak (Rata-rata 1 Bulan) [cite: 713, 864] ---
    avg_vol = volume.tail(20).mean().sort_values(ascending=False).head(5)

    # --- ANALISIS 2: 5 Saham Kenaikan Tertinggi (Daily Log Return) [cite: 639, 754, 865] ---
    # Log return dihitung secara vektorisasi menggunakan ln(Pt / Pt-1) [cite: 51, 943, 1082]
    log_returns = np.log(adj_close / adj_close.shift(1))
    top_gainers = log_returns.iloc[-1].sort_values(ascending=False).head(5)

    # --- ANALISIS 3: Strategi MA 20 (Trending Up & Approaching) [cite: 651, 855, 867] ---
    ma20 = adj_close.rolling(window=20).mean()
    
    # Syarat A: MA 20 naik selama 3 hari terakhir [cite: 866]
    ma_trending_up = (ma20.iloc[-1] > ma20.iloc[-2]) & (ma20.iloc[-2] > ma20.iloc[-3])
    
    # Syarat B: Harga mendekati MA 20 (Jarak absolut menyusut) [cite: 665, 867]
    dist_pct = ((adj_close - ma20) / ma20) * 100
    approaching_ma = dist_pct.abs().iloc[-1] < dist_pct.abs().iloc[-2]
    
    ma_signals = adj_close.columns[ma_trending_up & approaching_ma][:5]

    # 4. Format Pesan Telegram [cite: 857]
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
