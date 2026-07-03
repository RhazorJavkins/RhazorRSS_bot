"""
Script untuk mengambil data harga saham IDX dari daftar kode saham di file CSV,
menyimpan seluruh hasil ke CSV baru, lalu MENGIRIM ringkasan ke Telegram:
- 5 saham dengan kenaikan harga terbaik
- 5 saham dengan penurunan harga terburuk
- 5 saham dengan volume terbanyak
- 5 saham dengan volume tersedikit (hanya yang volume-nya > 0, bukan saham suspend/tidak aktif)

Didesain untuk dijalankan otomatis setiap hari lewat GitHub Actions.

Install dulu library yang dibutuhkan:
    pip install yfinance pandas requests
"""

import os
import yfinance as yf
import pandas as pd
import time
import requests


FILE_INPUT = "list_saham.csv"             # file berisi daftar kode saham (kolom: Ticker)
FILE_OUTPUT = "hasil_analisis_saham.csv"  # file hasil analisis akan disimpan di sini

# Kredensial Telegram diambil dari environment variable (JANGAN ditulis langsung di kode!)
# Saat pakai GitHub Actions, ini diisi lewat GitHub Secrets.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def baca_daftar_saham(file_csv):
    """
    Membaca daftar kode saham dari file CSV.
    Mendukung kode dengan atau tanpa akhiran '.JK'
    """
    df = pd.read_csv(file_csv)

    kolom_ticker = df.columns[0]
    daftar = df[kolom_ticker].dropna().astype(str).str.strip().tolist()

    daftar_final = []
    for kode in daftar:
        kode = kode.upper()
        if not kode.endswith(".JK"):
            kode = f"{kode}.JK"
        daftar_final.append(kode)

    return daftar_final


def ambil_data_satu_saham(ticker):
    """
    Mengambil data harga terakhir 1 saham (ticker sudah termasuk '.JK').
    Mengembalikan dict berisi info harga, atau None jika gagal/kosong.
    """
    kode_saham = ticker.replace(".JK", "")
    try:
        saham = yf.Ticker(ticker)
        data = saham.history(period="5d")

        if data.empty:
            return None

        hari_terakhir = data.iloc[-1]
        tanggal = data.index[-1].strftime("%Y-%m-%d")

        harga_buka = hari_terakhir["Open"]
        harga_tertinggi = hari_terakhir["High"]
        harga_terendah = hari_terakhir["Low"]
        harga_akhir = hari_terakhir["Close"]
        volume = hari_terakhir["Volume"]

        persen_perubahan = ((harga_akhir - harga_buka) / harga_buka) * 100 if harga_buka else None

        if len(data) >= 2:
            close_kemarin = data.iloc[-2]["Close"]
            persen_vs_kemarin = ((harga_akhir - close_kemarin) / close_kemarin) * 100
        else:
            persen_vs_kemarin = None

        return {
            "Kode": kode_saham,
            "Tanggal": tanggal,
            "Harga Buka": round(harga_buka, 2),
            "Harga Tertinggi": round(harga_tertinggi, 2),
            "Harga Terendah": round(harga_terendah, 2),
            "Harga Akhir": round(harga_akhir, 2),
            "Volume": int(volume),
            "Perubahan vs Buka (%)": round(persen_perubahan, 2) if persen_perubahan is not None else None,
            "Perubahan vs Kemarin (%)": round(persen_vs_kemarin, 2) if persen_vs_kemarin is not None else None,
        }

    except Exception:
        return None


def cek_banyak_saham(daftar_ticker, jeda_detik=0.3):
    """
    Mengambil data untuk semua saham dalam daftar.
    jeda_detik: jeda antar request agar tidak dianggap spam oleh Yahoo Finance
    """
    hasil = []
    gagal = []
    total = len(daftar_ticker)

    print(f"Mengambil data {total} saham dari '{FILE_INPUT}'...\n")

    for i, ticker in enumerate(daftar_ticker, start=1):
        kode = ticker.replace(".JK", "")
        if i % 10 == 0 or i == total:
            print(f"Progress: {i}/{total} saham diproses...")

        data = ambil_data_satu_saham(ticker)
        if data:
            hasil.append(data)
        else:
            gagal.append(kode)

        time.sleep(jeda_detik)

    print(f"\nSelesai. Berhasil: {len(hasil)} | Gagal/tidak ada data: {len(gagal)}")
    if gagal:
        print(f"Kode yang gagal diambil: {', '.join(gagal[:30])}" + (" ..." if len(gagal) > 30 else ""))

    return pd.DataFrame(hasil)


def ambil_ringkasan_harga(df, kolom_urutkan="Perubahan vs Kemarin (%)", top_n=5):
    """Mengembalikan (df_terbaik, df_terburuk) berdasarkan % perubahan harga."""
    df_valid = df.dropna(subset=[kolom_urutkan]).copy()

    if df_valid.empty:
        return None, None

    df_urut = df_valid.sort_values(by=kolom_urutkan, ascending=False)

    terbaik = df_urut.head(top_n)
    terburuk = df_urut.tail(top_n).sort_values(by=kolom_urutkan)

    return terbaik, terburuk


def ambil_ringkasan_volume(df, top_n=5):
    """
    Mengembalikan (df_volume_terbanyak, df_volume_tersedikit).
    PENTING: saham dengan volume 0 (suspend/tidak ada transaksi) DIKELUARKAN
    dari daftar volume tersedikit, supaya hasilnya tetap saham yang benar-benar
    aktif diperdagangkan tapi paling sepi peminat.
    """
    df_valid = df[df["Volume"] > 0].copy()  # <-- perbaikan: hanya volume > 0

    if df_valid.empty:
        return None, None

    df_urut = df_valid.sort_values(by="Volume", ascending=False)

    volume_terbanyak = df_urut.head(top_n)
    volume_tersedikit = df_urut.tail(top_n).sort_values(by="Volume")

    return volume_terbanyak, volume_tersedikit


def format_pesan_telegram(df, tanggal_analisis):
    """Menyusun teks ringkasan untuk dikirim ke Telegram (format Markdown)."""
    terbaik, terburuk = ambil_ringkasan_harga(df)
    vol_banyak, vol_sedikit = ambil_ringkasan_volume(df)

    baris = []
    baris.append(f"*📊 RINGKASAN SAHAM IDX — {tanggal_analisis}*")
    baris.append(f"_Total saham dianalisis: {len(df)}_")
    baris.append("")

    if terbaik is not None:
        baris.append("*🟢 5 SAHAM TERBAIK (% vs kemarin)*")
        for _, row in terbaik.iterrows():
            baris.append(f"`{row['Kode']:<6}` Rp{row['Harga Akhir']:>9,.0f}  {row['Perubahan vs Kemarin (%)']:+.2f}%")
        baris.append("")

    if terburuk is not None:
        baris.append("*🔴 5 SAHAM TERBURUK (% vs kemarin)*")
        for _, row in terburuk.iterrows():
            baris.append(f"`{row['Kode']:<6}` Rp{row['Harga Akhir']:>9,.0f}  {row['Perubahan vs Kemarin (%)']:+.2f}%")
        baris.append("")

    if vol_banyak is not None:
        baris.append("*📈 5 VOLUME TERBANYAK*")
        for _, row in vol_banyak.iterrows():
            baris.append(f"`{row['Kode']:<6}` Volume: {row['Volume']:,.0f}")
        baris.append("")

    if vol_sedikit is not None:
        baris.append("*📉 5 VOLUME TERSEDIKIT (tetap aktif, volume > 0)*")
        for _, row in vol_sedikit.iterrows():
            baris.append(f"`{row['Kode']:<6}` Volume: {row['Volume']:,.0f}")

    return "\n".join(baris)


def kirim_ke_telegram(pesan, token, chat_id):
    """Mengirim pesan teks ke Telegram lewat Bot API."""
    if not token or not chat_id:
        print("[!] TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diset, pesan tidak dikirim.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Telegram membatasi 4096 karakter per pesan; potong jika perlu
    MAKS_PANJANG = 4000
    potongan = [pesan[i:i + MAKS_PANJANG] for i in range(0, len(pesan), MAKS_PANJANG)]

    sukses = True
    for bagian in potongan:
        payload = {
            "chat_id": chat_id,
            "text": bagian,
            "parse_mode": "Markdown",
        }
        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"[!] Gagal mengirim pesan ke Telegram: {e}")
            sukses = False

    return sukses


if __name__ == "__main__":
    daftar_ticker = baca_daftar_saham(FILE_INPUT)
    df_hasil = cek_banyak_saham(daftar_ticker)

    if df_hasil.empty:
        print("Tidak ada data yang berhasil diambil.")
    else:
        df_hasil.to_csv(FILE_OUTPUT, index=False)
        print(f"\nData lengkap ({len(df_hasil)} saham) disimpan ke '{FILE_OUTPUT}'")

        tanggal_analisis = df_hasil["Tanggal"].mode()[0] if not df_hasil["Tanggal"].empty else "N/A"
        pesan = format_pesan_telegram(df_hasil, tanggal_analisis)

        print("\n" + "=" * 60)
        print("PESAN YANG AKAN DIKIRIM KE TELEGRAM:")
        print("=" * 60)
        print(pesan)

        berhasil_kirim = kirim_ke_telegram(pesan, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        if berhasil_kirim:
            print("\n✅ Pesan berhasil dikirim ke Telegram.")
        else:
            print("\n❌ Pesan gagal dikirim ke Telegram (cek token/chat_id/koneksi).")
