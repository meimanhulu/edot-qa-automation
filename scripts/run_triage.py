#!/usr/bin/env python3
"""
Entry point triage. Jalankan SETELAH suite:

    pytest
    python scripts/run_triage.py

Exit code SELALU 0 meski ada kegagalan yang di-triage. Skrip ini melaporkan,
bukan menggagalkan — menggagalkan build adalah tugas pytest.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.triage import classify, load_results, render_report  # noqa: E402

ALLURE_DIR = "allure-results"


def main() -> int:
    try:
        failures = load_results(ALLURE_DIR)
    except FileNotFoundError as e:
        print(f"[TRIAGE] {e}")
        return 0

    all_results = []
    for f in Path(ALLURE_DIR).glob("*-result.json"):
        try:
            all_results.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue

    from ai.triage import _run_counts
    counts = _run_counts(all_results)

    items = [classify(r, counts) for r in failures]
    out = render_report(items)

    print(f"[TRIAGE] {len(items)} kegagalan di-triage -> {out}")
    for it in items:
        print(f"  - {it['verdict']:28s} {it['test']}")
    print("[TRIAGE] Verdict adalah usulan. Tinjau sebelum membuat bug report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
