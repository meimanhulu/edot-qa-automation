# eDOT QA Automation — Take-Home Test V4

Suite automation testing untuk **eSuite (web)** dan **eWork SFA (mobile)**,
dengan AI di dalam suite.

> **Baca [docs/CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md) sebelum submit.**
> Dokumen itu menjelaskan setiap keputusan desain, dan diakhiri 10 pertanyaan
> latihan. Brief menyatakan ketidakmampuan menjelaskan kode akan diperlakukan
> sebagai bukan karya sendiri.
>
> **Yang masih perlu diisi:** nilai selector di blok `SEL` tiap page class
> (harus dari inspeksi DOM asli), serta Step 2 dan 3 wizard.

---

## Mulai dari mana

```bash
# 1. spec-kit — baca dulu, ini yang mengarahkan seluruh pengerjaan
cat docs/SPECKIT_PROMPTS.md

# 2. init spec-kit di repo ini
specify init --here --ai copilot

# 3. jalankan berurutan, review tiap hasil sebelum lanjut
/speckit-constitution   →   /speckit-specify   →   /speckit-plan
     →   /speckit-tasks   →   /speckit-implement
```

Isi tiap prompt sudah disiapkan di `docs/SPECKIT_PROMPTS.md`, sudah
disesuaikan dengan brief eDOT.

---

## Setup

### Web (Playwright)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
playwright install chromium

cp .env.example .env            # lalu isi nilainya
```

### Mobile (Maestro)

Windows perlu WSL. Panduan lengkap: **[docs/MAESTRO_SETUP_WINDOWS.md](docs/MAESTRO_SETUP_WINDOWS.md)**

```bash
maestro --version               # verifikasi terpasang
adb devices                     # verifikasi emulator terlihat
```

---

## Menjalankan

```bash
pytest -m web                   # suite web saja
pytest -m mobile                # suite mobile saja
pytest                          # keduanya, satu run Allure

python scripts/run_triage.py    # triage kegagalan (setelah suite)

allure serve allure-results     # buka laporan
```

---

## Struktur

```
web/pages/      Page Object — SATU-SATUNYA tempat locator
web/tests/      test Playwright, tanpa selector mentah
mobile/flows/   YAML Maestro, login sebagai shared sub-flow
mobile/runner.py  wrapper Pytest yang memanggil Maestro
ai/             3A generator data · 3B triage kegagalan
scripts/        entry point triage
docs/           spec-kit prompts, panduan Maestro, dokumen test case
```

---

## Aturan yang tidak boleh dilanggar

| Aturan | Kenapa |
|---|---|
| Asersi tidak boleh dilemahkan agar hijau | Non-negotiable pada brief |
| Tidak ada kredensial/API key di repo | Non-negotiable |
| Data test dihapus setelah run | Non-negotiable — shared environment |
| Setiap baris harus bisa dijelaskan | Non-negotiable |
| Tidak ada `time.sleep()` | Pakai auto-waiting Playwright / wait command Maestro |
| Locator hanya di page class / YAML | Tidak ada selector mentah di berkas test |
| Login sekali per sesi via `storage_state` | Bukan login di tiap test |
| Assertion Tier 2 diberi komentar penanda | Agar reviewer bisa membedakan bug produk dari cacat skrip |

---

## Yang harus diisi sebelum submit

- [ ] Link repo ini ke dalam dokumen test case (Excel/Google Sheet)
- [ ] `AI_USAGE.md` — lima poin yang diminta brief
- [ ] Laporan Allure dari satu run web penuh
- [ ] Laporan triage dari run yang **sengaja digagalkan**
- [ ] Catatan jujur soal skenario yang tidak selesai
- [ ] Bila memakai kredensial mobile fallback, catat di sini

Yang harus diisi sebelum submit
 Link repo ini ke dalam dokumen test case (Excel/Google Sheet)
 AI_USAGE.md — lima poin yang diminta brief
 Laporan Allure dari satu run web penuh
 Laporan triage dari run yang sengaja digagalkan
 Catatan jujur soal skenario yang tidak selesai
 Bila memakai kredensial mobile fallback, catat di sini
Temuan saat inspeksi manual (berbeda dari brief)

Dicatat karena memengaruhi implementasi, dan karena reviewer perlu tahu keputusan selector diambil atas dasar apa.

Temuan	Dampak
Nol data-testid di seluruh aplikasi (diverifikasi via document.querySelectorAll('[data-testid]').length === 0)	Prioritas pertama brief tidak tersedia. Dipakai name (atribut stabil) untuk input dan role + accessible name untuk tombol.
Tombol layar 2 dan 3 sama-sama "Log In", bukan "Continue" lalu "Sign In" seperti tertulis di brief	Satu locator dipakai untuk kedua layar; transisi antar layar ditandai dengan menunggu input yang relevan terlihat.
Login lewat OIDC di cronus.edot.id/oidc/interaction/<id>	Path mengandung interaction id yang berubah tiap sesi, jadi penantian berbasis URL tidak dipakai — yang ditunggu adalah elemennya.
Input tersembunyi bernama sama — input[name=password] sudah ada sebagai type=hidden di layar 2, begitu pula username di layar 3	Locator memakai filter :visible. Tanpa itu, locator cocok ke elemen tersembunyi dan fill() gagal dengan pesan menyesatkan.
id bernilai radix-:rd: (Radix UI, di-generate ulang tiap render)	Tidak dipakai sebagai selector. Sisi baiknya, Radix memberi role ARIA yang benar sehingga get_by_role andal.
Setelah login, landing page menampilkan daftar company beserta greeting "Welcome Back,"	TC-WEB-001 tetap valid: greeting ada di halaman ini.
Akun uji memiliki 571 company; company QA Production (ID 5049209) berstatus Active sampai 27/04/2027	ID tersebut sama dengan fallback mobile pada brief. Pencarian company wajib lewat search, bukan memindai halaman pertama.
