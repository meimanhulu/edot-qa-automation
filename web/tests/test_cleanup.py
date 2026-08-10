"""
TC-WEB-015 — delete company, verifikasi benar-benar hilang.

Brief: "Clean up - delete the company at the end of the run. This is a shared
environment; leftover data counts against you." Meninggalkan data termasuk
non-negotiable failure.
"""
import allure
import pytest

from web.pages.companies_page import CompaniesPage
from web.pages.company_detail_page import CompanyDetailPage
from web.pages.register_company_wizard import RegisterCompanyWizard


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-015 Delete company and confirm it is gone")
def test_delete_company(page, env, company_data):
    """
    Sengaja TIDAK memakai fixture created_company: fixture itu menghapus
    company di teardown, sedangkan penghapusan itulah yang sedang diuji.
    Memakai fixture berarti menguji cleanup fixture, bukan fitur delete.
    """
    data = company_data.model_dump()

    wizard = RegisterCompanyWizard(page)
    wizard.open(env["base_url"])
    wizard.fill_step_one(data)
    wizard.click_next(expect_locator=wizard.step_two_marker)
    wizard.complete_step_two()
    wizard.complete_step_three(data)

    # Setelah Register, aplikasi mengarahkan ke DAFTAR companies.
    companies = CompaniesPage(page)
    companies.open(env["base_url"])

    # Polling: 572 kartu dirender sekaligus, jadi kartu baru butuh waktu
    # muncul. Menghitung seketika bisa mendapat 0 padahal record-nya ada.
    companies.expect_company_count(company_data.name, 1)

    companies.open_manage(company_data.name)
    detail = CompanyDetailPage(page)
    detail.wait_loaded()
    mongo_id = detail.mongo_id_from_url()
    detail_url = page.url

    # ---- aksi yang diuji ----
    CompanyDetailPage(page).delete()

    # Tier 2: record hilang dari daftar.
    companies.open(env["base_url"])
    companies.expect_company_count(company_data.name, 0)

    # Tier 2: dan tidak dapat diakses lewat URL langsung.
    # Ini yang membedakan 'benar-benar terhapus' dari 'sekadar disembunyikan
    # dari daftar'. Record yang masih bisa dibuka lewat URL berarti hanya
    # di-filter dari tampilan, bukan dihapus.
    response = page.goto(detail_url)
    still_loads = CompanyDetailPage(page).is_loaded()

    allure.attach(
        f"URL: {detail_url}\n"
        f"mongo_id: {mongo_id}\n"
        f"status: {response.status if response else 'n/a'}\n"
        f"URL akhir: {page.url}\n"
        f"halaman detail masih termuat: {still_loads}",
        name="akses URL detail setelah delete",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert not still_loads, (
        "Halaman detail masih dapat dibuka setelah company dihapus — "
        "record kemungkinan hanya disembunyikan dari daftar, bukan terhapus"
    )