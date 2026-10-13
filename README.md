# STARA Mini — Customer → API → Database → Automation → AI → Web

Versi mini dari alur kerja STARA: pesan pelanggan masuk lewat webhook (simulasi WhatsApp), disimpan ke
database Supabase (PostgreSQL), dibalas otomatis oleh AI, dan dipantau staf lewat halaman web sederhana.

**Dapat dijalankan dengan dua cara:** langsung dengan Python (lihat [Cara menjalankan](#1-cara-menjalankan-proyek-dari-nol)) atau dengan **Docker** (`docker compose up --build`, lihat [Alternatif — Jalankan dengan Docker](#alternatif--jalankan-dengan-docker)).

```
POST /webhook/incoming-message
        │
        ▼
 cari / buat customer ──► simpan pesan "incoming" ──► AI membuat balasan ──► simpan pesan "outgoing" ──► respons 200
        │                                                  │ (AI gagal / lambat → balasan cadangan)
        ▼                                                  ▼
 tabel customers & messages (Supabase) ◄───────────  Halaman web  (http://localhost:8000)
```

Struktur proyek:

- `app.py` — Semua endpoint (CRUD customer, webhook), validasi, penanganan error
- `db.py` — Koneksi ke Supabase (connection pool), membaca `.env`
- `schema.sql` — Struktur tabel `customers` dan `messages`
- `ai.py`, `prompts.py` — Pembuatan balasan AI (Gemini atau mock), prompt, dan balasan cadangan
- `static/` — Halaman web (HTML, CSS, JavaScript)
- `test_manual.py` — Skrip pengujian end-to-end (34 kasus)
- `.env.example` — Contoh konfigurasi (salin menjadi `.env`)
- `Dockerfile`, `docker-compose.yml`, `.dockerignore` — Menjalankan aplikasi di dalam container Docker

---

## 1. Cara menjalankan proyek dari nol

**Prasyarat:** Python 3.10 atau lebih baru, Git, dan akun [Supabase](https://supabase.com) (gratis).
Akun Gemini (opsional) hanya diperlukan kalau ingin balasan AI sungguhan.

### Langkah 1 — Ambil kode

```bash
git clone <URL-REPOSITORY-ANDA>
cd <nama-folder-repository>
```

### Langkah 2 — Siapkan database di Supabase

1. Buat project baru di Supabase dan simpan **database password** yang Anda buat.
2. Buka tombol **Connect** pada project, pilih connection string **Session pooler**, lalu salin.
   Gunakan Session pooler, bukan _Direct connection_: direct connection hanya mendukung IPv6 dan akan
   _timeout_ di jaringan yang hanya IPv4.
3. Tabel dibuat **otomatis** dari `schema.sql` saat aplikasi pertama kali dijalankan. Alternatif manual:
   **SQL Editor → New query →** tempel isi `schema.sql` **→ Run**.

### Langkah 3 — Buat virtual environment dan pasang dependensi

```bash
python -m venv .venv
```

Aktifkan:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

> Jika PowerShell menolak dengan error _execution policy_, jalankan sekali:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

```bash
python -m pip install -r requirements.txt
```

### Langkah 4 — Atur konfigurasi `.env`

```bash
# Windows (PowerShell)
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Buka `.env` dan isi. Database cukup diisi dengan **salah satu** dari dua cara:

```
# Cara A: satu connection string (Session pooler dari Supabase)
DATABASE_URL=postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres

# Cara B: bagian terpisah (password tidak perlu di-URL-encode)
DB_HOST=aws-0-<region>.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.<project-ref>
DB_PASSWORD=<PASSWORD>
```

Catatan untuk Cara A: awalan harus `postgresql://` (bukan `postgresql+psycopg://`), dan karakter khusus
pada password (`@ : / # ?`) harus di-URL-encode, misalnya `@` menjadi `%40`.

Pengaturan AI dan lainnya:

- `AI_PROVIDER` — isi: `mock` (default) atau `gemini`. `mock` = balasan palsu berbasis kata kunci, tanpa API key
- `GEMINI_API_KEY` — isi: API key dari Google AI Studio. Hanya wajib jika `AI_PROVIDER=gemini`
- `GEMINI_MODEL` — isi: `gemini-3.8-flash`. Nama model Gemini
- `GEMINI_THINKING_LEVEL` — isi: `low` (default). Mempercepat balasan; kosongkan jika model menolaknya
- `AI_TIMEOUT_SECONDS` — isi: `15`. Batas tunggu AI sebelum memakai balasan cadangan
- `PORT` — isi: `8000`. Port server

File `.env` berisi rahasia dan sudah dimasukkan ke `.gitignore`. Jangan di-commit.
Tulis komentar di baris sendiri, bukan di belakang nilai (misalnya `AI_PROVIDER=mock   # ...`):
Docker memperlakukan komentar di belakang nilai sebagai bagian dari nilainya.

### Langkah 5 — Jalankan

```bash
python app.py
```

Server siap jika muncul `Running on http://127.0.0.1:8000`. Buka **http://localhost:8000** untuk halaman web:
tambah customer, klik namanya untuk melihat percakapan, lalu kirim pesan lewat kotak
_"Simulate an incoming WhatsApp message"_ untuk mencoba webhook.
Setiap request juga dicatat di terminal beserta durasinya (misalnya `GET /customers -> 200 in 85 ms`).

### Langkah 6 — Jalankan pengujian (opsional)

Dengan server tetap berjalan, buka terminal kedua (aktifkan venv di sana juga), lalu:

```bash
python test_manual.py
```

Skrip ini menjalankan 34 kasus (validasi, 400/404/409, webhook, hapus berantai, dsb.) dan mencetak `PASS`
atau `FAIL` untuk masing-masing. Nomor telepon yang dipakai acak, sehingga aman dijalankan berulang kali.

### Alternatif — Jalankan dengan Docker

Cara ini tidak memerlukan Python atau virtual environment di komputer; cukup **Docker Desktop**
(pastikan sudah berjalan). Langkah 1 (clone), Langkah 2 (Supabase), dan pembuatan file `.env` pada
Langkah 4 tetap diperlukan, karena container memakai database Supabase yang sama.

```bash
docker compose up --build
```

Buka **http://localhost:8000**. Untuk menghentikan, tekan `Ctrl+C`, atau jalankan `docker compose down`.
Untuk menjalankan di latar belakang: `docker compose up --build -d`, lalu lihat log dengan
`docker compose logs -f`.

Tanpa Docker Compose, hasilnya sama dengan:

```bash
docker build -t stara-mini .
docker run --rm -p 8000:8000 --env-file .env stara-mini
```

Hal yang perlu diketahui:

- File `.env` **tidak** disalin ke dalam image (lihat `.dockerignore`); nilainya diberikan saat container
  dijalankan lewat `env_file` / `--env-file`. Dengan begitu rahasia tidak ikut tersimpan di image.
- Di dalam container, aplikasi dijalankan oleh **gunicorn** (server produksi), bukan server bawaan Flask.
  Port di dalam container selalu `8000`; ubah angka kiri pada `"8000:8000"` di `docker-compose.yml`
  jika port 8000 di komputer Anda sudah terpakai.
- Container terhubung ke Supabase lewat internet, sama seperti saat dijalankan langsung, jadi
  gunakan connection string **Session pooler**.
- Pengujian tetap bisa dijalankan dari komputer: `python test_manual.py` (server di container sudah
  berada di `localhost:8000`).

---

## 2. Teknologi yang dipilih dan alasannya

- **Bahasa & framework: **Python 3 + Flask\*\*\*\* — Kecil dan eksplisit: setiap route, validasi, dan query terlihat jelas, sehingga mudah dijelaskan baris demi baris. Python juga bahasa yang paling saya kuasai.
- **Database: **PostgreSQL di Supabase** (free tier)** — Sesuai saran soal. Constraint (`UNIQUE`, `CHECK`, foreign key `ON DELETE CASCADE`) dijaga oleh database itu sendiri, bukan hanya oleh kode.
- **Akses database: **psycopg 3 + SQL biasa** (tanpa ORM)** — Setiap query terlihat langsung; tidak ada lapisan yang tersembunyi. Query memakai placeholder `%s` untuk mencegah SQL injection.
- **Koneksi: **Connection pool** (`psycopg_pool`)** — Database ada di server yang jauh; membuka koneksi baru pada setiap request mahal (TCP + TLS + login). Pool menyimpan beberapa koneksi terbuka dan memakainya ulang.
- **AI: **Google Gemini** + mode **mock\*\*\*\* — Gemini punya free tier. Mode `mock` membuat proyek tetap bisa dijalankan dan diuji tanpa API key atau internet, juga oleh penilai.
- **Frontend: **HTML + CSS + JavaScript biasa\*\*\*\* — Soal hanya meminta halaman yang berfungsi dan rapi; tanpa framework dan tanpa build step.
- **Container: **Docker + gunicorn\*\*\*\* — Lingkungan yang sama di komputer mana pun tanpa memasang Python sendiri. gunicorn dipakai di dalam container karena server bawaan Flask hanya untuk pengembangan. `.env` tidak ikut masuk image.
- **Pengujian: **Skrip `test_manual.py`** (library `requests`)** — Menguji API yang sedang berjalan secara end-to-end, dengan hasil PASS/FAIL yang mudah dibaca.

Keputusan desain lain yang sengaja saya ambil:

- **Pesan masuk disimpan sebelum AI dipanggil**, dalam transaksi terpisah. Jika AI gagal atau lambat, pesan
  tidak hilang dan pelanggan tetap menerima balasan cadangan (webhook tetap mengembalikan 200).
- **AI punya timeout** dan satu kali percobaan ulang untuk error 503 (server Gemini sibuk). Batas
  "maksimal 3 kalimat" dipaksakan di kode, bukan hanya di prompt, karena model bisa saja mengabaikan prompt.
- **Nomor telepon kembar → 409 Conflict**, bukan 400: datanya valid, tetapi bentrok dengan data yang sudah ada.
- **Hapus customer ikut menghapus pesannya** (`ON DELETE CASCADE`), sehingga tidak ada pesan yatim.
- **Keamanan:** tidak ada rahasia di kode (semuanya di `.env`); halaman web memakai `textContent`
  (bukan `innerHTML`) untuk mencegah XSS; **Row Level Security** diaktifkan tanpa policy di kedua tabel agar
  API publik Supabase (kunci `anon`) tidak bisa mengakses data. Backend terhubung langsung sebagai pemilik
  database sehingga tetap berfungsi.
- Prompt AI ada di `prompts.py`, terpisah dari logika.

---

## 3. Daftar endpoint dan contoh permintaan

Semua respons berformat JSON. Error selalu berbentuk `{"error": "...", "details": [...]}`.

- `POST /customers` — Tambah customer. Status: `201`, `400` (tidak valid), `409` (telepon kembar)
- `GET /customers` — Daftar customer; filter opsional `?status=active`. Status: `200`, `400` (status tidak dikenal)
- `GET /customers/{id}` — Satu customer beserta riwayat pesannya. Status: `200`, `404`
- `PUT /customers/{id}` — Ubah data (field yang tidak dikirim tetap). Status: `200`, `400`, `404`, `409`
- `DELETE /customers/{id}` — Hapus customer beserta pesannya. Status: `200`, `404`
- `POST /webhook/incoming-message` — Terima pesan, simpan, balas dengan AI. Status: `200`, `400` (data tidak lengkap)
- `GET /` — Halaman web. Status: `200`

Status customer yang diizinkan: `lead` (default), `active`, `inactive`.

### Contoh curl

```bash
# Tambah customer
curl -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "Budi Santoso", "phone": "081234567890", "status": "lead"}'

# Daftar semua customer
curl http://localhost:8000/customers

# Daftar customer dengan status active
curl "http://localhost:8000/customers?status=active"

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

Contoh error (webhook tanpa `message`) — status `400`:

```json
{ "error": "Incomplete data", "details": ["message is required"] }
```

**Catatan untuk PowerShell di Windows:** tanda kutip pada JSON sering rusak. Gunakan `curl.exe` (bukan
`curl`, yang merupakan alias perintah lain) dengan tanda kutip yang di-escape, atau pakai `Invoke-RestMethod`:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/webhook/incoming-message `
  -ContentType "application/json" `
  -Body '{"phone": "081234567890", "name": "Budi Santoso", "message": "Halo, mau tanya harga paket"}'
```

---

## 4. Yang belum selesai / akan saya perbaiki jika punya waktu lebih

**Fungsi**

- **Integrasi Gemini belum terverifikasi sampai berhasil.** Kodenya sudah ditulis, tetapi pada saat pengujian
  Gemini mengembalikan error kuota (`429`) dan server sibuk (`503`) di free tier. Yang sudah terbukti adalah
  jalur _fallback_-nya: webhook tetap mengembalikan 200, pesan tersimpan, dan pelanggan menerima balasan
  cadangan. Mode `mock` adalah default agar proyek tetap bisa dijalankan.
- **Normalisasi nomor telepon.** Saat ini `081234567890` dan `+6281234567890` dianggap dua nomor berbeda.
  Perlu diseragamkan sebelum disimpan, ditambah validasi format.
- **Konteks percakapan untuk AI.** AI hanya melihat pesan terakhir; seharusnya ikut membaca beberapa pesan
  sebelumnya agar balasan nyambung.
- **Batas panjang pesan** pada webhook (melindungi database dan biaya AI dari payload yang sangat besar).
- **Paginasi** pada `GET /customers`.

**Keamanan**

- **Autentikasi API key** pada endpoint dan verifikasi tanda tangan webhook (seperti WhatsApp Cloud API).
  Saat ini siapa pun yang bisa menjangkau server dapat memanggil semua endpoint, dan halaman web tidak
  memakai login.
- `python app.py` memakai server bawaan Flask dengan `host="0.0.0.0"`, sehingga dapat diakses dari perangkat
  lain di jaringan yang sama. Versi Docker sudah memakai gunicorn, tetapi tetap perlu HTTPS (reverse proxy)
  untuk produksi.

**Keandalan & performa**

- **AI diproses secara asinkron** (antrian/background job), supaya webhook langsung membalas 200 ke WhatsApp
  dan tidak menunggu AI. Saat ini webhook menunggu AI, paling lama sekitar 30 detik jika terjadi retry.
- **Dua webhook bersamaan dari nomor baru yang sama** bisa bentrok di constraint `UNIQUE` dan menghasilkan
  error 500; perlu `INSERT ... ON CONFLICT` atau retry.
- **Region database.** Project Supabase saya berada di Sydney (`ap-southeast-2`), sedangkan penggunaan dari
  Indonesia; memindahkannya ke Singapura akan mengurangi latensi.
- **Pengujian otomatis** (pytest dengan database uji dan HTTP yang di-mock). `test_manual.py` saat ini harus
  dijalankan terhadap server yang sedang hidup dan memakai database yang sama.
- Skema dikelola dengan satu file `schema.sql`; untuk perubahan skema di masa depan, perlu migrasi
  (misalnya Alembic).

**Belum dikerjakan (bonus)**

- Integrasi **n8n** dan **deploy** ke hosting.
- Docker: belum ada _health check_ dan belum ada kontainer database lokal (proyek ini memakai Supabase).

---

## 5. Penggunaan AI dalam pengerjaan

<!-- PERIKSA: bagian ini harus mencerminkan kenyataan. Hapus atau ubah apa pun yang tidak sesuai. -->

Saya memakai **Claude (Anthropic)** selama pengerjaan.

**Bagian yang dibantu AI**

- Kerangka dan kode awal proyek: struktur file, `schema.sql`, `app.py` (CRUD, validasi, webhook),
  `ai.py`, `prompts.py`, dan halaman web di `static/`.
- Migrasi dari SQLite ke Supabase/PostgreSQL, penambahan connection pool, dan log durasi request.
- Skrip pengujian `test_manual.py`, file Docker (`Dockerfile`, `docker-compose.yml`, `.dockerignore`), dan draf README ini.
- Bantuan membaca dan mendiagnosis error: masalah virtual environment, format `DATABASE_URL`, dan error
  dari API Gemini.

**Bagian yang saya kerjakan, ubah, atau perbaiki sendiri**

- Membuat project Supabase dan menentukan konfigurasinya: memilih _Session pooler_ setelah _direct
  connection_ mengalami timeout, lalu mengatur `.env` (termasuk memperbaiki awalan `postgresql+psycopg://`
  yang tidak cocok dengan driver yang dipakai).
- Menyiapkan lingkungan lokal: memperbaiki virtual environment yang rusak setelah folder dipindah, memasang
  dependensi, dan menjalankan serta mencoba semua endpoint dan halaman web.
- Men-debug integrasi Gemini: mencoba endpoint Interactions, mengganti model karena `gemini-2.5-flash`
  tidak lagi tersedia untuk akun baru, menyesuaikan timeout, dan membaca log error `404`, `400`, `503`, dan
  `429`; lalu memutuskan memakai mode `mock` sebagai default sambil mempertahankan jalur fallback.
- Menjalankan pengujian dan memeriksa hasilnya di Supabase Table Editor.
