# AI_USAGE.md

> Kerangka. Isi tiap bagian — brief mensyaratkan kelimanya secara eksplisit
> dan bagian ini ikut dinilai.

---

## 1. Model yang dipakai dan alasannya

**Model:** `TODO`

**Alasan:** TODO — sebutkan pertimbangan nyata: kualitas output JSON,
biaya token, latensi, atau ketersediaan API key.

---

## 2. Di mana AI berjalan

| Fase | AI dipakai? | Untuk apa |
|---|---|---|
| Saat menulis test | TODO | |
| Saat run berlangsung | TODO | Phase 3A — generate data test |
| Setelah run | TODO | Phase 3B — triage kegagalan |

---

## 3. Prompt persis yang dikirim

Salin **apa adanya** dari `ai/data_generator.py`. Jangan diringkas —
brief meminta prompt persisnya.

### Generate company data
```
TODO: tempel prompt persis di sini
```

### Generate customer data
```
TODO
```

### Triage kegagalan
```
TODO
```

---

## 4. Saat AI tidak tersedia atau mengembalikan output tidak valid

**Tidak ada API key:** TODO — jelaskan jalur fallback Faker, dan tegaskan
suite tetap jalan offline dan di CI.

**Output malformed:** TODO — jelaskan urutannya: validasi schema gagal →
retry sekali → masih gagal → jatuh ke fallback. Sebutkan bahwa jalur mana
yang dipakai tercatat di lampiran Allure.

**Contoh nyata:** TODO — kalau selama pengerjaan pernah ada output ditolak
schema, ceritakan. Itu bukti mekanismenya benar-benar bekerja.

---

## 5. Yang sengaja TIDAK diserahkan ke AI, dan kenapa

TODO. Minimal cakup:

- **Menulis atau mengubah asersi** — alasan: AI cenderung melemahkan
  asersi agar hijau. Asersi adalah inti nilai suite ini.
- **Memutuskan expected value** — alasan: expected value berasal dari test
  case, bukan dari hasil aktual. Menyesuaikannya agar cocok adalah
  non-negotiable failure.
- **Membuat atau menutup bug report** — alasan: verdict triage adalah
  usulan untuk manusia, bukan keputusan.
- TODO: tambahkan yang lain bila ada.

---

## Catatan biaya token

TODO — brief meminta "be deliberate about token cost". Jelaskan langkah
yang diambil: minta JSON tanpa penjelasan, hanya field yang dibutuhkan,
retry maksimal sekali, atau caching bila ada.
