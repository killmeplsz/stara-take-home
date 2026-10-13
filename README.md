# STARA Mini — Customer → API → Database → Automation → AI → Web

Pesan pelanggan masuk lewat webhook (simulasi WhatsApp), disimpan ke database Supabase (PostgreSQL),
dibalas otomatis oleh AI, dan dipantau staf lewat halaman web sederhana.

## Teknologi dan alasannya
- **Python + Flask** — saya kuasai, kecil, dan mudah dijelaskan baris per baris.
- **PostgreSQL di Supabase (free tier)** — sesuai saran soal. Diakses langsung lewat driver `psycopg` dengan SQL biasa (tanpa ORM) agar setiap query jelas.
- **AI: Gemini, dengan mode mock** — dipilih lewat `AI_PROVIDER` di `.env`. Mode `mock` (balasan palsu berbasis kata kunci) berjalan tanpa API key.
- **HTML + CSS + JavaScript biasa** — tanpa build step.

## Menjalankan dari nol
Prasyarat: Python 3.10+ dan akun Supabase (gratis).

**1. Siapkan database Supabase**
1. Buat project baru di https://supabase.com dan simpan *database password* yang Anda buat.
2. Buka tombol **Connect** di project, pilih connection string **Session pooler**, lalu salin.
   (Direct connection hanya mendukung IPv6; Session pooler berjalan di jaringan IPv4 biasa.)
3. Tabel dibuat otomatis dari `schema.sql` saat aplikasi pertama kali dijalankan. Alternatif manual:
   **SQL Editor → New query →** tempel isi `schema.sql` **→ Run**.

**2. Jalankan aplikasi**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
# Edit .env: isi DATABASE_URL dengan connection string tadi (ganti [YOUR-PASSWORD]).
# Jika password mengandung karakter khusus (@ : / # ?), URL-encode (mis. @ menjadi %40).
python app.py
```
Buka http://localhost:8000. Untuk AI sungguhan: `AI_PROVIDER=gemini` dan isi `GEMINI_API_KEY` di `.env`.

## Endpoint
| Method & alamat | Fungsi | Status |
|---|---|---|
| `POST /customers` | Tambah pelanggan | 201, 400, 409 (telepon kembar) |
| `GET /customers?status=active` | Daftar (filter opsional) | 200, 400 |
| `GET /customers/{id}` | Satu pelanggan + riwayat pesan | 200, 404 |
| `PUT /customers/{id}` | Ubah data | 200, 400, 404, 409 |
| `DELETE /customers/{id}` | Hapus (pesannya ikut terhapus) | 200, 404 |
| `POST /webhook/incoming-message` | Terima pesan, balas dengan AI | 200, 400 |

```bash
curl -X POST http://localhost:8000/customers -H "Content-Type: application/json" \
  -d '{"name":"Budi Santoso","phone":"081234567890"}'
curl "http://localhost:8000/customers?status=active"
curl http://localhost:8000/customers/1
curl -X PUT http://localhost:8000/customers/1 -H "Content-Type: application/json" -d '{"status":"active"}'
curl -X DELETE http://localhost:8000/customers/1
curl -X POST http://localhost:8000/webhook/incoming-message -H "Content-Type: application/json" \
  -d '{"phone":"081234567890","name":"Budi Santoso","message":"Halo, saya mau tanya harga paket layanan"}'
```
`reply_source` pada respons webhook: `mock`, `gemini`, atau `fallback` (AI gagal, balasan cadangan dipakai).

## Catatan desain
- Pesan masuk **disimpan sebelum memanggil AI**. Jika AI gagal atau lambat (timeout 10 detik), pesan tetap aman dan pelanggan menerima balasan cadangan.
- Batas 3 kalimat dipaksa di kode, bukan hanya di prompt. Prompt ada di `prompts.py`.
- Telepon kembar ditolak dengan 409 (data valid tetapi bentrok dengan data yang ada).
- Query memakai placeholder `%s` (anti SQL injection); dashboard memakai `textContent` (anti XSS); rahasia hanya di `.env`.
- **Row Level Security (RLS)** diaktifkan tanpa policy pada kedua tabel, sehingga API publik Supabase (kunci `anon`) tidak bisa membaca/menulis. Backend terhubung langsung sebagai pemilik database sehingga tetap berfungsi.

## Belum selesai / akan diperbaiki
- Normalisasi format nomor telepon (`+62…` vs `08…`), paginasi, autentikasi API key.
- Koneksi dibuka per permintaan; untuk trafik tinggi perlu connection pool.
- Panggilan Gemini belum diuji dengan API key sungguhan; jalur mock dan fallback sudah diuji.
- Bonus (n8n, deploy, Docker, konteks percakapan, tes otomatis) belum dikerjakan.

## Penggunaan AI dalam pengerjaan
> **ISI SENDIRI SEBELUM DIKUMPULKAN — tulis dengan jujur.**
- Dibantu AI (Claude): kerangka awal kode, dashboard, draf README.
- Yang saya pelajari/ubah sendiri: _[isi sendiri]_
