"""
Phase 3B — triage kegagalan.

Berjalan SETELAH suite. Membaca allure-results, memberi verdict tiap kegagalan.

GUARDRAIL (dinilai brief):
  - tidak mengubah test apa pun
  - tidak membuat bug report otomatis
  - tidak menutup apa pun otomatis
  - verdict adalah USULAN untuk manusia

Modul ini read-only terhadap repo. Satu-satunya yang ditulis adalah laporan.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

# Urutan penelusuran bukti — diambil PERSIS dari brief. Berhenti di kecocokan
# pertama. Jangan diubah urutannya: itu bagian dari yang dinilai.
EVIDENCE_ORDER = [
    "exception_or_assertion",
    "locator_resolution",
    "preceding_steps",
    "expected_value_correct",
    "reproducibility",
]

# Pola exception yang hampir selalu menandakan cacat skrip/environment,
# bukan bug produk.
SCRIPT_ERROR_PATTERNS = [
    (r"TimeoutError|Timeout \d+ms exceeded", "timeout menunggu elemen"),
    (r"strict mode violation", "locator cocok ke lebih dari satu elemen"),
    (r"waiting for locator|locator resolved to 0 elements", "elemen tidak ditemukan"),
    (r"NotImplementedError", "kode belum diimplementasikan"),
    (r"ConnectionError|ECONNREFUSED|net::ERR", "masalah jaringan/environment"),
    (r"ModuleNotFoundError|ImportError", "dependency belum terpasang"),
]


def load_results(allure_dir: str = "allure-results") -> list[dict]:
    """Baca semua *-result.json, kembalikan yang failed atau broken."""
    path = Path(allure_dir)
    if not path.exists():
        raise FileNotFoundError(f"{allure_dir} tidak ada — jalankan pytest lebih dulu")

    results = []
    for f in path.glob("*-result.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("status") in ("failed", "broken"):
            results.append(data)
    return results


def _run_counts(all_results: list[dict]) -> dict[str, dict[str, int]]:
    """
    Hitung berapa kali tiap test lulus dan gagal.

    Dipakai langkah bukti kelima: hasil yang berbeda antar run = flaky,
    bukan bug.
    """
    counts = defaultdict(lambda: {"passed": 0, "failed": 0})
    for r in all_results:
        name = r.get("fullName") or r.get("name", "unknown")
        if r.get("status") == "passed":
            counts[name]["passed"] += 1
        elif r.get("status") in ("failed", "broken"):
            counts[name]["failed"] += 1
    return counts


def classify(result: dict, run_counts: dict) -> dict:
    """
    Telusuri EVIDENCE_ORDER berurutan, berhenti di kecocokan pertama.

    Kembalikan verdict + bukti untuk TIAP langkah yang dilalui, bukan hanya
    kesimpulannya — supaya penalarannya bisa diperiksa orang lain.
    """
    name = result.get("fullName") or result.get("name", "unknown")
    message = (result.get("statusDetails") or {}).get("message", "") or ""
    trace = (result.get("statusDetails") or {}).get("trace", "") or ""
    haystack = f"{message}\n{trace}"

    evidence = []

    # ---- Langkah 1: exception atau assertion? ----
    for pattern, human in SCRIPT_ERROR_PATTERNS:
        if re.search(pattern, haystack):
            evidence.append(("exception_or_assertion", f"exception terdeteksi — {human}"))
            return {
                "test": name,
                "verdict": "script/environment defect",
                "stopped_at": "exception_or_assertion",
                "evidence": evidence,
                "message": message.strip()[:500],
                "confidence": "tinggi",
            }
    is_assertion = "AssertionError" in haystack or result.get("status") == "failed"
    evidence.append((
        "exception_or_assertion",
        "assertion gagal, bukan exception" if is_assertion else "status broken tanpa pola exception dikenal",
    ))

    # ---- Langkah 2: locator resolve ke elemen yang dimaksud dan unik? ----
    if re.search(r"resolved to \d+ elements", haystack):
        evidence.append(("locator_resolution", "locator cocok ke jumlah elemen tak terduga"))
        return {
            "test": name,
            "verdict": "script/environment defect",
            "stopped_at": "locator_resolution",
            "evidence": evidence,
            "message": message.strip()[:500],
            "confidence": "tinggi",
        }
    evidence.append(("locator_resolution", "tidak ada indikasi masalah locator pada pesan error"))

    # ---- Langkah 3: semua langkah sebelum assertion berhasil? ----
    steps = result.get("steps", [])
    failed_before = [s for s in steps[:-1] if s.get("status") in ("failed", "broken")]
    if failed_before:
        names = ", ".join(s.get("name", "?") for s in failed_before[:3])
        evidence.append(("preceding_steps", f"ada langkah sebelum assertion yang gagal: {names}"))
        return {
            "test": name,
            "verdict": "script/environment defect",
            "stopped_at": "preceding_steps",
            "evidence": evidence,
            "message": message.strip()[:500],
            "confidence": "sedang",
        }
    evidence.append(("preceding_steps", f"seluruh {max(len(steps) - 1, 0)} langkah sebelum assertion berhasil"))

    # ---- Langkah 4: expected value-nya sendiri benar? ----
    # Tidak bisa diputuskan otomatis — expected value berasal dari dokumen
    # test case, bukan dari kode. Ini justru titik di mana manusia wajib
    # memeriksa, dan laporan harus mengatakannya terang-terangan.
    evidence.append((
        "expected_value_correct",
        "TIDAK BISA DIVERIFIKASI OTOMATIS — cocokkan expected value dengan dokumen test case",
    ))

    # ---- Langkah 5: konsisten atau intermiten? ----
    c = run_counts.get(name, {"passed": 0, "failed": 0})
    if c["passed"] > 0 and c["failed"] > 0:
        evidence.append(("reproducibility", f"hasil bercampur: {c['passed']} lulus / {c['failed']} gagal"))
        return {
            "test": name,
            "verdict": "flaky",
            "stopped_at": "reproducibility",
            "evidence": evidence,
            "message": message.strip()[:500],
            "confidence": "sedang",
        }

    evidence.append(("reproducibility", f"konsisten gagal ({c['failed']}x), tidak ada run yang lulus"))
    return {
        "test": name,
        "verdict": "kandidat product bug",
        "stopped_at": "reproducibility",
        "evidence": evidence,
        "message": message.strip()[:500],
        "confidence": "perlu konfirmasi manusia",
    }


def render_report(items: list[dict], output: str = "triage-report.md") -> str:
    """
    Tulis laporan Markdown.

    Bahasanya sengaja USULAN, bukan vonis. Verdict adalah proposal untuk
    manusia — brief melarang keras skrip ini memutuskan sendiri.
    """
    lines = [
        "# Laporan Triage Kegagalan",
        "",
        "> Verdict di bawah adalah **usulan untuk ditinjau manusia**.",
        "> Skrip ini tidak membuat bug report dan tidak menutup apa pun.",
        "",
        f"Total kegagalan yang di-triage: **{len(items)}**",
        "",
    ]

    if not items:
        lines.append("Tidak ada kegagalan pada run ini.")
        Path(output).write_text("\n".join(lines), encoding="utf-8")
        return output

    summary = defaultdict(int)
    for it in items:
        summary[it["verdict"]] += 1

    lines += ["## Ringkasan", "", "| Verdict | Jumlah |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(summary.items())]
    lines += ["", "---", ""]

    for i, it in enumerate(items, 1):
        lines += [
            f"## {i}. {it['test']}",
            "",
            f"**Verdict:** {it['verdict']}  ",
            f"**Berhenti di langkah:** `{it['stopped_at']}`  ",
            f"**Tingkat keyakinan:** {it['confidence']}",
            "",
            "### Penelusuran bukti",
            "",
            "| # | Langkah | Temuan |",
            "|---|---|---|",
        ]
        for n, (step, finding) in enumerate(it["evidence"], 1):
            lines.append(f"| {n} | `{step}` | {finding} |")

        lines += ["", "### Pesan error", "", "```", it["message"] or "(kosong)", "```", "", "---", ""]

    Path(output).write_text("\n".join(lines), encoding="utf-8")
    return output
