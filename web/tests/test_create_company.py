"""
TC-WEB-005 s/d TC-WEB-012 — create company beserta edge case-nya.

CATATAN soal cascade:
Cascade muncul BERTAHAP — Province, City, District, Sub District, dan Postal
Code baru tampil setelah Country dipilih. Level keempat bernama "Sub District"
(brief menyebutnya "Zone"), dan Postal Code terisi OTOMATIS, bukan dipilih.
"""
import allure
import pytest

from web.pages.companies_page import CompaniesPage
from web.pages.company_detail_page import CompanyDetailPage
from web.pages.register_company_wizard import RegisterCompanyWizard


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-005 Create company with valid data")
def test_create_company(page, env, created_company):
    """
    Company dibuat oleh fixture created_company — yang sekaligus menghapusnya
    di teardown. Test ini memverifikasi hasilnya.
    """
    companies = CompaniesPage(page)
    companies.open(env["base_url"])

    # Tier 2: record benar-benar ADA di daftar, bukan sekadar toast sukses.
    # Jumlahnya tepat 1 — sekaligus membuktikan tidak ada duplikat.
    count = companies.count_companies_named(created_company["name"])
    assert count == 1, (
        f"Diharapkan tepat 1 company bernama {created_company['name']!r}, dapat {count}"
    )

    # Tier 2: company baru harus berstatus Active (trial 30 hari).
    # Ini juga prasyarat skenario mobile — company Expired tidak bisa dipakai login.
    status = companies.status_of(created_company["name"])
    assert status == "Active", (
        f"Company baru berstatus {status!r}, diharapkan 'Active'. "
        "Skenario mobile membutuhkan company aktif."
    )


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-007 Next stays disabled until Step 1 is valid")
def test_next_disabled_until_step_one_valid(page, env, company_data):
    """
    Aplikasi men-disable Next selama Step 1 belum lengkap — pola yang sama
    dengan tombol Log In di Account Center.

    Test ini juga memverifikasi validasi bereaksi terhadap PENGHAPUSAN nilai,
    bukan hanya terhadap pengisian pertama. Validasi yang hanya fire saat
    input pertama membuat user bisa mengosongkan field wajib lalu tetap lanjut.
    """
    wizard = RegisterCompanyWizard(page)
    wizard.open(env["base_url"])

    assert not wizard.is_next_enabled(), "Next sudah enabled padahal form masih kosong"

    data = company_data.model_dump()
    wizard.fill_step_one(data)
    assert wizard.is_next_enabled(), "Next tidak enabled padahal seluruh Step 1 terisi valid"

    wizard.clear_field("name")
    assert not wizard.is_next_enabled(), (
        "Next masih enabled setelah Company Name dikosongkan — "
        "validasi tidak bereaksi terhadap penghapusan nilai"
    )

    wizard.f["name"].fill(data["name"])
    assert wizard.is_next_enabled(), "Next tidak kembali enabled setelah field diisi ulang"


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-011 Branch step requires agreement before Register")
def test_register_requires_agreement(page, env, company_data):
    """
    Step 3 mengaku opsional ("If left unfilled, a default branch will be
    created"), tetapi Branch Name sudah terisi otomatis dengan "Headquarter"
    dan catatan di bawah form menyatakan mengisi Branch Name membuat seluruh
    field wajib.

    Test ini memverifikasi kontradiksi tersebut: apakah Register benar-benar
    terkunci sebelum checkbox persetujuan dicentang.

    Sengaja BERHENTI sebelum menekan Register — test ini tidak membuat data.
    """
    wizard = RegisterCompanyWizard(page)
    wizard.open(env["base_url"])

    data = company_data.model_dump()
    wizard.fill_step_one(data)
    wizard.click_next()
    wizard.complete_step_two()

    # Sampai di Step 3. Isi datanya tanpa mencentang persetujuan.
    wizard.fill_from_company_records.click()

    default_branch = wizard.branch_name()
    allure.attach(
        f"Branch Name terisi otomatis: {default_branch!r}",
        name="nilai default branch",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert not wizard.is_register_enabled(), (
        "Tombol Register enabled padahal checkbox persetujuan belum dicentang"
    )

    wizard.agree_checkbox.check()
    assert wizard.is_register_enabled(), (
        "Tombol Register tetap disabled setelah persetujuan dicentang"
    )


@pytest.mark.web
@pytest.mark.tier2
@allure.title("TC-WEB-008 Company name stored trimmed")
def test_company_name_stored_trimmed(page, env, company_data):
    """
    Edge case: input hasil copy-paste sering membawa spasi tak terlihat.
    Input tak ter-trim menciptakan record duplikat semu dan merusak pencarian
    dengan pencocokan persis.

    Test ini membuat companynya sendiri (bukan lewat fixture) karena datanya
    sengaja dimodifikasi — dan menghapusnya di blok finally.
    """
    clean_name = company_data.name
    data = company_data.model_dump()
    data["name"] = f"   {clean_name}   "

    wizard = RegisterCompanyWizard(page)
    wizard.open(env["base_url"])
    wizard.fill_step_one(data)
    wizard.click_next()
    wizard.complete_step_two()
    wizard.complete_step_three(data)

    detail = CompanyDetailPage(page)
    detail.wait_loaded()
    mongo_id = detail.mongo_id_from_url()

    try:
        stored = detail.get_field("name")

        allure.attach(
            f"input : {data['name']!r}\nstored: {stored!r}",
            name="perbandingan nilai sebelum dan sesudah disimpan",
            attachment_type=allure.attachment_type.TEXT,
        )

        # Tier 2: assert EXACT string. Memakai 'in' akan meloloskan nilai yang
        # masih membawa spasi — justru bug yang sedang diuji.
        assert stored == clean_name, (
            f"Nama tidak ter-trim saat disimpan: {stored!r} (diharapkan {clean_name!r})"
        )
    finally:
        page.goto(
            f"{env['base_url'].rstrip('/')}/companies/manage-companies/{mongo_id}/profile",
            wait_until="networkidle",
        )
        CompanyDetailPage(page).delete()


@pytest.mark.web
@pytest.mark.negative
@allure.title("TC-WEB-012 Required field validation on Step 1")
@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("email", ""),
        ("phone", ""),
        ("street_address", ""),
    ],
)
def test_required_field_blocks_next(page, env, company_data, field, value):
    """
    Setiap field wajib yang kosong harus menahan tombol Next.

    Parametrize dipakai supaya tiap field jadi baris terpisah di Allure —
    kalau digabung dalam satu test, kegagalan pada field pertama akan
    menyembunyikan tiga field berikutnya.

    Aplikasi memakai tombol disabled sebagai mekanisme validasi, bukan pesan
    error. Karena itu yang di-assert adalah status tombol, bukan teks error
    yang memang tidak muncul.
    """
    wizard = RegisterCompanyWizard(page)
    wizard.open(env["base_url"])

    data = company_data.model_dump()
    data[field] = value
    wizard.fill_step_one(data)

    # Negative: Next harus tetap terkunci saat ada field wajib yang kosong.
    assert not wizard.is_next_enabled(), (
        f"Next enabled padahal field wajib {field!r} kosong"
    )


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-006 Changing Province resets dependent cascade fields")
def test_cascade_parent_reset(page, env, company_data):
    """
    Edge case paling berisiko pada form ini.

    City yang tertinggal saat Province diubah akan membuat alamat yang
    mustahil secara geografis ikut tersubmit — mis. Province "JAWA BARAT"
    dengan City "KOTA GORONTALO". Happy path tidak pernah menyentuh ini
    karena hanya memilih ke bawah, tidak pernah mengubah parent.
    """
    wizard = RegisterCompanyWizard(page)
    wizard.open(env["base_url"])

    data = company_data.model_dump()
    wizard.fill_step_one(data)

    before = wizard.snapshot_cascade()
    allure.attach(
        "\n".join(f"{k}: {v!r}" for k, v in before.items()),
        name="cascade sebelum Province diubah",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Ubah ke provinsi lain. Sengaja tanpa menunggu child terisi ulang —
    # perilaku child itulah yang sedang diuji.
    new_province = wizard.change_province_to_second_option()
    allure.attach(
        f"Province diubah dari {before['province']!r} ke {new_province!r}",
        name="perubahan province",
        attachment_type=allure.attachment_type.TEXT,
    )

    after = wizard.snapshot_cascade()
    allure.attach(
        "\n".join(f"{k}: {v!r}" for k, v in after.items()),
        name="cascade setelah Province diubah",
        attachment_type=allure.attachment_type.TEXT,
    )

    stale = [
        key
        for key in ("city", "district", "sub_district", "postal_code")
        if after[key] == before[key] and before[key] not in ("", "Choose City")
    ]

    assert not stale, (
        f"Field berikut masih membawa nilai dari Province lama: {stale}. "
        f"Nilai tertinggal: { {k: before[k] for k in stale} }. "
        "Kombinasi wilayah yang mustahil bisa ikut tersubmit."
    )