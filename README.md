# eDOT QA Automation — Take-Home Test V4

Suite automation testing untuk **eSuite (web)** dan **eWork SFA (mobile)**,
dengan AI di dalam suite — generasi data test dan triage kegagalan.

**Repository:** https://github.com/meimanhulu/edot-qa-automation

---

## Ringkasan hasil

| Suite | Hasil |
|---|---|
| **Web** (Playwright) | 17 Passed · 2 Failed |
| **Mobile** (Maestro) | 2 Passed  |

| Evidence | Lokasi |
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

Maestro sejak 1.39.9 berjalan **native di Windows**; WSL tidak diperlukan.

```powershell
Invoke-WebRequest -Uri "https://github.com/mobile-dev-inc/maestro/releases/latest/download/maestro.zip" -OutFile "$env:USERPROFILE\Downloads\maestro.zip"
Expand-Archive "$env:USERPROFILE\Downloads\maestro.zip" -DestinationPath "C:\maestro"
$env:PATH += ";C:\maestro\maestro\bin"
maestro --version
```

Prasyarat: emulator Android dengan system image **Google Play** (agar eWork SFA
dapat dipasang dari Play Store), dan `adb devices` mengenalinya.

Kredensial mobile di `.env`:

```
EWORK_APP_ID=id.edot.ework
EWORK_COMPANY_ID=...
EWORK_USERNAME=...
EWORK_PASSWORD=...
```

Kredensial yang dipakai adalah **akun fallback** dari brief (Company ID
`5049209`), bukan company hasil skenario web — company tersebut dihapus di
akhir setiap run web sesuai persyaratan pembersihan data.

### Allure

```powershell
npm install -g allure-commandline
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
conftest.py              fixture bersama; satu-satunya pembaca os.environ
web/pages/               Page Object — satu-satunya tempat locator
web/tests/               test Playwright
mobile/flows/            YAML Maestro
  shared/login.yaml      sub-flow login, dipanggil runFlow
  login.yaml             TC-MOB-001
  create_customer.yaml   TC-MOB-002 — orkestrator
  steps/location.yaml    step 2: alamat + cascade wilayah
  steps/documents.yaml   step 3: KTP + capture foto
  steps/signature.yaml   tanda tangan, konfirmasi, layar sukses
mobile/runner.py         wrapper Pytest → Maestro
ai/                      3A generator data · 3B triage kegagalan
scripts/                 entry point triage
tools/                   pembersih data sisa
docs/                    walkthrough kode, panduan Maestro, bukti eksekusi
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
| **Nol tap koordinat di suite mobile** | Seluruh elemen diakses lewat `resource-id` |
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
| | **Detail page memuat data tanpa reload** | 1 | ⚠️ **intermiten — cacat produk** |
| Company name tersimpan ter-trim | 2 | ❌ **cacat produk** |
| Delete company | 2 | ✅ |

### Mobile — eWork SFA

| Skenario | Tier | Status |
|---|---|---|
| **TC-MOB-001** Login — dashboard tampil | 1 | ✅ |
| **TC-MOB-002** Create customer — end-to-end sampai muncul di daftar | 2 | ✅ |

`TC-MOB-002` menjalankan alur pendaftaran penuh:

```
Basic  →  Locations  →  Documents  →  Approval Signature  →  Register
   ↓                                                            ↓
data outlet, kontak,                          "Are you sure to save
sales information                              this customer data?" → Yes
                                                             ↓
                                              "Data Saved Successfully"
                                                             ↓
                                       New Customer List → nama ditemukan
```

Sebelas assertion Tier 2 di sepanjang alur: outlet name, phone, email, contact
person, channel type, customer type, pricelist, address type, address, nomor
KTP, dan — yang terpenting — **nama customer ditemukan di daftar setelah
pendaftaran selesai**, sesuai permintaan brief *"assert it appears correctly
after creation"*.

Seluruh data diacak tiap run: nama outlet, nomor telepon, email berdomain
gmail, nama contact person, jenis alamat, alamat jalan, dan NIK 16 digit
berstruktur sah. Test yang memakai nilai tetap bisa lolos karena record lama,
bukan karena input baru benar-benar diterima.

---

## Cacat produk yang ditemukan

### 1. Nama company disimpan tanpa dipangkas spasi

**Test:** `TC-WEB-008` — gagal konsisten.

Nama yang diinput dengan spasi di depan dan belakang tersimpan apa adanya:

```
input  : '   PT Nusantara Jaya 1062   '
stored : '   PT Nusantara Jaya 1062   '
```

Di layar keduanya tampil identik, tetapi tersimpan sebagai record berbeda.
Akibatnya pencarian dengan pencocokan persis meleset, dan dua company yang
terlihat sama bisa berdampingan tanpa pengguna menyadarinya.

Cacat ini hanya terlihat karena asersinya memakai `==`, bukan `in`.
Perbandingan parsial justru akan meloloskannya — `'PT Nusantara Jaya 1062'`
memang terkandung di dalam `'   PT Nusantara Jaya 1062   '`.

### 2. Halaman detail company tidak memuat data pada pembukaan pertama

**Test:** `TC-WEB-013d` — gagal secara sengaja selama cacatnya ada.

Setelah company dibuat, membukanya lewat Companies → Manage **kadang**
menampilkan form kosong seluruhnya: Company Name kosong, Company ID kosong,
seluruh dropdown masih `Choose ...`. Data baru muncul setelah halaman dimuat
ulang, tanpa petunjuk apa pun bagi pengguna.

Perilakunya **intermiten**, bukan konsisten — pada sebagian run halaman termuat
normal pada pembukaan pertama. Karena itu `TC-WEB-013d` kadang lolos dan kadang
gagal, dan justru itulah nilainya: ia merekam frekuensi kemunculannya alih-alih
mengklaim sesuatu yang lebih pasti daripada buktinya.

Suite melakukan reload otomatis agar verifikasi Tier 2 tetap berjalan. Reload
itu **dicatat, tidak disembunyikan** — lampiran Allure bernama
*"TEMUAN: detail page perlu reload"* muncul tiap kali reload dibutuhkan.

Cacat ini kemungkinan besar terlewat oleh pengujian manual: pengguna biasanya
tidak membuka halaman detail sedetik setelah membuat company.

### 3. Nomor telepon salah format ditolak tanpa pesan

Field Phone menampilkan `+62` sebagai prefix terpisah, sehingga hanya menerima
nomor lokal diawali `8`. Format `021...`, `+62...`, atau berawalan `0` membuat
tombol Next **terkunci tanpa pesan error apa pun**.

Ditangkap oleh schema validation di `ai/schemas.py` supaya kegagalan menyebut
penyebab sebenarnya, bukan berupa timeout yang membingungkan.

### 4. Waktu respons eSuite tidak konsisten

Sebagian navigasi selesai dalam hitungan detik, sebagian melewati 30 detik dan
menampilkan `"Please wait..."` berkepanjangan. Test yang gagal karena ini
berganti-ganti tiap run — ciri lingkungan yang lambat, bukan cacat pada satu
halaman tertentu.

Suite menaikkan timeout navigasi ke 60 detik dan `expect()` ke 15 detik agar
kegagalan yang tersisa benar-benar berasal dari perilaku aplikasi. Bagi
pengguna, keterlambatan seperti ini terasa seperti aplikasi yang menggantung.

### 5. Navigasi mobile "New Customer" tidak konsisten

Mengetuk menu New Customer di dashboard kadang membuka daftar customer, kadang
tetap di dashboard tanpa pesan apa pun. Dibungkus `retry` di YAML — ditangani
tanpa melemahkan asersi, karena yang diperiksa tetap kehadiran elemen tujuan.

### 6. Aksesibilitas (web)

- Seluruh combobox tanpa `aria-label`, `aria-labelledby`, maupun `title` —
  pengguna screen reader tidak mendapat informasi apa pun tentang fungsi
  tiap dropdown
- Dialog "Add Legal Document" memasang `aria-hidden="true"` pada elemen yang
  masih memegang focus. Peringatan Chrome: *"Blocked aria-hidden on an element
  because its descendant retained focus"*

### 7. Usability daftar company (web)

Empat hal yang saling memperburuk: **tanpa pagination** (470+ company dalam satu
halaman), **render bertahap** (kartu muncul hanya saat digulir), **company baru
di paling bawah**, dan **tanpa kolom pencarian**.

Akibatnya pengguna harus menggulir melewati ratusan kartu untuk melihat company
yang baru saja ia buat.

---

## Temuan saat inspeksi — berbeda dari brief

### Web nol penanda test; mobile justru sebaliknya

| Platform | Temuan |
|---|---|
| **Web** | Nol `data-testid`, nol accessible name pada combobox, `id` bernilai `radix-:rd:` yang di-generate ulang tiap render |
| **Mobile** | `resource-id` bersih dan stabil di seluruh layar — termasuk kanvas tanda tangan dan tombol capture kamera |

Konsekuensinya di web: input memakai `get_by_placeholder()`, tombol memakai
`role` + accessible name, dan combobox terpaksa memakai indeks. Di mobile,
seluruh elemen dapat diakses lewat prioritas pertama menurut brief.

### Alur login web

| Brief | Kenyataan |
|---|---|
| Tombol "Continue" lalu "Sign In" | **Keduanya bertuliskan "Log In"** |
| — | OIDC di `cronus.edot.id/oidc/interaction/<id>`; interaction id berubah tiap sesi |
| — | `input[name=password]` sudah ada sebagai `type=hidden` di layar username — locator wajib `:visible` |

### Wizard Register Company (web)

| Brief | Kenyataan |
|---|---|
| Cascade langsung tampil di Step 1 | Baru **muncul setelah Country dipilih** |
| Level keempat "Zone" | Namanya **"Sub District"** |
| Postal Code dipilih | **Terisi otomatis**; elemennya combobox disabled |
| — | Memilih Country ≠ Indonesia mengubah struktur cascade (Philippines: Region → Province → City → Barangay) dan prefix telepon |
| — | Step 3 mengaku opsional, tetapi Branch Name bertanda wajib — kontradiksi di UI |

### Form New Customer (mobile)

Empat langkah, bukan satu: Basic → Locations → Documents → Approval Signature.
Kamera untuk lampiran berada **di dalam aplikasi**, bukan aplikasi kamera
Android — sehingga `btn_capture` punya `resource-id` sendiri dan capture foto
tetap bebas dari tap koordinat.

Tanda tangan digores dengan `swipe` yang diarahkan lewat `from: id:`, bukan
titik koordinat. Kehadiran tombol *Repeat Signature* dipakai sebagai penanda
bahwa aplikasi benar-benar menerima goresan.

---

## Pembagian tanggung jawab data test

| Sumber | Field |
|---|---|
| **Modul AI (3A)** | Nama, email, telepon, alamat — company dan customer |
| **Opsi aplikasi** | Cascade wilayah di kedua platform; dipilih opsi pertama tiap level |
| **Data test** | Country (web), Channel Type (mobile) — ditetapkan eksplisit |
| **Aplikasi (otomatis)** | Postal Code, Company ID |

Nilai cascade diambil dari opsi yang disediakan aplikasi karena validitasnya
hanya dapat ditentukan saat runtime — daftar District untuk satu City berbeda
dari City lain. Menentukannya di data test akan gagal begitu induknya berbeda,
dan kegagalannya berupa *"Element not found"* yang menyesatkan: salah data,
bukan salah aplikasi.

Nilai yang terpilih **dibaca balik** dan dipakai sebagai expected value Tier 2.

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

Verdict pada run terakhir suite web:

| Verdict | Jumlah |
|---|---|
| kandidat product bug | 3 |
| script/environment defect | 1 |

Dua di antaranya, berdasarkan peninjauan manual, lebih tepat dikategorikan
**flaky** — kegagalannya berasal dari waktu render, bukan perilaku aplikasi
yang salah. Ini justru contoh mengapa brief mensyaratkan verdict sebagai usulan
untuk manusia: penelusuran bukti otomatis tidak dapat membedakan "assertion
gagal karena bug" dari "assertion gagal karena elemen belum ter-render".

---

## Pelajaran teknis

| Pola | Contoh | Konsekuensi |
|---|---|---|
| **Elemen tersembunyi sudah ada di DOM** | `input[name=password]` di layar username; combobox cascade sebelum Country dipilih | Locator berbasis indeks wajib `:visible` |
| **Render asinkron** | tombol validasi, Postal Code, kartu company | Pemeriksaan seketika (`is_enabled`, `count`) diganti polling (`expect`) |
| **Disclosure bertingkat** | cascade muncul setelah Country; field branch setelah Branch Name | Urutan pengisian tidak boleh sembarang |
| **Aksi berisiko dikunci checkbox** | Register di Step 3; Confirm pada dialog Delete | Checkbox persetujuan wajib dicentang lebih dulu |

Tiga keputusan yang layak disebut:

**Nol pemakaian `networkidle`.** Playwright menyarankan menghindarinya untuk
SPA, dan eSuite memuat data lewat XHR yang berjalan terus sehingga kondisi
"jaringan tenang" tidak pernah tercapai. Penggantinya penanda spesifik: URL
berubah, elemen tujuan muncul, atau tombol kembali enabled.

**Maestro memerlukan flag `-e`, bukan environment proses.** Dengan environment
proses saja, `appId: ${EWORK_APP_ID}` terbaca sebagai `undefined` dan flow gagal
dengan *"Package undefined is not installed"*. Flag `-e` diteruskan sampai ke
sub-flow yang dipanggil `runFlow`.

**Verifikasi dilakukan di tempat, bukan digulir balik.** `NestedScrollView`
Android melepas view yang keluar layar dari hierarchy, sehingga menggulir
kembali untuk memverifikasi berarti mencari elemen yang sudah tidak ada di
pohon. Assert tepat setelah input menghilangkan seluruh gulir balik — dan
membuat kegagalan menunjuk langsung ke field yang bermasalah.

---

## Catatan atas dua test web yang masih flaky

`test_delete_company` dan `test_company_name_stored_trimmed` lolos bila
dijalankan sendiri, tetapi gagal saat suite penuh dijalankan. Penyebabnya render
bertahap pada daftar company — kartu yang baru dibuat butuh waktu muncul, dan
waktunya bertambah seiring jumlah company yang menumpuk.

Sudah dimitigasi dengan `scroll_to_load_all()` dan polling `expect()`, tetapi
belum sepenuhnya stabil. **Tidak ditutupi dengan melemahkan asersi**

## Data test di shared environment

**Web:** fixture `created_company` menghapus company di teardown, dan
`test_delete_company` memverifikasi penghapusan secara eksplisit. Run yang gagal
di tengah fixture tidak sempat menjalankan teardown, sehingga selama
pengembangan sempat ada company yang tertinggal; semuanya sudah dibersihkan, dan
`tools/cleanup_orphans.py` tersedia untuk pembersihan susulan.

**Mobile:** customer yang dibuat `TC-MOB-002` tersimpan permanen — aplikasi
tidak menyediakan jalur penghapusan dari sisi pengguna. Ini konsekuensi dari
memenuhi persyaratan brief yang meminta verifikasi *"after creation"*. Statusnya
*Waiting for Approval*, dan aplikasi menyatakan data diunggah ke server saat
koneksi tersedia.

---

## Menambah skenario baru

**Web:**
1. Buat page class di `web/pages/` — locator hanya di sini
2. Ekspos method bermakna bisnis, bukan locator mentah
3. Kembalikan **keadaan**, jangan assert di dalam page object
4. Tulis test di `web/tests/` yang memanggilnya

**Mobile:**
1. Ambil selector lewat `maestro hierarchy` — jangan menebak
2. Pecah langkah panjang jadi sub-flow di `mobile/flows/steps/`
3. Assert **tepat setelah input**, jangan menggulir balik
4. Lewatkan data lewat variabel dari wrapper Pytest

Berlaku untuk keduanya:
- Beri komentar `# Tier 2:` pada asersi yang memverifikasi data
- Buktikan asersinya bisa gagal — ubah satu expected value, pastikan merah,
  kembalikan