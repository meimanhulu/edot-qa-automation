# Laporan Triage Kegagalan

> Verdict di bawah adalah **usulan untuk ditinjau manusia**.
> Skrip ini tidak membuat bug report dan tidak menutup apa pun.

Total kegagalan yang di-triage: **2**

## Ringkasan

| Verdict | Jumlah |
|---|---|
| kandidat product bug | 2 |

---

## 1. web.tests.test_verify_detail#test_detail_page_loads_without_reload

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
 +  where True = <web.pages.company_detail_page.CompanyDetailPage object at 0x000001BC2E6FE690>.needed_reload
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
AssertionError: Nama tidak ter-trim saat disimpan: '   PT Nusantara Jaya 1062   ' (diharapkan 'PT Nusantara Jaya 1062')
assert '   PT Nusantara Jaya 1062   ' == 'PT Nusantara Jaya 1062'
  
  [0m[91m- PT Nusantara Jaya 1062[39;49;00m[90m[39;49;00m
  [92m+    PT Nusantara Jaya 1062   [39;49;00m[90m[39;49;00m
  ? +++                      +++[90m[39;49;00m
```

---
