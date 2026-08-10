"""
Skrip pembersih data test yang tertinggal.

Jalankan bila run gagal di tengah dan meninggalkan company di shared
environment:

    python tools/cleanup_orphans.py "PT Nusantara"

Argumen adalah AWALAN nama. Skrip menampilkan daftar company yang cocok,
meminta konfirmasi, lalu menghapusnya satu per satu.

Dibuat karena brief menyebut "test data left behind on the shared
environment" sebagai kegagalan non-negotiable — dan run yang gagal di tengah
tidak sempat menjalankan teardown fixture.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from web.pages.companies_page import CompaniesPage
from web.pages.company_detail_page import CompanyDetailPage
from web.pages.login_page import LoginPage


def main() -> int:
    if len(sys.argv) < 2:
        print('Pakai: python tools/cleanup_orphans.py "<awalan nama>"')
        return 1

    prefix = sys.argv[1]
    load_dotenv()

    base_url = os.environ["ESUITE_BASE_URL"]
    email = os.environ["ESUITE_EMAIL"]
    password = os.environ["ESUITE_PASSWORD"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(30000)

        LoginPage(page).open(base_url)
        LoginPage(page).login(email, password)

        companies = CompaniesPage(page)
        companies.open(base_url)

        names = [
            t.strip()
            for t in page.locator("text=/^(PT|CV)\\s/").all_inner_texts()
            if t.strip().startswith(prefix)
        ]
        unique = sorted(set(names))

        if not unique:
            print(f"Tidak ada company berawalan {prefix!r}")
            browser.close()
            return 0

        print(f"\nDitemukan {len(unique)} company berawalan {prefix!r}:")
        for n in unique:
            print(f"  - {n}")

        if input("\nHapus semuanya? (ketik HAPUS untuk lanjut): ") != "HAPUS":
            print("Dibatalkan.")
            browser.close()
            return 0

        for name in unique:
            try:
                companies.open(base_url)
                companies.open_manage(name)
                CompanyDetailPage(page).delete()
                print(f"  terhapus: {name}")
            except Exception as e:
                print(f"  GAGAL: {name} — {type(e).__name__}: {e}")

        companies.open(base_url)
        print("\nSelesai. Periksa jumlah company di header untuk memastikan.")
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())