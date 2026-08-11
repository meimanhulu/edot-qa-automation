# eDOT QA Automation — Take-Home Test V4

Suite automation testing untuk **eSuite (web)** dan **eWork SFA (mobile)**,
dengan AI di dalam suite — generasi data test dan triage kegagalan.

**Repository:** https://github.com/meimanhulu/edot-qa-automation

---

## Ringkasan hasil

| Suite | Hasil |
|---|---|
| **Web** (Playwright) | 15 lolos · 4 gagal — kegagalannya disengaja dan terdokumentasi |
| **Mobile** (Maestro) | TC-MOB-001 login **lolos**, dilaporkan ke run Allure yang sama |

| Bukti | Lokasi |
|---|---|
| Laporan Allure (HTML) | [`docs/allure-report/`](docs/allure-report/) |
| Laporan triage | [`docs/triage-report.md`](docs/triage-report.md) |
| Dokumentasi AI | [`AI_USAGE.md`](AI_USAGE.md) |
| Penjelasan tiap keputusan desain | [`docs/CODE_WALKTHROUGH.md`](docs/CODE_WALKTHROUGH.md) |
| Panduan setup mobile | [`docs/MAESTRO_SETUP_WINDOWS.md`](docs/MAESTRO_SETUP_WINDOWS.md) |
| Dokumen test case | Google Sheet terpisah, 26 skenario |

---

## Setup

### Web — Playwright

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env       # lalu isi nilainya
```

Wajib diisi: `ESUITE_BASE_URL`, `ESUITE_EMAIL`, `ESUITE_PASSWORD`.
Bila salah satu kosong, suite gagal cepat dengan pesan yang menyebut nama
variabelnya — bukan error misterius di tengah run.

### Mobile — Maestro

Sejak Maestro 1.39.9 CLI-nya berjalan **native di Windows**, jadi WSL tidak
diperlukan:

```powershell
Invoke-WebRequest -Uri "https://github.com/mobile-dev-inc/maestro/releases/latest/download/maestro.zip" -OutFile "$env:USERPROFILE\Downloads\maestro.zip"
Expand-Archive "$env:USERPROFILE\Downloads\maestro.zip" -DestinationPath "C:\maestro"
$env:PATH += ";C:\maestro\maestro\bin"
maestro --version
```

Prasyarat: emulator Android dengan image **Google Play** (agar eWork SFA bisa
dipasang dari Play Store) dan `adb devices` mengenalinya.

Isi kredensial mobile di `.env`:

```
EWORK_APP_ID=id.edot.ework
EWORK_COMPANY_ID=...
EWORK_USERNAME=...
EWORK_PASSWORD=...
```

---

## Menjalankan

```powershell
pytest -m web                     # suite web
pytest -m mobile                  # suite mobile
pytest                            # keduanya, satu run Allure

python scripts/run_triage.py      # triage kegagalan — SETELAH suite
allure serve allure-results       # buka laporan

python tools/cleanup_orphans.py "PT"   # bersihkan data sisa run yang gagal
```

Melihat browser bergerak saat debug: `$env:HEADLESS="false"`

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
tools/              pembersih data sisa
docs/               walkthrough kode, panduan Maestro, bukti eksekusi
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
| Tidak ada `networkidle` | Nol pemakaian — lihat Pelajaran Teknis |
| Locator hanya di page class dan YAML | Tidak ada selector mentah di berkas test |
| Login sekali per sesi via `storage_state` | Bukan login di dalam tiap test |
| Assertion Tier 2 diberi komentar penanda | Agar reviewer membedakan bug produk dari cacat skrip |

---

## Skenario dan hasilnya

### Web — eSuite

| Skenario | Tier | Status |
|---|---|---|
| Login valid — greeting "Welcome Back," | 1 | ✅ |
| Login password salah — pesan error spesifik | Negative | ✅ |
| Tombol Log In disabled saat username kosong | Negative | ✅ |
| Email ber-spasi dan huruf besar | 1 | ✅ |
| Next disabled sampai Step 1 lengkap | 1 | ✅ |
| Validasi bereaksi saat field dikosongkan | 1 | ✅ |
| Cascade parent reset saat Province diubah | 1 | ✅ |
| Register terkunci sebelum persetujuan | 1 | ✅ |
| Validasi field wajib (parametrized ×4) | Negative | ✅ |
| Create company + verifikasi di daftar | 2 | ✅ |
| **Verify detail — field per field** | **2** | ✅ |
| Company ID ada dan read-only | 2 | ✅ |
| Cascade read-only di halaman detail | 1 | ✅ |
| Delete + verifikasi record hilang | 2 | ✅ |
| **Detail page memuat data tanpa reload** | 1 | ❌ **cacat produk** |
| Company name tersimpan ter-trim | 2 | ⚠️ flaky |
| Delete company (dalam suite penuh) | 2 | ⚠️ flaky |

### Mobile — eWork SFA

| Skenario | Tier | Status |
|---|---|---|
| **TC-MOB-001 Login eWork SFA** | 1 | ✅ |
| TC-MOB-002 Create customer + verifikasi field | 2 | ⬜ flow ditulis, belum dieksekusi |

`TC-MOB-002` sudah punya seluruh selector terverifikasi lewat `maestro hierarchy`
dan assertion Tier 2 di YAML-nya. Yang belum hanya eksekusi penuh — navigasi
dari dashboard ke form pendaftaran memerlukan waktu muat yang belum selesai
dikalibrasi.

Flow-nya sengaja **berhenti sebelum submit**: langkah setelah submit belum
diinspeksi, dan tanpa jalur penghapusan, menekannya akan meninggalkan data di
shared environment.

---

## Cacat produk yang ditemukan

### 1. Halaman detail tidak memuat data pada pembukaan pertama

**Test:** `TC-WEB-013d` — gagal secara sengaja selama cacatnya ada.

Setelah company dibuat, membukanya lewat Companies → Manage menampilkan form
**kosong seluruhnya**: Company Name kosong, Company ID kosong, seluruh dropdown
masih `Choose ...`. Data baru muncul setelah halaman dimuat ulang, tanpa
petunjuk apa pun bagi pengguna.

Suite melakukan reload otomatis agar verifikasi Tier 2 tetap berjalan. Reload
itu **dicatat, tidak disembunyikan** — lampiran Allure bernama
*"TEMUAN: detail page perlu reload"* muncul tiap kali reload dibutuhkan, dan
`TC-WEB-013d` memastikan cacatnya tetap terlihat. Bila aplikasi diperbaiki,
test itu menjadi hijau dengan sendirinya.

Cacat ini kemungkinan besar terlewat oleh pengujian manual: pengguna biasanya
tidak membuka halaman detail sedetik setelah membuat company.

### 2. Nomor telepon salah format ditolak tanpa pesan

Field Phone menampilkan `+62` sebagai prefix terpisah, sehingga hanya menerima
nomor lokal diawali `8` (mis. `81982913977`). Format `021...`, `+62...`, atau
berawalan `0` membuat tombol Next **terkunci tanpa pesan error apa pun**.

Ditangkap oleh schema validation di `ai/schemas.py` supaya kegagalan menyebut
penyebab sebenarnya, bukan berupa timeout yang membingungkan.

### 3. Aksesibilitas (web)

- Seluruh combobox tanpa `aria-label`, `aria-labelledby`, maupun `title` —
  pengguna screen reader tidak mendapat informasi apa pun tentang fungsi
  tiap dropdown
- Dialog "Add Legal Document" memasang `aria-hidden="true"` pada elemen yang
  masih memegang focus. Peringatan Chrome: *"Blocked aria-hidden on an element
  because its descendant retained focus"*

### 4. Usability daftar company

Empat hal yang saling memperburuk: **tanpa pagination** (470+ company dalam satu
halaman), **render bertahap** (kartu muncul hanya saat digulir), **company baru
di paling bawah**, dan **tanpa kolom pencarian**.

Akibatnya pengguna harus menggulir melewati ratusan kartu untuk melihat company
yang baru saja ia buat.

---

## Temuan saat inspeksi — berbeda dari brief

### Web tidak menyediakan penanda test; mobile justru sebaliknya

| Platform | Temuan |
|---|---|
| **Web** | Nol `data-testid`, nol accessible name pada combobox, `id` bernilai `radix-:rd:` yang di-generate ulang tiap render |
| **Mobile** | `resource-id` bersih dan stabil di seluruh layar — prioritas pertama pada urutan brief, tanpa satu pun tap koordinat |

Konsekuensinya di web: input memakai `get_by_placeholder()`, tombol memakai
`role` + accessible name, dan combobox terpaksa memakai indeks — satu-satunya
pembeda yang tersedia.

### Alur login web

| Brief | Kenyataan |
|---|---|
| Tombol "Continue" lalu "Sign In" | **Keduanya bertuliskan "Log In"** |
| — | OIDC di `cronus.edot.id/oidc/interaction/<id>`; interaction id berubah tiap sesi |
| — | `input[name=password]` sudah ada sebagai `type=hidden` di layar username — locator wajib `:visible` |

### Wizard Register Company

| Brief | Kenyataan |
|---|---|
| Cascade langsung tampil di Step 1 | Baru **muncul setelah Country dipilih** |
| Level keempat "Zone" | Namanya **"Sub District"** |
| Postal Code dipilih | **Terisi otomatis**; elemennya combobox disabled |
| — | Memilih Country ≠ Indonesia mengubah struktur cascade (Philippines: Region → Province → City → Barangay) dan prefix telepon |
| — | Step 2 "Register Legal" hanya berisi dokumen opsional |
| — | Step 3 mengaku opsional, tetapi Branch Name bertanda wajib — kontradiksi di UI |

### Validasi berupa tombol disabled

Account Center maupun wizard mengunci tombol lanjut selama form belum valid,
**tanpa pesan error**. Test Negative karena itu memverifikasi status tombol.

---

## Pembagian tanggung jawab data test

| Sumber | Field |
|---|---|
| **Modul AI (3A)** | Company Name, Email, Phone, Street Address · nama & kontak customer |
| **Opsi aplikasi** | Industry Type, Company Type, Language, Province, City, District, Sub District |
| **Data test** | Country — ditentukan eksplisit `Indonesia` |
| **Aplikasi (otomatis)** | Postal Code, Company ID |

Nilai dropdown diambil dari **opsi pertama** yang disediakan aplikasi. Alasannya
teknis: validitas cascade hanya dapat ditentukan saat runtime — opsi Sub District
untuk `SIPATANA` berbeda dari untuk `KOTA TENGAH`, dan kombinasi tak sah gagal
berupa timeout tanpa pesan.

Country dikecualikan karena opsi pertamanya `Philippines`, yang mengubah seluruh
bentuk form.

Nilai yang terpilih **dibaca balik** dan dipakai sebagai expected value Tier 2 —
sehingga verifikasi membandingkan terhadap apa yang benar-benar masuk ke form.

---

## AI di dalam suite

Detail lengkap di [`AI_USAGE.md`](AI_USAGE.md). Ringkasnya:

**3A — Generator data test.** Meminta model menghasilkan data bisnis Indonesia
yang koheren, memvalidasinya terhadap schema Pydantic sebelum dikonsumsi test,
retry sekali bila tidak valid, lalu jatuh ke fallback Faker. Tanpa API key,
fallback dipakai langsung sehingga suite tetap jalan offline dan di CI. Data
yang dipakai beserta sumbernya dilampirkan ke Allure.

**3B — Triage kegagalan.** Membaca hasil Allure setelah run, menelusuri bukti
mengikuti urutan yang ditetapkan brief, lalu memberi verdict: *script/environment
defect*, *kandidat product bug*, atau *flaky*. Modul ini tidak menyentuh test,
tidak membuat bug report, dan tidak menutup apa pun.

Verdict pada run terakhir:

| Verdict | Jumlah |
|---|---|
| kandidat product bug | 3 |
| script/environment defect | 1 |

Dua di antaranya, berdasarkan peninjauan manual, lebih tepat dikategorikan
**flaky** — kegagalannya berasal dari waktu render, bukan perilaku aplikasi yang
salah. Ini justru contoh mengapa brief mensyaratkan verdict sebagai usulan untuk
manusia: penelusuran bukti otomatis tidak dapat membedakan "assertion gagal
karena bug" dari "assertion gagal karena elemen belum ter-render".

---

## Pelajaran teknis dari aplikasi ini

| Pola | Contoh | Konsekuensi |
|---|---|---|
| **Elemen tersembunyi sudah ada di DOM** | `input[name=password]` di layar username; combobox cascade sebelum Country dipilih | Locator berbasis indeks wajib memakai `:visible` |
| **Render asinkron** | tombol validasi, Postal Code, kartu company | Pemeriksaan seketika (`is_enabled`, `count`) diganti polling (`expect`) |
| **Disclosure bertingkat** | cascade muncul setelah Country; field branch setelah Branch Name | Urutan pengisian tidak boleh sembarang |
| **Aksi berisiko dikunci checkbox** | Register di Step 3; Confirm pada dialog Delete | Checkbox persetujuan wajib dicentang lebih dulu |

Satu keputusan yang layak disebut: **nol pemakaian `networkidle`**. Playwright
menyarankan menghindarinya untuk SPA, dan eSuite memuat data lewat XHR yang
berjalan terus sehingga kondisi "jaringan tenang" tidak pernah tercapai —
penantiannya menggantung sampai timeout padahal halaman sudah siap. Penggantinya
penanda spesifik: URL berubah, elemen tujuan muncul, atau tombol kembali enabled.

Untuk mobile: variabel harus dilewatkan lewat flag `-e`, **bukan** environment
proses. Dengan environment proses saja, `appId: ${EWORK_APP_ID}` terbaca sebagai
`undefined` dan flow gagal dengan *"Package undefined is not installed"* — flag
`-e` diteruskan sampai ke sub-flow yang dipanggil `runFlow`.

---

## Catatan atas dua test web yang masih flaky

`test_delete_company` dan `test_company_name_stored_trimmed` lolos bila
dijalankan sendiri, tetapi gagal saat suite penuh dijalankan. Penyebabnya render
bertahap pada daftar company — kartu yang baru dibuat butuh waktu muncul, dan
waktunya bertambah seiring jumlah company yang menumpuk.

Sudah dimitigasi dengan `scroll_to_load_all()` dan polling `expect()`, tetapi
belum sepenuhnya stabil. **Tidak ditutupi dengan melemahkan asersi** — brief
menyebut suite hijau yang diperoleh dengan cara itu sebagai kegagalan
non-negotiable.

## Data test di shared environment

Fixture `created_company` menghapus company di teardown, dan
`test_delete_company` memverifikasi penghapusan secara eksplisit.

Run yang gagal di tengah fixture tidak sempat menjalankan teardown, sehingga
selama pengembangan sempat ada company yang tertinggal. Semuanya sudah
dibersihkan, dan `tools/cleanup_orphans.py` tersedia untuk pembersihan susulan.

---

## Menambah skenario baru

1. Buat page class di `web/pages/` — locator hanya di sini
2. Ekspos method bermakna bisnis, bukan locator mentah
3. Kembalikan **keadaan**, jangan assert di dalam page object
4. Tulis test di `web/tests/` yang memanggilnya
5. Beri komentar `# Tier 2:` pada asersi yang memverifikasi data
6. Buktikan asersinya bisa gagal — ubah satu expected value, pastikan merah,
   kembalikan