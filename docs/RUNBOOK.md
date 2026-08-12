# Panduan Menjalankan & Penilaian Reusability

Ringkasan cara memakai repository eDOT QA Automation, dan penilaian jujur
seberapa mudah reviewer bisa menjalankannya sendiri.

**Repo:** https://github.com/meimanhulu/edot-qa-automation

---

## Bagian 1 — Cara menjalankan dari nol

### Prasyarat

| Kebutuhan | Untuk apa |
|---|---|
| Python 3.10+ | seluruh suite |
| Node.js + npm | `allure-commandline` |
| Android Studio | emulator (hanya untuk suite mobile) |
| Kredensial eSuite | login web |

### Langkah 1 — Clone dan pasang dependency

```powershell
git clone https://github.com/meimanhulu/edot-qa-automation.git
cd edot-qa-automation

python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
playwright install chromium
```

### Langkah 2 — Isi kredensial

```powershell
Copy-Item .env.example .env
notepad .env
```

Minimal untuk suite web:

```
ESUITE_BASE_URL=https://esuite.edot.id
ESUITE_EMAIL=<email>
ESUITE_PASSWORD=<password>
```

Bila salah satu kosong, suite berhenti dengan pesan yang menyebut nama
variabelnya — bukan error misterius di tengah run.

### Langkah 3 — Jalankan suite web

```powershell
pytest -m web
```

Sekitar 10-12 menit. Untuk melihat browsernya bergerak:

```powershell
$env:HEADLESS="false"
pytest -m web -v
```

### Langkah 4 — Lihat laporan

```powershell
npm install -g allure-commandline
allure serve allure-results
```

Atau buka laporan yang sudah tersimpan di repo: `docs/allure-report/index.html`

### Langkah 5 — Triage kegagalan

```powershell
python scripts/run_triage.py
```

Membaca hasil Allure, memberi verdict tiap kegagalan, menulis
`triage-report.md`. Jalankan **setelah** suite, bukan sebelum.

---

## Menjalankan suite mobile

Lebih banyak persiapan. Langkah lengkap ada di
`docs/MAESTRO_SETUP_WINDOWS.md`; ringkasnya:

**1. Pasang Maestro** — sejak 1.39.9 berjalan native di Windows, WSL tidak
diperlukan:

```powershell
Invoke-WebRequest -Uri "https://github.com/mobile-dev-inc/maestro/releases/latest/download/maestro.zip" -OutFile "$env:USERPROFILE\Downloads\maestro.zip"
Expand-Archive "$env:USERPROFILE\Downloads\maestro.zip" -DestinationPath "C:\maestro"
$env:PATH += ";C:\maestro\maestro\bin"
maestro --version
```

**2. Siapkan emulator** — Android Studio → Virtual Device Manager → Pixel 7,
API 33, system image **Google Play** dan **x86_64**.

Dua hal ini menentukan berhasil-tidaknya:
- tanpa **Google Play**, eWork SFA tidak bisa dipasang dari Play Store
- image **ARM** akan crash di laptop Intel/AMD

**3. Pasang eWork SFA** dari Play Store di emulator, lalu ambil package name:

```powershell
adb shell pm list packages | Select-String ework
```

**4. Isi `.env`:**

```
EWORK_APP_ID=id.edot.ework
EWORK_COMPANY_ID=<company id>
EWORK_USERNAME=<username>
EWORK_PASSWORD=<password>
```

**5. Jalankan:**

```powershell
pytest -m mobile
```

Sekitar 5-6 menit. Emulator harus menyala dan terdeteksi `adb devices`.

---

## Perintah sehari-hari

```powershell
pytest                            # web + mobile, satu run Allure
pytest -m web                     # web saja
pytest -m mobile                  # mobile saja
pytest -k login                   # test yang namanya mengandung "login"
pytest web/tests/test_login.py -v # satu berkas

python scripts/run_triage.py      # triage, SETELAH suite
allure serve allure-results       # buka laporan

python tools/cleanup_orphans.py "PT"   # bersihkan data sisa run yang gagal
```

⚠️ **Tiap sesi terminal baru** perlu dua hal ini:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PATH += ";C:\maestro\maestro\bin"    # hanya bila menjalankan mobile
```

---

## Bagian 2 — Seberapa reusable?

Penilaian jujur, dipisah per aspek.

### ✅ Yang sudah siap pakai

**Suite web dapat dijalankan dalam ~5 menit persiapan.** Clone, `pip install`,
isi tiga variabel di `.env`, jalankan. Tidak ada langkah tersembunyi.

**Kegagalan menjelaskan dirinya sendiri.** Variabel `.env` kosong berhenti
dengan pesan yang menyebut namanya. Data test yang tidak sah ditolak schema
dengan penyebab yang jelas, bukan timeout membingungkan. Halaman detail yang
tidak memuat data memberi diagnosis, bukan `waiting for locator`.

**Suite tetap jalan tanpa API key.** Modul AI otomatis memakai fallback Faker,
sehingga berfungsi offline dan di CI.

**Data acak tiap run.** Nama, telepon, email, alamat, NIK — semuanya berbeda
tiap eksekusi, sehingga run berulang tidak bentrok satu sama lain.

**Menambah skenario baru mengikuti pola yang jelas.** Locator hanya di page
class dan YAML; test tidak pernah menyentuh selector. Langkah panjang dipecah
jadi sub-flow di `mobile/flows/steps/`.

**Dokumentasi menjelaskan keputusan, bukan cuma langkah.**
`docs/CODE_WALKTHROUGH.md` menerangkan alasan tiap pilihan desain, dengan
sepuluh pertanyaan latihan di akhirnya.

### ⚠️ Yang perlu perhatian reviewer

**Setup mobile memakan waktu.** Realistis 1-2 jam bila belum ada Android
Studio: unduh emulator ~1,5 GB, pasang Maestro, install app dari Play Store.
Panduannya lengkap, tapi tidak bisa disebut cepat.

**Dua test gagal secara sengaja.** `TC-WEB-008` dan `TC-WEB-013d`
mendokumentasikan cacat produk. Suite yang "tidak seluruhnya hijau" itu
disengaja — brief secara eksplisit menghargainya di atas suite hijau yang
diperoleh dengan melemahkan asersi.

**Kegagalan karena lingkungan masih mungkin.** eSuite kerap merespons lambat.
Timeout sudah dinaikkan (navigasi 60 detik, `expect()` 15 detik), tetapi pada
kondisi jaringan buruk kegagalan sporadis tetap dapat terjadi. Modul triage
membantu memilahnya, dan verdict-nya perlu ditinjau manusia.

**Data test mobile tersimpan permanen.** Customer yang dibuat `TC-MOB-002`
tidak dapat dihapus dari sisi pengguna. Ini konsekuensi dari memenuhi
persyaratan brief yang meminta verifikasi *"after creation"*.

**Selector bergantung pada UI saat ini.** Web tidak menyediakan `data-testid`
maupun accessible name pada combobox, sehingga sebagian locator memakai indeks
— rapuh terhadap perubahan tata letak. Alasannya tercatat di komentar kode.

### Kesimpulan

| Aspek | Nilai |
|---|---|
| Suite web — kemudahan menjalankan | Tinggi |
| Suite mobile — kemudahan menjalankan | Sedang (setup emulator) |
| Kejelasan pesan kegagalan | Tinggi |
| Kemudahan menambah skenario | Tinggi |
| Ketahanan terhadap perubahan UI | Sedang (keterbatasan aplikasi) |
| Kelengkapan dokumentasi | Tinggi |

**Untuk reviewer yang ingin memverifikasi cepat:** jalankan `pytest -m web`,
lalu buka `docs/allure-report/index.html` dan `docs/triage-report.md`. Keduanya
sudah tersimpan di repo, jadi bisa dibaca tanpa menjalankan apa pun.

---

## Hasil terakhir

```
Web     : 17 lolos · 2 gagal  (keduanya cacat produk terdokumentasi)
Mobile  : 2 lolos             (login + create customer end-to-end)
```

### Cacat produk yang ditemukan

1. **Nama company tidak dipangkas spasi** — `'   PT X   '` tersimpan apa adanya;
   di layar identik, di database berbeda
2. **Halaman detail kosong di pembukaan pertama** — intermiten, data baru muncul
   setelah reload manual
3. **Nomor telepon salah format ditolak tanpa pesan** — tombol terkunci diam-diam
4. **Waktu respons tidak konsisten** — sebagian navigasi melewati 30 detik
5. **Navigasi mobile "New Customer" tidak konsisten** — tap kadang tidak berpindah
6. **Aksesibilitas** — combobox tanpa `aria-label`; `aria-hidden` pada elemen
   ber-focus
7. **Usability daftar company** — 470+ tanpa pagination, render bertahap,
   tanpa pencarian

Cacat nomor 1 hanya terlihat karena asersinya memakai `==`, bukan `in` —
perbandingan parsial justru akan meloloskannya.

---

## Pelajaran teknis yang membentuk suite ini

| Pola | Konsekuensi |
|---|---|
| Elemen tersembunyi sudah ada di DOM | Locator berbasis indeks wajib `:visible` |
| Render asinkron | `is_enabled`/`count` diganti polling `expect` |
| Disclosure bertingkat | Urutan pengisian tidak boleh sembarang |
| Aksi berisiko dikunci checkbox | Persetujuan wajib dicentang lebih dulu |
| `NestedScrollView` melepas view | Assert di tempat, jangan gulir balik |
| Maestro butuh flag `-e` | Environment proses tidak sampai ke sub-flow |
| **Nol `networkidle`** | Menggantung pada SPA — diganti penanda spesifik |
| **Nol tap koordinat di mobile** | Seluruh elemen punya `resource-id`, termasuk kamera dan kanvas tanda tangan |   