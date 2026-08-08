"""
TC-WEB-013 — Verify company detail matches input, field by field.

Test paling bernilai di seluruh suite: brief menyebut kedalaman assertion
Tier 2 sebagai satu dari dua hal yang paling menggerakkan penilaian.
"""
import allure
import pytest

from web.pages.companies_page import CompaniesPage
from web.pages.company_detail_page import CompanyDetailPage

# Pemetaan field detail -> field data input.
# Dipisah jadi konstanta supaya penambahan field cukup di satu tempat,
# dan supaya pesan kegagalan bisa menyebut nama field yang ramah dibaca.
FIELD_MAP = [
    ("name", "name", "Company Name"),
    ("industry_type", "industry_type", "Industry Type"),
    ("company_type", "company_type", "Company Type"),
    ("address", "street_address", "Street Address"),
    ("postal_code", "postal_code", "Postal Code"),
    ("email", "email", "Email"),
    ("phone", "phone", "Phone"),
]


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-013 Verify company detail matches input field by field")
def test_company_detail_matches_input(page, created_company):
    expected = created_company["input"].model_dump()

    companies = CompaniesPage(page)
    companies.open()
    companies.open_manage(created_company["name"])

    actual = CompanyDetailPage(page).get_all_fields()

    # Kumpulkan SEMUA ketidakcocokan dulu, baru gagalkan sekali.
    #
    # Kenapa begini, bukan assert satu per satu yang langsung berhenti:
    #   assert berantai berhenti di field pertama yang salah. Kalau tiga field
    #   bermasalah, kita hanya tahu satu, perbaiki, jalankan lagi, tahu yang
    #   kedua, dan seterusnya. Mengumpulkan dulu memberi gambaran utuh dalam
    #   satu run — dan pesannya tetap menyebut field mana saja yang salah.
    mismatches = []
    for detail_key, input_key, label in FIELD_MAP:
        # Tier 2: nilai tersimpan harus SAMA PERSIS dengan yang diinput.
        # Perbandingan '==' , bukan 'in' — 'in' akan meloloskan nilai yang
        # masih membawa spasi berlebih, yaitu bug yang diuji TC-WEB-008.
        if actual[detail_key] != str(expected[input_key]):
            mismatches.append(
                f"  {label}: expected {expected[input_key]!r}, got {actual[detail_key]!r}"
            )

    allure.attach(
        "\n".join(f"{k}: {v!r}" for k, v in actual.items()),
        name="nilai yang tampil di detail view",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Tier 2: satu field tidak cocok = test FAIL, dan pesannya menyebut fieldnya.
    assert not mismatches, (
        f"{len(mismatches)} field tidak cocok dengan input:\n" + "\n".join(mismatches)
    )
