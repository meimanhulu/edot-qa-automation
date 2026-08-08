"""TC-WEB-015 — delete company, verifikasi benar-benar hilang."""
import allure
import pytest

from web.pages.companies_page import CompaniesPage
from web.pages.register_company_wizard import RegisterCompanyWizard


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-015 Delete company and confirm it is gone")
def test_delete_company(page, company_data):
    """
    Sengaja TIDAK memakai fixture created_company: fixture itu menghapus
    company di teardown, sedangkan penghapusan itulah yang sedang diuji.
    """
    companies = CompaniesPage(page)
    companies.open()
    companies.click_add_company()

    wizard = RegisterCompanyWizard(page)
    data = company_data.model_dump()
    wizard.fill_basic_fields(data)
    wizard.select_cascade(
        data["country"], data["province"], data["city"],
        data["district"], data["zone"], data["postal_code"],
    )
    wizard.click_next()
    wizard.complete_step_two(data)
    wizard.complete_step_three(data)
    wizard.submit()

    companies.open()
    assert companies.count_rows_matching(company_data.name) == 1, "Prasyarat gagal: company tidak terbuat"

    # Ambil URL detail sebelum dihapus, untuk diuji di langkah berikutnya.
    companies.open_manage(company_data.name)
    detail_url = page.url

    companies.open()
    companies.delete_company(company_data.name)

    # Tier 2: record hilang dari list.
    count = companies.count_rows_matching(company_data.name)
    assert count == 0, f"Masih ada {count} record bernama {company_data.name!r} setelah dihapus"

    # Tier 2: dan tidak bisa diakses lewat URL langsung.
    # Ini yang membedakan 'benar-benar terhapus' dari 'sekadar disembunyikan dari list'.
    response = page.goto(detail_url, wait_until="networkidle")
    allure.attach(
        f"URL: {detail_url}\nstatus: {response.status if response else 'n/a'}\nfinal URL: {page.url}",
        name="akses URL detail setelah delete",
        attachment_type=allure.attachment_type.TEXT,
    )
    assert response is None or response.status >= 400 or page.url != detail_url, (
        "URL detail masih dapat diakses setelah company dihapus — "
        "record kemungkinan hanya disembunyikan dari list, bukan terhapus"
    )
