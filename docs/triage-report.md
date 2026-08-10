# Laporan Triage Kegagalan

> Verdict di bawah adalah **usulan untuk ditinjau manusia**.
> Skrip ini tidak membuat bug report dan tidak menutup apa pun.

Total kegagalan yang di-triage: **4**

## Ringkasan

| Verdict | Jumlah |
|---|---|
| kandidat product bug | 3 |
| script/environment defect | 1 |

---

## 1. web.tests.test_cleanup#test_delete_company

**Verdict:** kandidat product bug  
**Berhenti di langkah:** `reproducibility`  
**Tingkat keyakinan:** perlu konfirmasi manusia

### Penelusuran bukti

| # | Langkah | Temuan |
|---|---|---|
| 1 | `exception_or_assertion` | assertion gagal, bukan exception |
| 2 | `locator_resolution` | tidak ada indikasi masalah locator pada pesan error |
| 3 | `preceding_steps` | seluruh 0 langkah sebelum assertion berhasil |
| 4 | `expected_value_correct` | TIDAK BISA DIVERIFIKASI OTOMATIS — cocokkan expected value dengan dokumen test case |
| 5 | `reproducibility` | konsisten gagal (1x), tidak ada run yang lulus |

### Pesan error

```
AssertionError: Locator expected to have count '0'
Actual value: 1 
Call log:
  - Expect "to_have_count" with timeout 30000ms
  - waiting for get_by_text("CV Mandiri Rejeki", exact=True)
    54 × locator resolved to 1 element
       - unexpected value "1"
```

---

## 2. web.tests.test_create_company#test_company_name_stored_trimmed

**Verdict:** kandidat product bug  
**Berhenti di langkah:** `reproducibility`  
**Tingkat keyakinan:** perlu konfirmasi manusia

### Penelusuran bukti

| # | Langkah | Temuan |
|---|---|---|
| 1 | `exception_or_assertion` | assertion gagal, bukan exception |
| 2 | `locator_resolution` | tidak ada indikasi masalah locator pada pesan error |
| 3 | `preceding_steps` | seluruh 0 langkah sebelum assertion berhasil |
| 4 | `expected_value_correct` | TIDAK BISA DIVERIFIKASI OTOMATIS — cocokkan expected value dengan dokumen test case |
| 5 | `reproducibility` | konsisten gagal (1x), tidak ada run yang lulus |

### Pesan error

```
AssertionError: Locator expected to be visible
Actual value: None
Error: element(s) not found 
Call log:
  - Expect "to_be_visible" with timeout 30000ms
  - waiting for get_by_text("Company Details", exact=True)

Aria snapshot:
- banner:
  - navigation:
    - img
    - link "Home":
      - /url: /
    - link "Companies":
      - /url: /companies
    - link "Settings":
      - /url: /setting/administrator
  - button "I itqaedot 484 Companies":
    - text: I itqaedot
    - img
    - text: 484 Comp
```

---

## 3. web.tests.test_verify_detail#test_detail_page_loads_without_reload

**Verdict:** kandidat product bug  
**Berhenti di langkah:** `reproducibility`  
**Tingkat keyakinan:** perlu konfirmasi manusia

### Penelusuran bukti

| # | Langkah | Temuan |
|---|---|---|
| 1 | `exception_or_assertion` | assertion gagal, bukan exception |
| 2 | `locator_resolution` | tidak ada indikasi masalah locator pada pesan error |
| 3 | `preceding_steps` | seluruh 0 langkah sebelum assertion berhasil |
| 4 | `expected_value_correct` | TIDAK BISA DIVERIFIKASI OTOMATIS — cocokkan expected value dengan dokumen test case |
| 5 | `reproducibility` | konsisten gagal (1x), tidak ada run yang lulus |

### Pesan error

```
AssertionError: Halaman detail tidak memuat data pada pembukaan pertama; data baru muncul setelah reload. Pengguna yang membuka company yang baru dibuat akan melihat form kosong tanpa petunjuk apa pun bahwa ia perlu memuat ulang halaman.
assert not True
 +  where True = <web.pages.company_detail_page.CompanyDetailPage object at 0x000001E90443EE10>.needed_reload
```

---

## 4. web.tests.test_verify_detail#test_company_id_present_and_readonly

**Verdict:** script/environment defect  
**Berhenti di langkah:** `locator_resolution`  
**Tingkat keyakinan:** tinggi

### Penelusuran bukti

| # | Langkah | Temuan |
|---|---|---|
| 1 | `exception_or_assertion` | assertion gagal, bukan exception |
| 2 | `locator_resolution` | locator cocok ke jumlah elemen tak terduga |

### Pesan error

```
AssertionError: Locator expected to have count '1'
Actual value: 2 
Call log:
  - Expect "to_have_count" with timeout 30000ms
  - waiting for get_by_text("CV Berkah Sinar", exact=True)
    55 × locator resolved to 2 elements
       - unexpected value "2"
```

---
