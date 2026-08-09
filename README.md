# eDOT QA Automation — Take-Home Test V4

Suite automation testing untuk **eSuite (web)** dan **eWork SFA (mobile)**,
dengan AI di dalam suite.

> **Baca [docs/CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md) sebelum submit.**
> Dokumen itu menjelaskan setiap keputusan desain, dan diakhiri 10 pertanyaan
> latihan. Brief menyatakan ketidakmampuan menjelaskan kode akan diperlakukan
> sebagai bukan karya sendiri.

---

## Setup

### Web — Playwright

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
playwright install chromium

Copy-Item .env.example .env       # lalu isi nilainya
```

Variabel wajib untuk suite web: `ESUITE_BASE_URL`, `ESUITE_EMAIL`, `ESUITE_PASSWORD`.
Bila salah satu kosong, suite gagal cepat dengan pesan yang menyebut nama variabelnya.

### Mobile — Maestro

Windows perlu WSL. Panduan lengkap: **[docs/MAESTRO_SETUP_WINDOWS.md](docs/MAESTRO_SETUP_WINDOWS.md)**

```bash
maestro --version                 # verifikasi Maestro terpasang
adb devices                       # verifikasi emulator terlihat
```

Suite mobile otomatis di-skip dengan pesan jelas bila Maestro tidak ditemukan.

---

## Menjalankan

```bash
pytest -m web                     # suite web saja
pytest -m mobile                  # suite mobile saja
pytest                            # keduanya, masuk satu run Allure

python scripts/run_triage.py      # triage kegagalan, jalankan SETELAH suite
allure serve allure-results       # buka laporan
```

Untuk melihat browser bergerak saat debug:

```powershell
$env:HEADLESS="false"
pytest -m web -v
```

---

## Struktur

```
conftest.py         fixture bersama; satu-satunya pembaca os.environ
web/pages/          Page Object — satu-satunya tempat locator
web/tests/          test Playwright, tanpa selector mentah
mobile/flows/       YAML Maestro; login sebagai shared sub-flow via runFlow
mobile/runner.py    wrapper Pytest yang memanggil Maestro
ai/                 3A generator data · 3B triage kegagalan
scripts/            entry point triage
docs/               walkthrough kode, panduan Maestro, prompt spec-kit
```

---

## Aturan yang tidak boleh dilanggar

| Aturan | Kenapa |
|---|---|
| Asersi tidak boleh dilemahkan agar hijau | Non-negotiable pada brief |
| Tidak ada kredensial atau API key di repo | Non-negotiable |
| Data test dihapus setelah run | Non-negotiable — shared environment |
| Setiap baris harus bisa dijelaskan | Non-negotiable |
| Tidak ada `time.sleep()` | Auto-waiting Playwright / wait command Maestro |
| Locator hanya di page class dan YAML | Tidak ada selector mentah di berkas test |
| Login sekali per sesi via `storage_state` | Bukan login di dalam tiap test |
| Assertion Tier 2 diberi komentar penanda | Agar reviewer bisa membedakan bug produk dari cacat skrip |

---

## Temuan saat inspeksi manual

Semua diverifikasi langsung di aplikasi, bukan diasumsikan dari brief.
Dicatat karena memengaruhi implementasi dan menjelaskan keputusan selector.

### Aplikasi tidak menyediakan penanda test sama sekali

| Temuan | Bukti | Dampak |
|---|---|---|
| **Nol `data-testid`** di seluruh aplikasi | `document.querySelectorAll('[data-testid]').length === 0` | Prioritas pertama brief tidak tersedia |
| **Nol accessible name** pada semua combobox | `aria-label`, `aria-labelledby`, dan `title` kosong pada kelimanya | `get_by_role(..., name=...)` selalu gagal; combobox diakses lewat urutan |
| **`id` bernilai `radix-:rd:`** | Radix UI, di-generate ulang tiap render | Tidak dipakai sebagai selector |

Konsekuensinya: input memakai `get_by_placeholder()` (atribut stabil, prioritas
ke-3 brief), tombol memakai `role` + accessible name, dan combobox terpaksa
memakai indeks — satu-satunya pembeda yang tersedia.

### Alur login berbeda dari brief

| Brief | Kenyataan |
|---|---|
| Tombol "Continue" lalu "Sign In" | **Keduanya bertuliskan "Log In"** |
| — | Login lewat OIDC di `cronus.edot.id/oidc/interaction/<id>`; interaction id berubah tiap sesi, sehingga penantian berbasis URL tidak dipakai |
| — | `input[name=password]` sudah ada sebagai `type=hidden` di layar username, begitu pula sebaliknya — locator wajib memakai filter `:visible` |

### Wizard Register Company berbeda dari brief

| Brief | Kenyataan |
|---|---|
| Cascade langsung tampil di Step 1 | Baru **muncul setelah Country dipilih** (progressive disclosure) |
| Level keempat bernama "Zone" | Namanya **"Sub District"** |
| Postal Code dipilih | **Terisi otomatis** setelah Sub District; field-nya read-only |
| — | Tiap dropdown cascade punya **kotak Search** di dalam listbox |
| — | Step 2 "Register Legal" hanya berisi Legal Document opsional — nol input, nol combobox |
| — | Step 3 "Create Your Branch" mengaku opsional, tetapi Branch Name terisi otomatis `Headquarter` dan catatan di bawah form menyatakan mengisinya membuat seluruh field wajib |

### Validasi berupa tombol disabled, bukan pesan error

Baik Account Center maupun wizard mengunci tombol lanjut selama form belum
valid, tanpa menampilkan pesan error apa pun. Test Negative karena itu
memverifikasi **status tombol**, bukan teks error yang memang tidak muncul.

### Format telepon menyebabkan kegagalan senyap

Field Phone menampilkan `+62` sebagai prefix terpisah, sehingga hanya menerima
nomor lokal diawali `8` (mis. `81982913977`). Format `021...`, `+62...`, atau
berawalan `0` membuat tombol Next **terkunci tanpa pesan apa pun** — user tidak
diberi tahu apa yang salah.

Ditangkap oleh schema validation di `ai/schemas.py` supaya kegagalan menyebut
penyebab sebenarnya, bukan berupa timeout yang membingungkan.

### Temuan aksesibilitas (di luar cakupan brief)

- Seluruh combobox tanpa `aria-label` — pengguna screen reader tidak mendapat
  informasi apa pun tentang fungsi tiap dropdown
- Dialog "Add Legal Document" memasang `aria-hidden="true"` pada elemen yang
  masih memegang focus. Peringatan Chrome: *"Blocked aria-hidden on an element
  because its descendant retained focus"*

### Karakteristik data

- Akun uji memiliki **571 company**, seluruhnya dirender sekaligus tanpa
  pagination — 1.148 tombol dalam satu DOM
- Halaman Companies **tidak punya search input**; pencarian dilakukan dengan
  memfilter kartu yang sudah ada di DOM
- Company `QA Production` (ID 5049209) berstatus Active sampai 27/04/2027 —
  ID yang sama dengan fallback mobile pada brief

---

## Pembagian tanggung jawab data test

| Sumber | Field |
|---|---|
| **Modul AI (3A)** | Company Name, Email, Phone, Street Address |
| **Opsi aplikasi** | Industry Type, Company Type, Language, Country, Province, City, District, Sub District |
| **Aplikasi (otomatis)** | Postal Code, Company ID |

Nilai dropdown diambil dari **opsi pertama** yang disediakan aplikasi, bukan
dari data AI. Alasannya teknis: validitas cascade hanya dapat ditentukan saat
runtime — opsi Sub District untuk `SIPATANA` berbeda dari untuk `KOTA TENGAH`,
dan kombinasi tak sah gagal berupa timeout tanpa pesan.

Nilai yang terpilih **dibaca balik** dan dipakai sebagai expected value Tier 2,
sehingga verifikasi membandingkan terhadap apa yang benar-benar masuk ke form —
bukan terhadap nilai yang diasumsikan.

---

## Status pengerjaan

| Bagian | Status |
|---|---|
| Struktur project, fixture, Allure | ✅ Selesai |
| `LoginPage` — 4 test lolos | ✅ Selesai |
| `CompaniesPage` · `RegisterCompanyWizard` · `CompanyDetailPage` | ✅ Selector terverifikasi |
| Test create company, verify detail, cleanup | 🔄 Sedang dijalankan |
| Modul AI 3A — generator + schema + fallback Faker | ✅ Selesai |
| Modul AI 3B — triage kegagalan | ✅ Selesai |
| Suite mobile — Maestro | ⬜ Belum |
| Laporan Allure + laporan triage | ⬜ Belum |

---

## Yang harus diisi sebelum submit

- [ ] Link repo dimasukkan ke dokumen test case (Excel / Google Sheet)
- [ ] `AI_USAGE.md` — lima poin yang diminta brief
- [ ] Laporan Allure dari satu run web penuh
- [ ] Laporan triage dari run yang **sengaja digagalkan**
- [ ] Catatan jujur soal skenario yang tidak selesai
- [ ] Bila memakai kredensial mobile fallback, catat di bagian ini