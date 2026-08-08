# Code Walkthrough — Penjelasan Setiap Keputusan Desain

Dokumen ini menjelaskan **kenapa** kode ditulis seperti itu, bukan sekadar apa
yang dilakukannya. Dibuat supaya bisa dijelaskan ke tiga audiens berbeda:

| Audiens | Yang mereka tanyakan | Bagian yang dibaca |
|---|---|---|
| **QA junior** | "Ini fungsinya apa?" | Kolom *Apa* di tiap tabel |
| **QA senior / SDET** | "Kenapa begitu, bukan cara lain?" | Kolom *Kenapa* dan bagian Trade-off |
| **Lead / hiring manager** | "Apa risikonya, dan apa yang kamu putuskan?" | Bagian Keputusan Sadar dan Batasan |

---

## Cara memakai dokumen ini

Sebelum submit, lakukan ini untuk tiap file:

1. Tutup editornya
2. Jawab tiga pertanyaan tanpa melihat kode:
   - Apa yang dilakukan file ini?
   - Kenapa pendekatannya begitu, bukan cara lain?
   - Apa yang rusak kalau bagian ini dihapus?
3. Kalau ada yang tidak bisa dijawab, **buka kodenya dan tulis ulang bagian itu sendiri**

Brief menyatakan ketidakmampuan menjelaskan kode diperlakukan sebagai bukan
karya sendiri. Dokumen ini alat belajar, bukan pengganti pemahaman.

---

## 1. Arsitektur — kenapa dipisah seperti ini

```
conftest.py          fixture bersama, satu-satunya pembaca os.environ
web/pages/           Page Object — satu-satunya tempat locator
web/tests/           test, tanpa selector mentah
mobile/flows/        YAML Maestro, login sebagai shared sub-flow
mobile/runner.py     jembatan Python ↔ Maestro
ai/                  3A generator data · 3B triage kegagalan
```

| Keputusan | Kenapa |
|---|---|
| Locator hanya di page class | Saat DOM berubah, satu file yang disunting. Kalau selector tersebar di test, satu perubahan UI merusak sepuluh test dan semuanya harus disisir. |
| `os.environ` hanya di `conftest.py` | Env baru cukup ditambahkan di satu tempat. Juga membuat "env mana yang dipakai suite ini" bisa dijawab dengan membuka satu file. |
| Page object **mengembalikan** keadaan, tidak assert | Assert milik test. Dengan begitu satu page object bisa dipakai test positif maupun negatif, dan test bebas memilih cara membandingkan. |
| Mobile lewat wrapper Python | Supaya web dan mobile masuk ke **satu** run Allure. Kalau Maestro dijalankan terpisah, laporannya dua dan reviewer harus menggabungkan sendiri. |

---

## 2. Fixture — tiga syarat brief yang dipenuhi di sini

### `storage_state_path` — login sekali per sesi

```python
@pytest.fixture(scope="session")
def storage_state_path(browser, env, tmp_path_factory):
```

**Apa:** login satu kali, simpan cookie + localStorage ke file, semua test
memakai file itu.

**Kenapa:** brief melarang login di dalam tiap test. Alasan praktisnya: login
eSuite melewati tiga layar dan satu redirect Account Center — sekitar 5–8 detik.
Dengan 15 test, itu 2 menit terbuang hanya untuk login berulang.

**Cara membuktikan ini benar:** hitung request ke endpoint login dalam satu run
penuh. Harus tepat 1, berapa pun jumlah test-nya.

**Kalau dihapus:** tiap test login sendiri. Suite tetap hijau, tapi lambat, dan
melanggar syarat eksplisit brief.

### `page` vs `anon_page` — dua fixture, bukan satu

| Fixture | Punya sesi login? | Dipakai |
|---|---|---|
| `page` | ✅ ya | test yang butuh keadaan sudah login |
| `anon_page` | ❌ tidak | test Negative login |

**Kenapa dipisah:** test "login gagal dengan password salah" yang memakai
fixture `page` **tidak menguji apa pun** — browsernya sudah login. Ini jenis
test yang selalu hijau tanpa membuktikan apa pun, dan brief menyebutnya
sebagai non-negotiable failure.

### `created_company` — cleanup yang tidak bisa dilewati

```python
yield {"input": company_data, "name": company_data.name}
# ---- teardown: selalu jalan ----
```

**Kenapa cleanup di fixture, bukan di baris terakhir test:** kalau test gagal di
tengah, baris setelahnya tidak pernah dieksekusi — dan data tertinggal di
shared environment. Teardown fixture tetap jalan apa pun hasil test-nya.

**Kenapa teardown dibungkus `try/except`:** kalau penghapusan gagal, kita ingin
tahu, bukan menyembunyikannya. Karena itu kegagalannya dilampirkan ke Allure
sebagai peringatan — bukan ditelan diam-diam, dan juga tidak menggagalkan test
yang sebenarnya sudah selesai.

### `screenshot_on_failure` — kenapa `autouse=True`

**Kenapa:** brief mensyaratkan screenshot pada **setiap** kegagalan. Kalau
fixture harus diminta manual, satu test yang lupa memintanya = satu kegagalan
tanpa bukti visual.

**Kenapa ada `except: pass` di dalamnya:** kalau pengambilan screenshot sendiri
gagal (browser sudah tertutup, misalnya), kita tidak mau error itu menutupi
kegagalan aslinya. Ini satu-satunya tempat menelan exception dibenarkan, dan
alasannya ditulis di komentar.

---

## 3. Cascade dropdown — masalah paling teknis di suite ini

```
Country → Province → City → District → Zone → Postal Code
```

Tiap child baru terisi **setelah** parent dipilih, lewat XHR.

### Kenapa tidak bisa langsung pilih berurutan

```python
# SALAH — akan flaky
country.select_option("Indonesia")
province.select_option("DKI Jakarta")   # opsi belum termuat
```

Playwright akan mengklik dropdown yang opsinya belum ada. Kadang berhasil
(jaringan cepat), kadang gagal. Itu definisi flaky.

### Kenapa tidak pakai sleep

`sleep(2)` kadang terlalu cepat (tetap flaky) dan kadang terlalu lambat
(suite jadi lama). Dan brief melarangnya eksplisit.

### Solusinya

```python
def select_and_wait_child(self, parent, value, child, minimum=2):
    parent.select_option(label=value)
    self.wait_options_populated(child, minimum=minimum)
```

**Kenapa `minimum=2`, bukan 1:** dropdown biasanya sudah punya satu opsi
placeholder ("Pilih Provinsi") sejak awal. Menunggu ≥1 langsung lolos padahal
data belum termuat. Menunggu ≥2 berarti setidaknya satu opsi asli sudah masuk.

**Kenapa diekstrak jadi method:** pola "pilih lalu tunggu" harus terjadi di
**setiap** level. Melewatkannya di satu level saja sudah cukup membuat suite
flaky. Dengan diekstrak, tidak mungkin terlewat.

**Kenapa `change_province()` sengaja TIDAK menunggu child:** TC-WEB-006 justru
menguji apa yang terjadi pada child setelah parent berubah. Menunggu di situ
akan menyembunyikan perilaku yang sedang diuji.

---

## 4. Assertion Tier 2 — bagian dengan bobot nilai tertinggi

### Kenapa mengumpulkan mismatch, bukan assert berantai

```python
mismatches = []
for detail_key, input_key, label in FIELD_MAP:
    if actual[detail_key] != str(expected[input_key]):
        mismatches.append(...)
assert not mismatches, f"{len(mismatches)} field tidak cocok:\n" + "\n".join(mismatches)
```

**Assert berantai** berhenti di field pertama yang salah. Kalau tiga field
bermasalah: perbaiki satu, jalankan lagi, tahu yang kedua, dan seterusnya —
tiga siklus untuk informasi yang bisa didapat sekali.

**Mengumpulkan dulu** memberi gambaran utuh dalam satu run, dan pesannya tetap
menyebut field mana saja yang salah.

### Kenapa `==`, bukan `in`

```python
assert actual["name"] == expected["name"]      # ✅
assert expected["name"] in actual["name"]      # ❌
```

`in` akan **meloloskan** nilai yang masih membawa spasi berlebih
(`"PT Sinar  "` mengandung `"PT Sinar"`) — padahal itu persis bug yang diuji
TC-WEB-008. Asersi yang tidak bisa gagal sama tidak bergunanya dengan tidak
ada asersi.

### Kenapa `text_of()` tidak melakukan `.strip()`

Kalau page object ikut men-trim, bug trimming tersembunyi dan test selalu
hijau tanpa membuktikan apa pun. Page object melaporkan **apa adanya**;
test yang memutuskan.

### Komentar `# Tier 2:` itu wajib

Brief mensyaratkan penanda agar reviewer bisa membedakan **bug produk** dari
**cacat skrip** sekali lihat. Tanpa penanda, reviewer harus membaca seluruh
test untuk tahu apa yang sebenarnya diverifikasi.

---

## 5. Modul AI 3A — generator data

### Alur lengkapnya

```
ada API key? ── tidak ──> fallback Faker
    │ ya
    ▼
panggil model ──> validasi schema ──┬── valid ──> pakai
                                    └── invalid ──> retry SEKALI
                                                    └── gagal ──> fallback
```

### Kenapa schema validation ada di tengah, bukan di akhir

Model bisa mengembalikan `"postal_code": "12920 (Kuningan)"` — lolos sebagai
string, tapi merusak form. Kalau tidak divalidasi, test gagal dengan pesan
`element not found` dan **triage akan salah memvonisnya sebagai cacat locator**.

Schema menangkapnya lebih dulu, dengan pesan yang menyebut penyebab sebenarnya.

### Kenapa `MAX_RETRY = 1`

Brief meminta "be deliberate about token cost". Retry sekali sudah menangkap
kasus output acak yang malformed; kalau prompt-nya sendiri yang salah, retry
sepuluh kali pun tidak akan menolong — dan fallback sudah tersedia.

### Kenapa fallback pakai tabel REGIONS, bukan Faker murni

Faker bisa menghasilkan `"DKI Jakarta"` + `"Bandung"` — kombinasi yang ditolak
cascade. Test akan gagal **karena datanya**, bukan karena aplikasinya. Tabel
menjamin kombinasi selalu sah.

### Kenapa sumber data dilampirkan ke Allure

Reviewer harus bisa melihat mekanismenya bekerja — jalur mana yang dipakai,
dan kalau fallback, kenapa. Itu bukti schema validation dan fallback bukan
sekadar ada di kode.

---

## 6. Modul AI 3B — triage

### Kenapa urutan bukti tidak boleh diubah

```python
EVIDENCE_ORDER = [
    "exception_or_assertion",
    "locator_resolution",
    "preceding_steps",
    "expected_value_correct",
    "reproducibility",
]
```

Diambil persis dari brief, dan urutannya **berarti**: exception hampir selalu
cacat skrip, jadi diperiksa lebih dulu supaya kegagalan yang jelas-jelas bukan
bug tidak pernah salah divonis sebagai bug produk.

### Kenapa langkah 4 menyerah secara terbuka

```python
evidence.append((
    "expected_value_correct",
    "TIDAK BISA DIVERIFIKASI OTOMATIS — cocokkan dengan dokumen test case",
))
```

Expected value berasal dari dokumen test case, bukan dari kode. Skrip tidak
bisa tahu apakah nilainya benar.

**Menyatakan batas ini terang-terangan lebih jujur daripada menebak.** Laporan
yang mengaku tidak tahu bisa dipercaya; laporan yang menebak semuanya tidak.

### Kenapa bahasa laporannya "usulan", bukan vonis

Brief: *"The triage verdict is a proposal for a human. It must not auto-file
bugs and must not auto-close anything."*

Karena itu verdict-nya `"kandidat product bug"` dengan confidence
`"perlu konfirmasi manusia"`, bukan `"product bug"`.

### Kenapa exit code selalu 0

Skrip ini **melaporkan**, bukan menggagalkan. Menggagalkan build adalah tugas
pytest. Kalau triage ikut menggagalkan, satu kegagalan akan dihitung dua kali.

---

## 7. Keputusan sadar — untuk dijelaskan ke lead

Bagian ini yang paling sering ditanyakan di wawancara teknis.

| Keputusan | Alternatif yang ditolak | Alasan |
|---|---|---|
| `storage_state` untuk auth | Login tiap test | Syarat brief + hemat ~2 menit per run |
| Context baru tiap test | Satu context untuk semua | Isolasi: satu test tidak mewarisi state UI test sebelumnya |
| Kumpulkan mismatch | Assert berantai | Satu run memberi gambaran utuh, bukan satu field per run |
| Fallback pakai tabel wilayah | Faker murni | Menjamin cascade valid; kegagalan jadi soal aplikasi, bukan data |
| `parametrize` untuk validasi field | Satu test berisi tiga kondisi | Kegagalan kondisi pertama tidak menyembunyikan dua sisanya |
| Skip mobile bila Maestro absen | Gagalkan test | Skip dengan alasan jelas lebih informatif daripada merah yang menyesatkan |
| Triage exit 0 | Exit non-zero saat ada kegagalan | Menggagalkan build adalah tugas pytest, bukan pelapor |

---

## 8. Batasan yang diketahui — sampaikan sebelum ditanya

Menyebutkan batasan lebih dulu jauh lebih kuat daripada ketahuan saat ditanya.

| Batasan | Kenapa ada | Rencana |
|---|---|---|
| Selector masih perlu diverifikasi terhadap DOM asli | Dibuat sebelum akses ke aplikasi | Ganti nilai di blok `SEL` tiap page class |
| Step 2 dan 3 wizard belum lengkap | Brief hanya merinci Step 1 | Isi setelah inspeksi manual |
| Assertion Tier 2 mobile ada di YAML, bukan Python | Maestro yang memegang device | Sudah dicatat di test dan README |
| Triage langkah 4 tidak bisa otomatis | Expected value ada di dokumen, bukan kode | Disebut eksplisit di laporan |
| Region fallback baru 3 kombinasi | Cukup untuk suite ini | Tambah bila butuh variasi lebih |

---

## 9. Latihan sebelum submit

Jawab tanpa membuka kode. Kalau ada yang macet, tulis ulang bagian itu sendiri.

**Tingkat junior**
1. Kenapa locator tidak boleh ada di berkas test?
2. Apa beda `page` dan `anon_page`?
3. Kenapa cleanup ada di fixture, bukan di akhir test?

**Tingkat senior**
4. Kenapa `wait_options_populated` memakai `minimum=2`?
5. Kenapa `text_of()` tidak melakukan `.strip()`?
6. Kenapa `assert ==` bukan `assert in` pada verifikasi detail?
7. Kenapa `change_province()` sengaja tidak menunggu child terisi?

**Tingkat lead**
8. Apa yang terjadi kalau API key tidak ada saat CI berjalan?
9. Kenapa triage tidak boleh menggagalkan build?
10. Kalau harus memotong satu skenario karena waktu, mana yang dipotong dan kenapa?

> Jawaban nomor 10 yang paling menunjukkan level: yang dipotong adalah
> **Edit** (TC-WEB-014 / TC-MOB-010), karena Tier 2 sudah terwakili oleh
> Create, Verify Detail, dan Delete. Yang **tidak boleh** dipotong adalah
> Delete — data tertinggal di shared environment termasuk non-negotiable.
