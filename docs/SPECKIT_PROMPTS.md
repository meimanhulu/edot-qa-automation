# Spec-Kit Prompts — eDOT QA Automation Take-Home

Urutan: **constitution → specify → plan → tasks → implement**.
Jalankan satu per satu, review hasilnya, baru lanjut.

> Ini project **greenfield** — beda dengan K6 yang brownfield. Constitution-nya preskriptif: menetapkan aturan sebelum ada kode.

---

# 1️⃣ `/speckit-constitution`

```
/speckit-constitution
```

Buat constitution untuk **eDOT QA Automation Take-Home Test (V4)** — suite automation testing untuk web dan mobile, dengan AI di dalam suite.

Ini project baru dari nol, deadline **3 hari**. Constitution harus menetapkan aturan yang mencegah kesalahan yang secara eksplisit disebut penilai sebagai kegagalan.

## Konteks

| | |
|---|---|
| **Web** | eSuite (`https://esuite.edot.id`) — Playwright + Pytest |
| **Mobile** | eWork SFA (Play Store) — Maestro + Pytest wrapper |
| **Bahasa** | Python + Pytest saja. **Selenium dan Appium tidak diterima** |
| **Reporting** | Allure, untuk web dan mobile dalam satu run |
| **Deadline** | 3 hari |

## Principle yang Harus Ada

### P1 — Integritas Asersi (paling utama)
Asersi tidak boleh dilemahkan, dilewati, atau diubah agar lolos. Test yang gagal **tetap gagal**.

Tingkatan asersi:
- **Tier 1** — navigasi/tampilan. Cukup pastikan elemen terlihat.
- **Tier 2** — setiap test yang membuat, mengubah, atau menghapus data. **Wajib** memverifikasi outcome DAN datanya: record ada, dan tiap nilainya (nama, email, telepon, alamat, dst) sama persis dengan yang diinput. **Toast sukses saja TIDAK CUKUP.** Untuk delete: pastikan record hilang. Untuk edit: pastikan nilainya berubah.
- **Negative** — verifikasi pesan error yang spesifik, bukan sekadar form masih terbuka.

Tiap asersi Tier 2 di kode WAJIB diberi komentar penanda, agar reviewer bisa membedakan bug produk dari cacat skrip sekali lihat.

*Rationale:* penilai menyatakan kedalaman asersi sebagai satu dari dua hal yang paling menentukan nilai, dan "suite hijau karena asersi tidak bisa gagal" sebagai non-negotiable failure.

### P2 — Kejujuran Cakupan
Lebih baik **tiga skenario yang benar-benar memverifikasi perilaku** plus catatan jujur soal yang tidak selesai, daripada lima yang semuanya lolos karena asersinya dangkal.

Skenario yang tidak selesai WAJIB ditulis eksplisit di README beserta alasannya. Dilarang menutupinya dengan asersi yang dilemahkan.

### P3 — AI Tidak Boleh Menyentuh Asersi
AI hadir di dalam suite, tapi dengan batas keras:
- Dilarang melemahkan, melewati, atau menulis ulang asersi
- Dilarang menelan kegagalan dalam `try/except`
- Dilarang mengubah expected value agar cocok dengan actual
- Verdict triage adalah **usulan untuk manusia** — dilarang membuat bug report otomatis, dilarang menutup apa pun otomatis

### P4 — Rahasia Tidak Pernah Masuk Repo
Kredensial dan API key hanya dari environment variable. Yang di-commit hanya `.env.example` berisi nama variabel tanpa nilai. Berlaku untuk kredensial eSuite, kredensial mobile, dan API key model.

### P5 — Tanpa Sleep
Dilarang `time.sleep()`. Web memakai auto-waiting Playwright dan `expect()`. Mobile memakai perintah wait Maestro.

*Rationale:* sleep menyembunyikan race condition dan membuat suite lambat sekaligus rapuh. Cascade dropdown pada form Create Company adalah tempat paling rawan.

### P6 — Disiplin Locator
**Web**, urutan prioritas: `data-testid` → role + accessible name → atribut stabil (`name`/`id`/`aria-*`) → text sebagai pilihan terakhir **dengan justifikasi di komentar**.

**Mobile**, urutan prioritas: `id` → id regex → text → accessibilityText → composite → point. Tap koordinat adalah pilihan terakhir dan **wajib dijustifikasi di komentar**.

Locator hanya boleh berada di page class (web) dan di YAML flow (mobile). **Dilarang ada selector mentah di berkas test.**

### P7 — Lingkungan Bersama, Wajib Bersih
Data test yang tertinggal dihitung sebagai kegagalan. Cleanup WAJIB berjalan **bahkan saat test gagal** — pakai fixture dengan teardown, bukan langkah terakhir di dalam badan test.

### P8 — Setiap Baris Harus Bisa Dijelaskan
Dilarang menyerahkan kode yang tidak bisa dijelaskan barisnya. Kode dari AI atau contoh yang tidak dipahami harus ditulis ulang sendiri sampai paham.

*Rationale:* penilai menyatakan ketidakmampuan menjelaskan kode akan diperlakukan sebagai bukan karya sendiri.

### P9 — Login Sekali, Bagikan Sesi
Web login satu kali per sesi, bagikan lewat `storage_state`. Dilarang login di dalam tiap test.

### P10 — AI Harus Tetap Jalan Tanpa AI
Modul data AI wajib punya fallback deterministik (Faker) yang otomatis dipakai saat API key tidak ada, sehingga suite tetap jalan offline dan di CI. Output AI wajib divalidasi terhadap schema sebelum dikonsumsi test; kalau tidak valid, tolak dan ulangi, atau jatuh ke fallback.

## Batasan Teknis

- **Python + Pytest.** Selenium dan Appium dilarang.
- **Page Object Model** untuk web. **Sub-flow `runFlow`** untuk mobile — apa pun yang dipakai ulang, terutama login, wajib diekstrak.
- Flow mobile berupa YAML; wrapper Pytest yang memanggilnya, sehingga web dan mobile masuk ke satu run Allure.
- Kredensial dan data test mobile dilewatkan sebagai environment variable. **Dilarang hardcode di YAML.**
- Screenshot dilampirkan ke Allure saat gagal.

## Governance

- Perubahan constitution butuh persetujuan eksplisit pemilik project
- Setiap plan wajib punya bagian "Constitution Check" yang menguji tiap principle
- Pelanggaran principle harus dicatat eksplisit dengan justifikasi

---

# 2️⃣ `/speckit-specify`

```
/speckit-specify
```

Bangun suite automation testing untuk eDOT: web (eSuite) dan mobile (eWork SFA), dengan AI di dalam suite.

## Cakupan

### Web — eSuite (`https://esuite.edot.id`)

Login tiga layar: klik "Use Email or Username" → submit email → submit password. Ada redirect melalui eDOT Account Center lalu kembali — page object harus memperhitungkan ini.

Kredensial dari environment variable (nilainya ada di lembar soal, jangan di-commit).

**Skenario:**

1. **Login** — verifikasi salam dashboard "Welcome Back," tampil. *(Tier 1)*

2. **Create company** — Companies → "+ Add Company" membuka wizard Register Company 3 langkah. Step 1 butuh: Company Name, Email, Phone, Industry Type, Company Type, Language, Street Address, dan cascade dependen **Country → Province → City → District → Zone → Postal Code**. Tombol Next tetap disabled sampai step valid. Data dummy dari modul AI (Phase 3A).

3. **Verify detail** *(Tier 2)* — buka lewat Companies → Manage, verifikasi **field per field**: name, industry type, company type, address, postal code, email, phone. Ini skenario paling bernilai; kerjakan paling teliti.

4. **Cleanup** — hapus company di akhir run. Lingkungan bersama; data tertinggal mengurangi nilai.

### Mobile — eWork SFA

Kredensial: utamakan company yang dibuat di skenario web (company baru dapat trial 30 hari, jadi aktif). Fallback (mungkin sudah kedaluwarsa): Company ID `5049209`, user `salesmanqaauto`, password dari env. **Kalau memakai fallback, tulis di README.**

**Skenario:**

5. **Login** — verifikasi dashboard tampil. *(Tier 1)*
6. **Create customer** — input data, verifikasi muncul dengan benar setelah dibuat. *(Tier 2)*

### AI 3A — Generator Data Test

Modul yang meminta model menghasilkan data bisnis Indonesia yang koheren dan realistis:
- **Company:** nama legal, email, telepon, alamat jalan, industri
- **Customer:** nama, kontak, alamat

Wajib:
- Validasi output terhadap schema sebelum dikonsumsi test
- Tolak dan ulangi, atau jatuh ke fallback, saat output malformed
- Fallback deterministik (Faker) otomatis dipakai saat tidak ada API key
- Data yang benar-benar dipakai dilampirkan ke Allure

### AI 3B — Triage Kegagalan

Skrip yang berjalan **setelah** suite, membaca hasil Allure, dan untuk tiap kegagalan memberi verdict: **cacat skrip/environment**, **bug produk**, atau **flaky**.

Urutan penelusuran bukti — berhenti di kecocokan pertama:
1. Exception (element not found, timeout) atau asersi gagal? Exception hampir selalu skrip/environment, bukan bug.
2. Apakah locator menunjuk elemen yang dimaksud, dan unik?
3. Apakah semua langkah sebelum asersi berhasil, dan prakondisi terpenuhi?
4. Apakah expected value-nya sendiri benar menurut test case?
5. Apakah berulang konsisten, atau kadang saja? Intermiten berarti flaky, bukan bug.

Output berupa laporan triage (Markdown atau HTML) berisi verdict dan bukti pendukungnya untuk tiap kegagalan.

## Deliverable

| Deliverable | Isi |
|---|---|
| **Dokumen test case** | Google Sheet/Excel, web + mobile, kolom: Test Case ID, Title, Precondition, Test Steps, Test Data (nilai persis), Expected Result, Assertion Tier, Status (kosongkan). Link GitHub repo di dalamnya. |
| **Repo GitHub** | Struktur modular, kode web, kode mobile, dua modul AI, setup Allure, README.md, AI_USAGE.md |
| **Bukti eksekusi** | Laporan Allure dari minimal satu run web penuh, **plus laporan triage dari run yang sengaja digagalkan** — rusakkan sesuatu dengan sengaja (mis. arahkan locator ke elemen yang salah) supaya terlihat triage-nya bekerja |

**AI_USAGE.md wajib memuat:** model apa dan kenapa; di mana AI berjalan (saat menulis test / saat run / setelah run); prompt persis yang dikirim; apa yang terjadi saat AI tidak tersedia atau mengembalikan output tidak valid; apa yang sengaja **tidak** diserahkan ke AI, dan kenapa.

## Kriteria Sukses

1. Asersi Tier 2 benar-benar bisa gagal — diverifikasi dengan sengaja merusak data/locator
2. Kedua kapabilitas AI bekerja, dengan schema validation dan fallback yang terbukti
3. Nol kredensial atau API key di repo
4. Nol data test tertinggal di lingkungan bersama
5. Reviewer bisa mengikuti apa yang dikerjakan dari README dan AI_USAGE.md
6. Setiap baris kode bisa dijelaskan pemiliknya

## Di Luar Cakupan

- Skenario di luar enam yang disebut di atas
- Optimasi performa suite
- Bonus (CI pipeline, eksekusi paralel, data handoff web→mobile) — dikerjakan hanya jika waktu tersisa

---

# 3️⃣ `/speckit-plan`

```
/speckit-plan
```

Buat implementation plan. **Deadline 3 hari** — plan wajib memperhitungkan waktu, bukan hanya kelengkapan teknis.

## Struktur Repo

```
edot-qa-automation/
├── README.md
├── AI_USAGE.md
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
├── conftest.py                    fixture global: storage_state, allure, cleanup
├── web/
│   ├── pages/                     Page Object — SATU-SATUNYA tempat locator
│   │   ├── base_page.py
│   │   ├── login_page.py
│   │   ├── companies_page.py
│   │   ├── register_company_wizard.py
│   │   └── company_detail_page.py
│   ├── tests/
│   │   ├── test_login.py
│   │   ├── test_create_company.py
│   │   └── test_verify_company_detail.py
│   └── conftest.py
├── mobile/
│   ├── flows/                     YAML Maestro
│   │   ├── shared/login.yaml      sub-flow dipakai ulang via runFlow
│   │   ├── login.yaml
│   │   └── create_customer.yaml
│   ├── tests/
│   │   ├── test_mobile_login.py
│   │   └── test_create_customer.py
│   └── runner.py                  wrapper pemanggil maestro
├── ai/
│   ├── data_generator.py          3A — generator data
│   ├── schemas.py                 validasi schema
│   ├── fallback.py                Faker, dipakai saat tanpa API key
│   └── triage.py                  3B — triage kegagalan
└── docs/
    └── test-cases.xlsx
```

## Pendekatan Teknis

**Page Object.** `base_page.py` memuat helper bersama (navigasi, tunggu, screenshot). Tiap page class mengekspos method bermakna bisnis (`fill_step_one`, `get_detail_values`), bukan locator mentah. Berkas test tidak pernah menyentuh selector.

**Cascade dropdown** — bagian paling rawan flaky. Polanya: pilih parent → **tunggu opsi child benar-benar terisi** → baru pilih. Jangan pakai sleep, jangan asal klik berurutan. Pakai `expect()` yang menunggu jumlah opsi bertambah atau opsi spesifik muncul.

**Verifikasi Tier 2** — page detail mengembalikan `dict` berisi seluruh field, lalu dibandingkan dengan `dict` data yang diinput. Satu perbandingan per field dengan pesan jelas, bukan satu asersi gabungan — supaya kegagalan langsung menunjuk field mana.

**Cleanup** — fixture `yield` dengan teardown. Berjalan meski test gagal. Simpan ID company yang dibuat, hapus di teardown, verifikasi terhapus.

**Auth** — fixture session-scoped: login sekali, simpan `storage_state`, semua test memakainya.

**AI data (3A)** — panggil model, validasi terhadap schema (Pydantic), retry sekali kalau tidak valid, jatuh ke Faker kalau tetap gagal atau tidak ada API key. Lampirkan data yang benar-benar dipakai ke Allure.

**AI triage (3B)** — baca `allure-results/*.json`, untuk tiap kegagalan telusuri lima langkah bukti berurutan, hasilkan Markdown berisi verdict + bukti. Tidak menyentuh test, tidak membuat bug report.

## Urutan Pengerjaan dengan Timebox

| Hari | Fokus | Timebox |
|---|---|---|
| **1** | Dokumen test case (Phase 1) + struktur repo + Allure + login web dengan `storage_state` | Test case 3 jam, sisanya 5 jam |
| **2** | Create company (wizard + cascade) → **Verify detail Tier 2** → cleanup fixture → AI data 3A | Verify detail dapat porsi terbesar |
| **3** | AI triage 3B → mobile (timebox 4 jam) → run sengaja gagal + laporan triage → README + AI_USAGE.md | Mobile dipotong keras di 4 jam |

**Alasan urutan ini:** dokumen test case dikerjakan lebih dulu karena deliverable terpisah dan memaksa memikirkan asersi sebelum ngoding. Verify detail Tier 2 dapat porsi terbesar karena penilai menyebutnya penentu nilai. Mobile ditimebox keras karena Maestro di Windows butuh WSL + emulator + install app — berisiko menelan satu hari penuh.

**Kalau mobile tidak selesai:** tetap tulis YAML flow + pytest wrapper (artefak yang bisa dinilai), lalu catat jujur di README. Ini sejalan dengan P2, bukan pelanggaran.

## Constitution Check

| Principle | Cara dipenuhi | Cara diverifikasi |
|---|---|---|
| P1 Integritas asersi | Tier 2 field-by-field, komentar penanda | Sengaja ubah satu nilai → test wajib gagal |
| P2 Kejujuran cakupan | Catatan eksplisit di README | Review manual |
| P3 AI tidak sentuh asersi | Triage read-only, output Markdown | Review kode triage |
| P4 Rahasia | `.env` + `.env.example` | `git ls-files` bersih |
| P5 Tanpa sleep | `expect()` dan wait Maestro | `grep -r "sleep(" ` harus kosong |
| P6 Locator | Hanya di page class / YAML | `grep` selector di berkas test harus kosong |
| P7 Cleanup | Fixture teardown | Sengaja gagalkan test → cleanup tetap jalan |
| P8 Bisa dijelaskan | Review sendiri tiap modul | Uji diri: tutup editor, jelaskan |
| P9 Login sekali | Fixture session-scoped | Hitung request login di satu run |
| P10 Fallback AI | Faker otomatis | Jalankan tanpa API key → suite tetap jalan |

## Risiko

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Maestro di Windows tidak jalan | Mobile hilang | Timebox 4 jam, tetap serahkan YAML + wrapper + catatan jujur |
| Cascade dropdown flaky | Test tidak andal | Tunggu opsi terisi, bukan sleep; jalankan 3x untuk pastikan stabil |
| Cleanup gagal saat test gagal | Data tertinggal (non-negotiable) | Fixture teardown, diuji dengan sengaja menggagalkan test |
| Kredensial fallback kedaluwarsa | Mobile login gagal | Utamakan company hasil skenario web |
| Waktu habis di mobile | Web ikut tidak selesai | Web selesai lebih dulu, mobile terakhir |

---

# 4️⃣ `/speckit-tasks`

```
/speckit-tasks
```

Pecah plan menjadi task yang bisa dieksekusi.

## Aturan Penyusunan

- **Satu task = satu commit.**
- Tiap task punya kriteria verifikasi yang bisa dijalankan, bukan sekadar "selesai".
- Tandai `[NEEDS DECISION]` untuk yang butuh keputusan saya.
- Tandai `[P]` untuk yang bisa paralel.
- **Cantumkan estimasi waktu tiap task** dan tandai mana yang boleh dipotong kalau waktu habis.

## Fase

**Fase 0 — Dokumen test case (Phase 1)**
Enam skenario, kolom lengkap sesuai spec, Assertion Tier diisi benar. Ini deliverable terpisah — selesaikan utuh sebelum ngoding.

**Fase 1 — Fondasi**
Struktur repo, `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, Allure jalan, `base_page.py`.

**Fase 2 — Login web + storage_state**
Login tiga layar termasuk redirect Account Center. Fixture session-scoped. Verifikasi hanya ada satu login per run.

**Fase 3 — AI data generator (3A)**
Schema, generator, fallback Faker, lampiran Allure. Uji dengan dan tanpa API key.

**Fase 4 — Create company**
Wizard 3 langkah, cascade dropdown. Verifikasi kestabilan dengan menjalankan 3 kali berturut-turut.

**Fase 5 — Verify detail Tier 2** ← paling bernilai
Perbandingan field per field. **Wajib diuji bisa gagal:** ubah satu nilai yang diharapkan, pastikan test merah, kembalikan.

**Fase 6 — Cleanup fixture**
Teardown yang jalan meski test gagal. Uji dengan sengaja menggagalkan test.

**Fase 7 — AI triage (3B)**
Baca hasil Allure, lima langkah bukti, output Markdown.

**Fase 8 — Mobile (timebox 4 jam)**
YAML flow + sub-flow login + wrapper Pytest. Kalau eksekusi terkendala, tetap serahkan artefaknya + catatan jujur.

**Fase 9 — Bukti eksekusi**
Run web penuh → laporan Allure. Lalu **sengaja rusakkan satu locator** → run → laporan triage. Keduanya wajib diserahkan.

**Fase 10 — Dokumentasi**
README (dependency, `playwright install`, Maestro CLI, emulator/adb, cara menjalankan tiap suite, cara membuat dan membuka Allure) + AI_USAGE.md lengkap sesuai lima poin di spec.

## Verifikasi per Task

```
[ ] Kriteria fungsional terpenuhi
[ ] Tidak ada sleep()
[ ] Tidak ada selector di berkas test
[ ] Tidak ada kredensial di kode
[ ] Asersi Tier 2 (bila ada) terbukti bisa gagal
[ ] Saya bisa menjelaskan setiap baris
```

---

# 5️⃣ `/speckit-implement`

```
/speckit-implement
```

Eksekusi task list. Ikuti aturan berikut ketat-ketat.

## Yang Dilarang Keras

1. Melemahkan, melewati, atau menulis ulang asersi agar test lolos
2. Mengubah expected value agar cocok dengan actual
3. Menelan kegagalan dalam `try/except`
4. `time.sleep()` di mana pun
5. Selector mentah di berkas test
6. Kredensial atau API key di kode maupun YAML
7. Membuat triage yang mengubah test, membuat bug report, atau menutup apa pun
8. Menambah skenario di luar enam yang disebut

## Yang Wajib

- **Tiap asersi Tier 2 diberi komentar penanda** — reviewer harus bisa membedakan bug produk dari cacat skrip sekali lihat
- **Tiap locator text-based diberi justifikasi di komentar** — kenapa tidak pakai prioritas yang lebih tinggi
- **Tiap tap koordinat di Maestro diberi justifikasi**
- Cleanup lewat fixture teardown, bukan langkah di dalam test

## Ritme Kerja

Kerjakan **satu task, lalu berhenti dan laporkan**. Untuk Fase 5 (Verify detail Tier 2), tunggu konfirmasi saya sebelum lanjut — itu bagian paling menentukan nilai.

Format laporan tiap task:

```
Task        : <id> — <nama>
Berkas      : <yang dibuat/diubah>
Verifikasi  : [✓/✗] fungsional  [✓/✗] no sleep  [✓/✗] no selector di test  [✓/✗] no secret
Tier 2      : <asersi apa, dan bagaimana dibuktikan bisa gagal>
Perlu keputusan : <apa, atau "tidak ada">
```

## Berhenti dan Tanya Kalau

- Struktur halaman berbeda dari yang dijelaskan spec
- Cascade dropdown berperilaku tidak seperti dugaan
- Ada yang menggoda untuk dilemahkan asersinya agar hijau — **jangan, laporkan saja**
- Waktu menipis dan perlu memutuskan apa yang dipotong

## Catatan Penting

Setelah tiap modul selesai, saya akan menutup editor dan menjelaskan kodenya tanpa melihat. Kalau ada yang tidak bisa saya jelaskan, modul itu ditulis ulang. Jadi **utamakan kode yang jelas dan sederhana** daripada yang pintar tapi padat.

Mulai dari **Fase 0**.
