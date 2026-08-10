"""
Fixture khusus suite Playwright.

Tiga syarat brief dipenuhi di sini:
  1. login SEKALI per sesi, dibagikan lewat storage_state
  2. screenshot dilampirkan ke Allure pada SETIAP kegagalan
  3. cleanup jalan MESKI test gagal
"""
from pathlib import Path

import allure
import pytest
from playwright.sync_api import sync_playwright

from web.pages.companies_page import CompaniesPage
from web.pages.company_detail_page import CompanyDetailPage
from web.pages.login_page import LoginPage
from web.pages.register_company_wizard import RegisterCompanyWizard


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance, env):
    b = playwright_instance.chromium.launch(headless=env["headless"])
    yield b
    b.close()


@pytest.fixture(scope="session")
def storage_state_path(browser, env, tmp_path_factory) -> str:
    """
    Login SEKALI, simpan cookie + localStorage ke file, kembalikan path-nya.

    Brief: "Log in once per session and share auth via storage_state — do not
    log in inside every test."

    Cara memverifikasi ini benar: hitung request ke endpoint login dalam satu
    run penuh. Harus tepat 1, berapa pun jumlah test-nya.
    """
    path = tmp_path_factory.mktemp("auth") / "storage_state.json"

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(env["timeout_ms"])

    login = LoginPage(page)
    login.open(env["base_url"])
    login.login(env["email"], env["password"])

    context.storage_state(path=str(path))
    context.close()
    return str(path)


@pytest.fixture
def page(browser, storage_state_path, env):
    """
    Page yang sudah ter-autentikasi, satu context baru per test.

    Context baru tiap test menjaga isolasi: satu test tidak mewarisi state
    UI test sebelumnya. Yang dibagikan hanya autentikasinya.
    """
    context = browser.new_context(storage_state=storage_state_path)
    p = context.new_page()
    p.set_default_timeout(env["timeout_ms"])
    yield p
    context.close()


@pytest.fixture
def anon_page(browser, env):
    """
    Page TANPA autentikasi. Dipakai test Negative yang butuh keadaan logout.

    Tanpa fixture ini, test login gagal akan memakai sesi yang sudah login
    dan tidak menguji apa pun.
    """
    context = browser.new_context()
    p = context.new_page()
    p.set_default_timeout(env["timeout_ms"])
    yield p
    context.close()


@pytest.fixture(autouse=True)
def screenshot_on_failure(request):
    """
    Lampirkan screenshot ke Allure saat test gagal.

    autouse=True: brief mensyaratkan screenshot pada SETIAP kegagalan, bukan
    hanya pada test yang ingat memanggilnya.
    """
    yield

    report = getattr(request.node, "rep_call", None)
    if report is None or not report.failed:
        return

    for name in ("page", "anon_page"):
        if name not in request.fixturenames:
            continue
        try:
            pg = request.getfixturevalue(name)
            allure.attach(
                pg.screenshot(full_page=True),
                name=f"screenshot-on-failure ({name})",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            # Screenshot gagal tidak boleh menutupi kegagalan aslinya.
            pass


@pytest.fixture
def created_company(page, env, company_data):
    """
    Buat company lewat wizard 3 langkah, serahkan ke test, HAPUS di teardown.

    Cleanup ada di fixture — bukan di baris terakhir test — supaya tetap
    berjalan meski test gagal di tengah. Brief menyebut "test data left
    behind on the shared environment" sebagai non-negotiable failure.

    Yang dikembalikan:
        input       objek CompanyData yang dipakai mengisi form
        name        nama company, untuk pencarian di daftar
        company_id  ID yang tampil di halaman detail (dipakai skenario mobile)
        mongo_id    ID pada URL, untuk menguji akses langsung setelah delete
    """
    wizard = RegisterCompanyWizard(page)
    wizard.open(env["base_url"])

    data = company_data.model_dump()

    # fill_step_one mengembalikan nilai dropdown yang BENAR-BENAR terpilih.
    # Digabung ke data supaya verifikasi Tier 2 membandingkan terhadap apa
    # yang masuk ke form, bukan terhadap nilai yang diasumsikan.
    chosen = wizard.fill_step_one(data)
    data.update(chosen)

    wizard.click_next(expect_locator=wizard.step_two_marker)
    wizard.complete_step_two()
    wizard.complete_step_three(data)

    # Setelah Register, aplikasi mengarahkan ke DAFTAR companies — bukan ke
    # halaman detail.
    companies = CompaniesPage(page)
    companies.open(env["base_url"])
    companies.expect_company_count(company_data.name, 1)

    # Company ID diambil dari KARTU di daftar, bukan dari halaman detail.
    #
    # Kartu sudah menampilkan ID di bawah nama, sementara halaman detail
    # memuat datanya secara asinkron dan kadang tetap kosong. Mengambilnya
    # dari daftar menghilangkan satu titik gagal dari fixture — fixture
    # seharusnya menyiapkan data, bukan menguji halaman detail.
    ids = companies.company_ids_named(company_data.name)

    # mongo_id hanya ada di URL halaman detail, jadi Manage tetap dibuka —
    # tetapi TANPA menunggu datanya termuat.
    companies.open_manage(company_data.name)
    mongo_id = CompanyDetailPage(page).mongo_id_from_url()

    info = {
        "input": company_data,
        "submitted": data,          # data teks + nilai dropdown yang terpilih
        "name": company_data.name,
        "company_id": ids[0] if ids else "",
        "mongo_id": mongo_id,
    }

    allure.attach(
        "\n".join(f"{k}: {v!r}" for k, v in data.items())
        + f"\n\ncompany_id: {info['company_id']}\nmongo_id: {info['mongo_id']}",
        name="company yang dibuat fixture",
        attachment_type=allure.attachment_type.TEXT,
    )

    yield info

    # ---- teardown: selalu jalan, apa pun hasil test ----
    try:
        page.goto(
            f"{env['base_url'].rstrip('/')}/companies/manage-companies/{info['mongo_id']}/profile"
        )
        CompanyDetailPage(page).wait_loaded()
        CompanyDetailPage(page).delete()

        companies.open(env["base_url"])
        remaining = companies.count_companies_named(info["name"])
        if remaining != 0:
            allure.attach(
                f"Cleanup TIDAK bersih: masih ada {remaining} record bernama "
                f"{info['name']!r}. Hapus manual di eSuite.",
                name="cleanup-warning",
                attachment_type=allure.attachment_type.TEXT,
            )
    except Exception as e:
        allure.attach(
            f"Cleanup gagal: {type(e).__name__}: {e}\n"
            f"Company {info['name']!r} (id {info['company_id']}) kemungkinan masih tertinggal.",
            name="cleanup-error",
            attachment_type=allure.attachment_type.TEXT,
        )