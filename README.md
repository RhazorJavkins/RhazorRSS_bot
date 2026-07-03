# Analisis Saham IDX Harian ke Telegram

Script Python yang mengambil data harga & volume saham IDX dari daftar di
`list_saham.csv`, lalu mengirim ringkasan (5 terbaik, 5 terburuk, 5 volume
terbanyak, 5 volume tersedikit) otomatis ke Telegram setiap hari lewat
GitHub Actions.

## 1. Buat Bot Telegram

1. Buka Telegram, chat ke **@BotFather**
2. Ketik `/newbot`, ikuti instruksinya (kasih nama & username bot)
3. BotFather akan memberi **Bot Token**, contoh:
   `123456789:AAExampleTokenXXXXXXXXXXXXXXXXXXXXX`
4. Simpan token ini, jangan dibagikan ke siapa pun

## 2. Dapatkan Chat ID kamu

1. Kirim pesan apa saja ke bot yang baru dibuat (chat langsung ke bot-nya)
2. Buka browser, akses:
   `https://api.telegram.org/bot<TOKEN_BOT_KAMU>/getUpdates`
3. Cari nilai `"chat":{"id": ...}` di hasil JSON — angka itu adalah **Chat ID** kamu

   Kalau mau kirim ke grup, tambahkan bot ke grup tersebut, kirim pesan di
   grup, lalu ulangi langkah di atas — chat ID grup biasanya berupa angka negatif.

## 3. Upload folder ini ke GitHub

1. Buat repository baru di GitHub (bisa private)
2. Upload semua file di folder ini (termasuk folder `.github/workflows/`)
   beserta file `list_saham.csv` kamu
3. Struktur folder harus seperti ini:
   ```
   nama-repo/
   ├── .github/
   │   └── workflows/
   │       └── daily-saham.yml
   ├── analisis_saham_telegram.py
   ├── requirements.txt
   ├── list_saham.csv
   └── README.md
   ```

## 4. Simpan Token & Chat ID sebagai GitHub Secrets

1. Di repository GitHub, buka **Settings** → **Secrets and variables** → **Actions**
2. Klik **New repository secret**, buat 2 secret:
   - Name: `TELEGRAM_BOT_TOKEN` → Value: token dari BotFather
   - Name: `TELEGRAM_CHAT_ID` → Value: chat ID kamu
3. Secret ini aman, tidak akan terlihat oleh siapa pun termasuk di log Actions

## 5. Jalankan / Uji coba

- Otomatis: workflow akan jalan sendiri setiap **Senin–Jumat jam 16:15 WIB**
  (bisa diubah di file `.github/workflows/daily-saham.yml`, bagian `cron`)
- Manual: buka tab **Actions** di GitHub repo kamu → pilih workflow
  **"Analisis Saham Harian ke Telegram"** → klik **Run workflow**

## Catatan

- Waktu di GitHub Actions cron pakai **UTC**, bukan WIB. WIB = UTC+7.
  Jadi kalau ingin jalan jam 16:00 WIB, atur cron ke `09:00 UTC`.
- Proses mengambil ratusan saham bisa memakan waktu beberapa menit;
  GitHub Actions gratis punya limit 2.000 menit/bulan untuk akun free,
  biasanya lebih dari cukup untuk kebutuhan ini.
- Volume saham yang bernilai 0 (suspend/tidak ada transaksi) otomatis
  dikeluarkan dari daftar "volume tersedikit", supaya hasilnya tetap saham
  yang benar-benar aktif diperdagangkan.
- Ini alat bantu analisis, bukan rekomendasi keputusan trading.
