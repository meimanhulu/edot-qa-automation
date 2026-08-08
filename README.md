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
