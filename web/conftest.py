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
    Buat company, serahkan datanya ke test, HAPUS di teardown.

    Cleanup ada di fixture — bukan sebagai langkah terakhir di dalam test —
    supaya tetap jalan meski test gagal di tengah.

    Brief: "Test data left behind on the shared environment" adalah
    non-negotiable failure.
    """
    companies = CompaniesPage(page)
    companies.open()
    companies.click_add_company()

    wizard = RegisterCompanyWizard(page)
    wizard.fill_basic_fields(company_data.model_dump())
    wizard.select_cascade(
        country=company_data.country,
        province=company_data.province,
        city=company_data.city,
        district=company_data.district,
        zone=company_data.zone,
        postal_code=company_data.postal_code,
    )
    wizard.click_next()
    wizard.complete_step_two(company_data.model_dump())
    wizard.complete_step_three(company_data.model_dump())
    wizard.submit()

    yield {"input": company_data, "name": company_data.name}

    # ---- teardown: selalu jalan ----
    try:
        companies.open()
        companies.delete_company(company_data.name)
        remaining = companies.count_rows_matching(company_data.name)
        if remaining != 0:
            allure.attach(
                f"Cleanup TIDAK bersih: masih ada {remaining} record bernama "
                f"{company_data.name!r}. Hapus manual di eSuite.",
                name="cleanup-warning",
                attachment_type=allure.attachment_type.TEXT,
            )
    except Exception as e:
        allure.attach(
            f"Cleanup gagal: {type(e).__name__}: {e}\n"
            f"Company {company_data.name!r} kemungkinan masih tertinggal.",
            name="cleanup-error",
            attachment_type=allure.attachment_type.TEXT,
        )
