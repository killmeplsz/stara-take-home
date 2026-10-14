# STARA Take Home Test

## 1. Cara menjalankan proyek dari nol

**Prasyarat:** Python 3.10+, Git, dan akun [Supabase](https://supabase.com) (gratis).

1. **Ambil kode**

```bash
   git clone https://github.com/killmeplsz/stara-take-home
   cd <nama-folder-repository>
```

2. **Siapkan Supabase.** Buat project baru, lalu klik tombol **Connect** dan salin connection string
   **Session pooler** (bukan _Direct connection_, karena hanya mendukung IPv6 dan bisa _timeout_).
   Tabel dibuat otomatis dari `schema.sql` saat aplikasi pertama kali jalan.

3. **Buat virtual environment dan pasang dependensi**

```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1        # Windows PowerShell (macOS/Linux: source .venv/bin/activate)
   python -m pip install -r requirements.txt
```

4. **Atur `.env`**

```bash
   copy .env.example .env            # macOS/Linux: cp .env.example .env
```

Isi `DATABASE_URL` dengan connection string tadi. Awalannya harus `postgresql://`, dan karakter khusus pada
password harus di-URL-encode (misalnya `@` menjadi `%40`). Variabel lain boleh dibiarkan:

- `AI_PROVIDER` — `mock` (default, balasan palsu tanpa API key) atau `gemini`
- `GEMINI_API_KEY` — hanya diperlukan jika memakai `gemini`
- `GEMINI_MODEL`, `AI_TIMEOUT_SECONDS`, `PORT` — sudah punya nilai bawaan

Tulis komentar di baris sendiri, bukan di belakang nilai. `.env` berisi rahasia dan sudah ada di
`.gitignore`, jadi jangan di-commit.

5. **Jalankan**

```bash
   python app.py
```

Buka **http://localhost:8000**: tambah customer, klik namanya untuk melihat percakapan, lalu kirim pesan
lewat kotak _"Simulate an incoming WhatsApp message"_ untuk mencoba webhook.

6. **Jalankan pengujian (opsional).** Dengan server tetap berjalan, buka terminal kedua (venv aktif):

```bash
   python test_manual.py
```

Hasil yang benar: `Result: 34 passed, 0 failed`.

**Alternatif dengan Docker** (tetap perlu langkah 2 dan `.env` dari langkah 4):

```bash
docker compose up --build
```

Lalu buka http://localhost:8000. Untuk berhenti: `Ctrl+C`, kemudian `docker compose down`.

---

## 2. Teknologi yang dipilih dan alasannya

- **Python + Flask** — kecil dan eksplisit, sehingga setiap route dan validasi mudah dibaca dan dijelaskan.
- **PostgreSQL di Supabase** — sesuai saran soal. Aturan data (`UNIQUE`, `CHECK`, foreign key `ON DELETE CASCADE`)
  dijaga oleh database, bukan hanya oleh kode.
- **psycopg + SQL biasa, dengan connection pool** — tanpa ORM agar setiap query terlihat jelas (memakai
  placeholder `%s` untuk mencegah SQL injection). Pool dipakai karena database ada di server jauh, sehingga
  membuka koneksi baru di setiap request lambat.
- **Gemini + mode mock** — Gemini untuk balasan sungguhan; mode `mock` membuat proyek bisa dijalankan dan diuji
  tanpa API key.
- **HTML + CSS + JavaScript biasa** — halaman cukup sederhana, tanpa framework dan tanpa build step.
- **Docker + gunicorn** — opsional, agar bisa dijalankan tanpa memasang Python.

Keputusan desain penting:

- **Pesan masuk disimpan sebelum AI dipanggil.** Jika AI gagal atau lambat (ada timeout), pesan tidak hilang dan
  pelanggan tetap menerima balasan cadangan; webhook tetap mengembalikan 200.
- **Nomor telepon kembar → 409 Conflict**, karena datanya valid tetapi bentrok dengan data yang sudah ada.
- **Menghapus customer ikut menghapus pesannya** (`ON DELETE CASCADE`).
- **Keamanan dasar:** rahasia hanya di `.env`; halaman web memakai `textContent` (anti XSS); _Row Level Security_
  diaktifkan di kedua tabel agar API publik Supabase tidak bisa membaca data.

---

## 3. Daftar endpoint beserta contoh permintaan

Semua respons berformat JSON. Error berbentuk `{"error": "...", "details": [...]}`.

- `POST /customers` — tambah customer. Status: `201`, `400` (tidak valid), `409` (telepon kembar)
- `GET /customers` — daftar customer; filter opsional `?status=active`. Status: `200`, `400`
- `GET /customers/{id}` — satu customer beserta riwayat pesannya. Status: `200`, `404`
- `PUT /customers/{id}` — ubah data (field yang tidak dikirim tetap). Status: `200`, `400`, `404`, `409`
- `DELETE /customers/{id}` — hapus customer beserta pesannya. Status: `200`, `404`
- `POST /webhook/incoming-message` — terima pesan, simpan, balas dengan AI. Status: `200`, `400` (data tidak lengkap)

Status customer yang diizinkan: `lead` (default), `active`, `inactive`.

```bash
# Tambah customer
curl -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "Budi Santoso", "phone": "081234567890", "status": "lead"}'

# Daftar customer (opsional: ?status=active)
curl http://localhost:8000/customers

# Detail customer + riwayat pesan
curl http://localhost:8000/customers/1

# Ubah status
curl -X PUT http://localhost:8000/customers/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'

# Hapus customer
curl -X DELETE http://localhost:8000/customers/1

# Simulasi pesan WhatsApp masuk (customer dibuat otomatis jika belum ada)
curl -X POST http://localhost:8000/webhook/incoming-message \
  -H "Content-Type: application/json" \
  -d '{"phone": "081234567890", "name": "Budi Santoso", "message": "Halo, saya mau tanya harga paket layanan"}'
```

Respons webhook:

```json
{
  "customer_id": 1,
  "reply": "Terima kasih sudah menghubungi STARA. Tim kami akan segera mengirimkan rincian harga dan paket layanan kepada Anda.",
  "reply_source": "mock"
}
```

`reply_source` bernilai `mock`, `gemini`, atau `fallback` (AI gagal sehingga balasan cadangan dipakai).
Jika data webhook tidak lengkap, responsnya `400`, misalnya `{"error": "Incomplete data", "details": ["message is required"]}`.

Catatan PowerShell: tanda kutip JSON di `curl` sering rusak. Pakai `curl.exe` dengan tanda kutip yang di-escape,
atau cukup jalankan `python test_manual.py`.

---

## 4. Hal yang belum selesai atau akan saya perbaiki jika punya waktu lebih

- **Gemini belum terverifikasi berhasil.** Saat diuji, Gemini mengembalikan error kuota (`429`) dan server sibuk (`503`) di free tier. Yang sudah terbukti adalah jalur _fallback_-nya (webhook tetap 200 dan pesan tersimpan), sehingga `mock` dijadikan default.
- **Tidak ada autentikasi.** Siapa pun yang bisa menjangkau server dapat memanggil semua endpoint. Rencana: API key atau login, dan verifikasi tanda tangan webhook.
- **Nomor telepon belum dinormalisasi**: `081234567890` dan `+6281234567890` dianggap dua nomor berbeda.
- **AI hanya melihat pesan terakhir**, belum membaca beberapa pesan sebelumnya.
- **Webhook menunggu AI** (paling lama sekitar 30 detik). Sebaiknya diproses di latar belakang agar langsung membalas 200.
- **Belum ada** batas panjang pesan, paginasi `GET /customers`, dan penanganan dua webhook bersamaan dari nomor baru yang sama (bisa menghasilkan error 500).
- **Pengujian otomatis** (pytest) belum ada; `test_manual.py` harus dijalankan terhadap server yang sedang hidup.
- **Database di Sydney**, sedangkan pengguna di Indonesia; Singapura akan lebih cepat.
- **Deploy** ke hosting juga belum dikerjakan.

---

## 5. Penggunaan AI dalam pengerjaan

Saya memakai Claude dan ChatGPT, dan sebagian besar kode awal proyek ini ditulis dengan bantuannya.

**Dibantu AI**

- Kerangka dan kode awal: `schema.sql`, `app.py` (CRUD, validasi, webhook), `ai.py`, `prompts.py`, halaman web, `test_manual.py`, dan file Docker.
- Mencari solusi dari beberapa masalah selama pengerjaan
- Membantu dalam testing otomatis

**Dikerjakan, diputuskan, atau diperbaiki sendiri**

- Melakukan setup untuk Supabase dan Docker
- Memilih Supabase, dan membuat serta mengatur project-nya: memakai _Session pooler_ setelah _direct connection_timeout_, serta memperbaiki `.env` (awalan `postgresql+psycopg://` tidak cocok dengan driver yang dipakai).
- Memperbaiki virtual environment yang rusak setelah folder dipindah, lalu memasang dependensi.
- Men-debug Gemini: mengganti model karena `gemini-2.5-flash` tidak lagi tersedia untuk akun baru, menyesuaikan timeout, dan membaca error `404`, `400`, `503`, `429`; lalu memutuskan memakai `mock` sebagai default dengan tetap mempertahankan jalur fallback.
