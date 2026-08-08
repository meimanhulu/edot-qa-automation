"""TC-WEB-005 s/d TC-WEB-012 — create company beserta edge case-nya."""
import allure
import pytest

from web.pages.companies_page import CompaniesPage
from web.pages.register_company_wizard import RegisterCompanyWizard


def _open_wizard(page) -> RegisterCompanyWizard:
    companies = CompaniesPage(page)
    companies.open()
    companies.click_add_company()
    return RegisterCompanyWizard(page)


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-005 Create company with valid data")
def test_create_company(page, created_company):
    """
    Pembuatan company terjadi di fixture created_company — yang sekaligus
    menghapusnya di teardown. Test ini memverifikasi hasilnya.
    """
    companies = CompaniesPage(page)
    companies.open()

    # Tier 2: record benar-benar ADA di list, bukan sekadar toast sukses.
    # Dan jumlahnya tepat 1 — membuktikan tidak ada duplikat.
    count = companies.count_rows_matching(created_company["name"])
    assert count == 1, f"Diharapkan tepat 1 company bernama {created_company['name']!r}, dapat {count}"


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-006 Changing parent resets dependent cascade fields")
def test_cascade_parent_reset(page, company_data):
    """
    Edge case paling berisiko: City yang tertinggal saat Province diubah
    membuat alamat yang mustahil secara geografis ikut tersubmit.
    """
    wizard = _open_wizard(page)
    wizard.fill_basic_fields(company_data.model_dump())
    wizard.select_cascade(
        company_data.country, company_data.province, company_data.city,
        company_data.district, company_data.zone, company_data.postal_code,
    )

    before = wizard.get_cascade_values()
    allure.attach(str(before), name="cascade sebelum province diubah",
                  attachment_type=allure.attachment_type.TEXT)

    # Ubah parent. Sengaja tanpa menunggu child — perilaku child itulah
    # yang sedang diuji.
    new_province = "Jawa Barat" if company_data.province != "Jawa Barat" else "DKI Jakarta"
    wizard.change_province(new_province)

    after = wizard.get_cascade_values()
    allure.attach(str(after), name="cascade setelah province diubah",
                  attachment_type=allure.attachment_type.TEXT)

    stale = [
        key for key in ("city", "district", "zone", "postal_code")
        if after[key] == before[key] and before[key] != ""
    ]
    assert not stale, (
        f"Field berikut masih membawa nilai dari Province lama: {stale}. "
        f"Nilai lama: { {k: before[k] for k in stale} }"
    )


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-007 Next re-disables when required field cleared")
def test_next_reacts_to_field_removal(page, company_data):
    wizard = _open_wizard(page)
    wizard.fill_basic_fields(company_data.model_dump())
    wizard.select_cascade(
        company_data.country, company_data.province, company_data.city,
        company_data.district, company_data.zone, company_data.postal_code,
    )
    assert wizard.is_next_enabled(), "Next belum enabled padahal seluruh field terisi valid"

    wizard.clear_field("name")
    assert not wizard.is_next_enabled(), (
        "Next masih enabled setelah Company Name dikosongkan — "
        "validasi tidak bereaksi terhadap penghapusan nilai"
    )

    wizard.f["name"].fill(company_data.name)
    assert wizard.is_next_enabled(), "Next tidak kembali enabled setelah field diisi ulang"


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-008 Company name stored trimmed")
def test_company_name_stored_trimmed(page, company_data):
    """
    Edge case: input tak ter-trim menciptakan record duplikat semu dan
    merusak exact-match search.
    """
    from web.pages.company_detail_page import CompanyDetailPage

    clean_name = company_data.name
    padded_name = f"   {clean_name}   "

    data = company_data.model_dump()
    data["name"] = padded_name

    wizard = _open_wizard(page)
    wizard.fill_basic_fields(data)
    wizard.select_cascade(
        data["country"], data["province"], data["city"],
        data["district"], data["zone"], data["postal_code"],
    )
    wizard.click_next()
    wizard.complete_step_two(data)
    wizard.complete_step_three(data)
    wizard.submit()

    companies = CompaniesPage(page)
    companies.open()
    try:
        companies.open_manage(clean_name)
        stored = CompanyDetailPage(page).get_all_fields()["name"]

        # Tier 2: assert EXACT string. 'in' atau 'contains' akan meloloskan
        # nilai yang masih ber-spasi — justru bug yang sedang diuji.
        assert stored == clean_name, (
            f"Nama tidak ter-trim saat disimpan: {stored!r} (diharapkan {clean_name!r})"
        )
    finally:
        # Cleanup manual: test ini tidak memakai fixture created_company
        # karena datanya sengaja dimodifikasi.
        companies.open()
        companies.delete_company(clean_name)


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-010 Double submit does not create duplicate")
def test_double_submit_no_duplicate(page, company_data):
    wizard = _open_wizard(page)
    data = company_data.model_dump()
    wizard.fill_basic_fields(data)
    wizard.select_cascade(
        data["country"], data["province"], data["city"],
        data["district"], data["zone"], data["postal_code"],
    )
    wizard.click_next()
    wizard.complete_step_two(data)
    wizard.complete_step_three(data)
    wizard.submit_twice()

    companies = CompaniesPage(page)
    companies.open()
    try:
        # Tier 2: menghitung baris, bukan membaca toast.
        count = companies.count_rows_matching(company_data.name)
        assert count == 1, (
            f"Double submit menghasilkan {count} record bernama {company_data.name!r}. "
            "Diharapkan tepat 1 — tombol submit seharusnya disabled setelah klik pertama."
        )
    finally:
        companies.open()
        companies.delete_company(company_data.name)


@pytest.mark.web
@pytest.mark.negative
@allure.title("TC-WEB-011 Duplicate company name rejected")
def test_duplicate_company_name(page, created_company):
    data = created_company["input"].model_dump()
    data["email"] = "admin2@duplicate-test.co.id"

    wizard = _open_wizard(page)
    wizard.fill_basic_fields(data)
    wizard.select_cascade(
        data["country"], data["province"], data["city"],
        data["district"], data["zone"], data["postal_code"],
    )
    wizard.click_next()
    wizard.complete_step_two(data)
    wizard.complete_step_three(data)
    wizard.submit()

    # Negative: pesan error spesifik soal duplikat.
    error = wizard.field_error_text("name")
    assert "exist" in error.lower() or "sudah" in error.lower(), (
        f"Pesan error tidak menyebut duplikasi: {error!r}"
    )

    companies = CompaniesPage(page)
    companies.open()
    count = companies.count_rows_matching(created_company["name"])
    assert count == 1, f"Jumlah record berubah jadi {count} setelah percobaan duplikat"


@pytest.mark.web
@pytest.mark.negative
@allure.title("TC-WEB-012 Required field and format validation")
@pytest.mark.parametrize(
    "field,value,expect_in_error",
    [
        ("name", "", "required"),
        ("email", "admin@nodomain", "email"),
        ("phone", "021-ABC-DEFG", "phone"),
    ],
)
def test_field_validation(page, company_data, field, value, expect_in_error):
    """
    Parametrize dipakai supaya tiap kondisi jadi baris terpisah di Allure.

    Kalau digabung dalam satu test, kegagalan pada kondisi pertama akan
    menyembunyikan dua kondisi berikutnya.
    """
    wizard = _open_wizard(page)
    data = company_data.model_dump()
    data[field] = value
    wizard.fill_basic_fields(data)

    error = wizard.field_error_text(field)
    assert error.strip(), f"Tidak ada pesan error untuk field {field!r} bernilai {value!r}"
    assert expect_in_error in error.lower(), (
        f"Pesan error untuk {field!r} tidak menyebut '{expect_in_error}': {error!r}"
    )
    assert not wizard.is_next_enabled(), f"Next masih enabled padahal {field!r} tidak valid"
