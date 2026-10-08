# ki.eng.unila.ac.id — Sistem Pencarian Karya Ilmiah Terpadu Universitas Lampung

Sistem ini adalah mesin pencari terpadu untuk menelusuri karya ilmiah Universitas Lampung dari dua sumber repositori melalui satu antarmuka. Aplikasi ini mengintegrasikan metadata dari **Digilib dan LPPM**, sehingga pengguna dapat mencari karya akademik tanpa perlu membuka setiap repositori secara terpisah.

## ✨ Fitur Utama

* **Pencarian Terpadu:** mencari dokumen akademik dari sumber Digilib dan LPPM.
* **Full-Text Search:** pencarian teks penuh menggunakan PostgreSQL dengan konfigurasi bahasa Indonesia.
* **Pemeringkatan Hasil:** mengurutkan hasil berdasarkan relevansi kata kunci, termasuk kecocokan judul dan penulis.
* **Filter Pencarian:** menyaring hasil berdasarkan sumber, rentang tahun, dan fakultas/divisi jika tersedia.
* **Autocomplete:** memberikan saran kata kunci saat pengguna melakukan pencarian.
* **Detail Dokumen:** menampilkan informasi dokumen dan tautan ke sumber aslinya.
* **Tren Pencarian:** mencatat kata kunci yang dicari pengguna.
* **Dashboard Analitik:** menyediakan halaman untuk melihat analitik pencarian.

## 🛠️ Teknologi yang Digunakan

* Figma
* HTML/CSS
* Python
* Django
* PostgreSQL
* PostgreSQL Full-Text Search
* GIN Index
* Redis untuk caching pada lingkungan Linux
* OAI-PMH untuk pengambilan metadata repositori

## 📌 Endpoint

| Endpoint                | Fungsi                       |
| ----------------------- | ---------------------------- |
| `/`                     | Halaman pencarian utama      |
| `/search/`              | Halaman hasil pencarian      |
| `/detail/<id>/`         | Detail dokumen akademik      |
| `/api/dokumen/`         | REST API data dokumen        |
| `/api/autocomplete/`    | API autocomplete kata kunci  |
| `/dashboard-pencarian/` | Dashboard analitik pencarian |

## 🚀 Instalasi Sistem
### Requirements

* Python dan pip
* PostgreSQL
* Git
* Redis untuk caching pada lingkungan Linux, sesuai konfigurasi aplikasi


```bash
git clone https://github.com/nazmahevano/Search-Engine-Unila.git
cd Search-Engine-Unila
```

```bash
python -m venv .venv
```

Aktifkan environment:

**Windows**

```bash
.venv\Scripts\activate
```

**Linux/macOS**

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

Buat file `.env` di direktori utama proyek:

Sesuaikan kredensial database dengan konfigurasi PostgreSQL lokal. Jangan menggunakan secret key atau kredensial produksi pada environment pengembangan.

```bash
python manage.py migrate
```

```bash
python manage.py createsuperuser
```

Langkah ini opsional, sesuai kebutuhan pengelolaan aplikasi.

```bash
python manage.py runserver
```

Buka `http://127.0.0.1:8000/` melalui browser.

> **Catatan:** Fitur pencarian kemiripan teks memerlukan dukungan ekstensi PostgreSQL `pg_trgm`. Pastikan ekstensi tersedia dan konfigurasi database, environment, serta cache telah disesuaikan sebelum menjalankan aplikasi.

## 📂 Struktur Proyek

```text
Search-Engine-Unila/
├── UnilaSearch/       # Konfigurasi proyek Django
├── SearchEngine/      # Model, views, API, dan logika pencarian
├── templates/         # Template antarmuka
├── static/            # Aset static
├── manage.py          # Django management commands
├── requirements.txt   # Dependensi Python
└── README.md
```

## 👩‍💻 Pengembang

**Rifdah Fitriani Saharrudin as Frontend Developer**
**Nazma Hevano as Backend Developer**

---

Dikembangkan sebagai proyek tugas akhir untuk mendukung pencarian karya ilmiah Universitas Lampung secara terpadu.
