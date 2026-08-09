"""
TC-WEB-013 — Verify company detail matches input, field by field.

Test paling bernilai di seluruh suite: brief menyebut kedalaman assertion
Tier 2 sebagai satu dari dua hal yang paling menggerakkan penilaian.
"""
import allure
import pytest

from web.pages.company_detail_page import (
    READONLY_FIELDS,
    CompanyDetailPage,
)

# Pemetaan field di halaman detail -> field pada data input.
# Hanya field yang memang berasal dari input wizard yang dibandingkan.
# Cascade (Province s/d Postal Code) diisi sistem, bukan oleh user, sehingga
# tidak punya nilai pembanding di sisi input.
FIELD_MAP = [
    ("name", "name", "Company Name"),
    ("industry_type", "industry_type", "Industry Type"),
    ("company_type", "company_type", "Company Type"),
    ("email", "email", "Email"),
    ("country", "country", "Country"),
]


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-013 Verify company detail matches input field by field")
def test_company_detail_matches_input(page, created_company):
    # Dibandingkan terhadap nilai yang BENAR-BENAR masuk ke form: teks dari
    # data AI, dropdown dari opsi yang dipilih aplikasi. Membandingkan
    # terhadap data AI saja akan salah, karena nilai dropdown ditentukan
    # aplikasi — bukan oleh data test.
    expected = created_company["submitted"]

    detail = CompanyDetailPage(page)
    detail.wait_loaded()
    actual = detail.get_all_fields()

    allure.attach(
        "\n".join(f"{k}: {v!r}" for k, v in actual.items()),
        name="nilai yang tampil di halaman detail",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Kumpulkan SEMUA ketidakcocokan dulu, baru gagalkan sekali.
    #
    # Kenapa begini, bukan assert berantai yang langsung berhenti:
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

    # Tier 2: satu field tidak cocok = test FAIL, dan pesannya menyebut fieldnya.
    assert not mismatches, (
        f"{len(mismatches)} field tidak cocok dengan input:\n" + "\n".join(mismatches)
    )


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-013b Company ID is present and read-only")
def test_company_id_present_and_readonly(page, created_company):
    """
    Company ID dihasilkan sistem, bukan diinput user.

    Dua hal diverifikasi:
      1. nilainya ada dan berupa angka — dipakai skenario mobile untuk login
      2. field-nya read-only — ID tidak boleh bisa diubah dari UI
    """
    detail = CompanyDetailPage(page)
    detail.wait_loaded()

    company_id = detail.company_id()

    # Tier 2: ID benar-benar dihasilkan, bukan kosong.
    assert company_id.isdigit(), (
        f"Company ID bukan angka: {company_id!r}. Nilai ini dipakai login eWork SFA."
    )

    # Tier 2: ID tidak boleh editable.
    assert not detail.is_field_editable("company_id"), (
        "Company ID dapat diubah dari UI — seharusnya read-only"
    )


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-013c Cascade fields are read-only")
def test_cascade_fields_are_readonly(page, created_company):
    """
    Membuktikan temuan yang membatalkan TC-WEB-006.

    Brief menggambarkan cascade Country > Province > City > District > Zone >
    Postal Code sebagai field yang saling bergantung dan bisa dipilih. Di
    aplikasi sebenarnya, seluruhnya terkunci di halaman detail dan hanya
    Country yang muncul di wizard.

    Test ini merekam kenyataan itu sebagai fakta yang terverifikasi, bukan
    sebagai asumsi di dokumen. Kalau kelak aplikasi membukanya, test ini gagal
    dan memberi tahu bahwa TC-WEB-006 sudah bisa diuji.
    """
    detail = CompanyDetailPage(page)
    detail.wait_loaded()

    editable = [f for f in READONLY_FIELDS if detail.is_field_editable(f)]

    allure.attach(
        "\n".join(f"{f}: editable={detail.is_field_editable(f)}" for f in READONLY_FIELDS),
        name="status editable field cascade",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert not editable, (
        f"Field berikut ternyata dapat diubah: {editable}. "
        "Bila cascade sudah dibuka, TC-WEB-006 (parent reset) kini dapat diuji "
        "dan perlu ditambahkan ke suite."
    )