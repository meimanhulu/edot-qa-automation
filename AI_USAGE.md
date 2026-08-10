# AI_USAGE.md

Dokumentasi pemakaian AI di dalam suite ini, sesuai lima poin yang diminta brief.

---

## 1. Model yang dipakai dan alasannya

**Model:** `claude-sonnet-4-6` (Anthropic API), dipanggil lewat `ai/data_generator.py`.

**Alasannya:**

- **Kualitas output JSON.** Modul ini meminta objek JSON murni tanpa penjelasan.
  Model yang konsisten mengembalikan JSON valid mengurangi jumlah retry, dan
  retry adalah pemborosan token yang paling mudah dihindari.
- **Pemahaman konteks Indonesia.** Data yang dibutuhkan harus koheren secara
  geografis — kota harus benar-benar berada di provinsi yang disebut, kode pos
  harus milik wilayah tersebut. Model yang mengenal wilayah Indonesia
  menghasilkan data yang lolos validasi lebih sering.
- **`max_tokens=512`.** Dibatasi sengaja: satu objek JSON kecil tidak butuh
  lebih, dan batas ini mencegah biaya membengkak bila model mulai menjelaskan.

**Catatan penting:** suite ini **tidak bergantung** pada model tertentu. Bila
`AI_API_KEY` kosong, seluruh test tetap berjalan lewat jalur fallback Faker.
Itu bukan mode darurat melainkan jalur utama saat CI berjalan.

---

## 2. Di mana AI berjalan

| Fase | AI dipakai? | Untuk apa |
|---|---|---|
| Saat menulis test | ❌ tidak | Locator dan asersi ditulis manual setelah inspeksi DOM. Lihat bagian 5. |
| **Saat run berlangsung** | ✅ ya | **Phase 3A** — menghasilkan data company dan customer sebelum test mengisinya ke form |
| **Setelah run** | ✅ ya | **Phase 3B** — membaca hasil Allure dan memberi verdict tiap kegagalan |

Keduanya berjalan **di dalam suite**, bukan sebagai alat bantu penulisan —
sesuai penekanan brief bahwa itulah yang membedakan V4 dari latihan automation
biasa.

---

## 3. Prompt persis yang dikirim

Disalin apa adanya dari `ai/data_generator.py`.

### Generate company data

```
Generate ONE fictional Indonesian company for software testing.

Return ONLY a JSON object. No markdown fences, no explanation, no extra text.

Required keys and constraints:
  name            PT or CV company name, max 100 chars
  email           lowercase, derived from the company name, domain .co.id
  phone           DIGITS ONLY, no spaces or dashes, no country code, no leading zero.
                  Must start with 8 and be 11 digits total, e.g. 81982913977
  industry_type   one of: Retail, Manufacturing, Services, Technology
  company_type    one of: PT, CV, UD
  language        "Indonesia"
  street_address  Indonesian street address with a house number
  country         "Indonesia"
  province        a real Indonesian province
  city            a real city INSIDE that province
  district        a real district INSIDE that city
  zone            a real zone/kelurahan INSIDE that district
  postal_code     EXACTLY 5 digits, and it must be the real postal code for that zone

The geographic chain must be internally consistent: city belongs to province,
district belongs to city, zone belongs to district, postal_code belongs to zone.
An inconsistent chain is rejected by the form under test.
```

### Generate customer data

```
Generate ONE fictional Indonesian retail customer for software testing.

Return ONLY a JSON object. No markdown fences, no explanation, no extra text.

Required keys and constraints:
  name      shop or business name, Indonesian style, max 100 chars
  contact   DIGITS ONLY, Indonesian mobile number starting with 08, 10-13 digits
  address   Indonesian street address including the city
```

### Triage kegagalan

Modul 3B **tidak memanggil model**. Ia menelusuri bukti secara deterministik
mengikuti urutan yang ditetapkan brief:

```python
EVIDENCE_ORDER = [
    "exception_or_assertion",   # exception hampir selalu skrip/environment
    "locator_resolution",       # locator menunjuk elemen yang dimaksud dan unik?
    "preceding_steps",          # semua langkah sebelum assert berhasil?
    "expected_value_correct",   # expected value-nya sendiri benar?
    "reproducibility",          # konsisten atau intermiten?
]
```

**Ini keputusan sadar, bukan kelalaian.** Alasannya di bagian 5.

---

## 4. Saat AI tidak tersedia atau mengembalikan output tidak valid

### Tanpa API key

`AI_API_KEY` kosong → langsung jalur fallback Faker, tanpa mencoba memanggil
model. Suite tetap berjalan offline dan di CI.

Fallback **bukan versi seadanya**. Ia memakai tabel kombinasi wilayah yang
sudah diverifikasi manual di aplikasi, karena Faker murni bisa menghasilkan
pasangan mustahil seperti `DKI Jakarta` + `Bandung` — dan cascade menolaknya
dengan timeout tanpa pesan.

### Output tidak valid

```
panggil model → validasi schema → valid?   pakai
                                 → invalid? retry SEKALI
                                            → masih invalid? fallback Faker
```

`MAX_RETRY = 1` disengaja: retry sekali menangkap kasus JSON acak yang
malformed. Bila prompt-nya sendiri yang salah, sepuluh retry pun tidak
menolong — dan fallback sudah tersedia.

### Kenapa validasi schema ada di tengah, bukan di akhir

Model bisa mengembalikan `"postal_code": "12920 (Kuningan)"` — lolos sebagai
string, tapi merusak form. Tanpa validasi, test gagal dengan pesan
`element not found`, dan **modul triage akan salah memvonisnya sebagai cacat
locator**.

Schema menangkapnya lebih dulu, dengan pesan yang menyebut penyebab sebenarnya.

### Contoh nyata dari pengerjaan ini

Validator `phone` lahir dari kegagalan sungguhan. Form eSuite menampilkan `+62`
sebagai prefix terpisah, sehingga hanya menerima nomor lokal diawali `8`.
Model dan Faker sama-sama menghasilkan format `021...`, dan aplikasi
menolaknya **secara senyap** — tombol Next terkunci tanpa pesan error apa pun.

Kegagalannya muncul sebagai timeout 30 detik yang terbaca seperti aplikasi
rusak. Setelah validator ditambahkan, kegagalan yang sama langsung menyebut:

```
phone harus diawali 8 (tanpa 0 maupun +62), dapat: '02150998877'.
Form eSuite menampilkan +62 sebagai prefix terpisah.
```

### Jalur mana yang dipakai selalu tercatat

Tiap generate melampirkan ke Allure: data yang dipakai, sumbernya (`ai` atau
`fallback`), dan bila fallback — alasannya. Reviewer bisa melihat mekanismenya
bekerja tanpa membaca kode.

---

## 5. Yang sengaja TIDAK diserahkan ke AI, dan kenapa

### Menulis atau mengubah asersi

AI cenderung melemahkan asersi agar suite hijau — mengganti `==` jadi `in`,
menambah `try/except`, menaikkan toleransi. Asersi adalah inti nilai suite ini,
dan brief menyebut pelemahannya sebagai kegagalan non-negotiable.

Seluruh asersi ditulis manual. Contoh konkret: `test_verify_detail.py` memakai
`actual == expected` per field, **bukan** `expected in actual` — karena `in`
akan meloloskan nilai yang masih membawa spasi berlebih, yaitu bug yang justru
diuji `TC-WEB-008`.

### Menentukan expected value

Expected value berasal dari dokumen test case dan dari data yang benar-benar
dikirim ke form — bukan dari hasil aktual. Menyesuaikannya agar cocok adalah
kegagalan non-negotiable.

Karena nilai dropdown ditentukan aplikasi (opsi pertama), suite **membaca balik**
nilai yang terpilih dan memakainya sebagai expected. Itu bukan menyesuaikan
diri dengan hasil, melainkan mencatat masukan yang sebenarnya.

### Memberi verdict triage lewat model

Modul 3B sengaja deterministik. Tiga alasan:

1. **Dapat diaudit.** Verdict dari aturan yang tertulis bisa diperiksa ulang
   orang lain. Verdict dari model tidak bisa direproduksi persis.
2. **Tidak boleh menebak.** Langkah keempat (`expected_value_correct`) tidak
   dapat diverifikasi otomatis, karena expected value ada di dokumen test case,
   bukan di kode. Laporan menyatakannya terang-terangan:
   *"TIDAK BISA DIVERIFIKASI OTOMATIS — cocokkan dengan dokumen test case"*.
   Model kemungkinan besar akan menebak dan terdengar meyakinkan.
3. **Biaya token.** Meminta model membaca seluruh stack trace tiap kegagalan
   jauh lebih mahal daripada pencocokan pola, tanpa manfaat yang jelas.

### Membuat atau menutup bug report

Verdict adalah **usulan untuk manusia**. Skrip tidak membuat tiket dan tidak
menutup apa pun. Bahasanya pun sengaja tidak memvonis — `"kandidat product bug"`
dengan tingkat keyakinan `"perlu konfirmasi manusia"`, bukan `"product bug"`.

### Menulis locator

Seluruh locator ditulis setelah inspeksi DOM langsung. Aplikasi ini tidak punya
`data-testid` dan tidak punya accessible name pada combobox — dua fakta yang
hanya bisa diketahui dengan memeriksa, bukan menebak. Locator hasil tebakan akan
gagal dengan timeout yang menyesatkan.

---

## Catatan biaya token

| Langkah | Alasan |
|---|---|
| `max_tokens=512` | Satu objek JSON kecil; batas ini mencegah model menjelaskan |
| Prompt meminta JSON murni | Tanpa preamble, tanpa markdown fence |
| Hanya field yang dibutuhkan | Tidak ada field cadangan "kalau-kalau perlu" |
| `MAX_RETRY = 1` | Retry kedua jarang menolong; fallback sudah tersedia |
| Triage tanpa model | Pencocokan pola cukup, dan hasilnya dapat diaudit |
| Fallback tanpa panggilan | Tanpa API key, nol token terpakai |