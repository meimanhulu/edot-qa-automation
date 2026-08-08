"""TC-WEB-001 s/d TC-WEB-004 — login."""
import allure
import pytest

from web.pages.login_page import LoginPage


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-001 Login with valid credentials")
def test_login_valid(page):
    """
    Login sudah terjadi di fixture session (storage_state). Test ini
    memverifikasi HASILNYA, bukan mengulang prosesnya — itulah sebabnya
    tidak ada pemanggilan login() di sini.
    """
    login = LoginPage(page)
    assert login.is_dashboard_visible(), "Greeting 'Welcome Back,' tidak tampil di dashboard"


@pytest.mark.web
@pytest.mark.negative
@allure.title("TC-WEB-002 Login rejected with invalid password")
def test_login_invalid_password(anon_page, env):
    """
    Pakai anon_page: test ini butuh keadaan LOGOUT. Dengan fixture `page`
    yang sudah ter-autentikasi, test ini tidak menguji apa pun.
    """
    login = LoginPage(anon_page)
    login.open(env["base_url"])
    login.submit_email(env["email"])
    login.submit_password("WrongPass123!")

    # Negative: assert TEKS pesan error, bukan sekadar "masih di halaman login".
    error = login.error_text()
    assert error.strip(), "Tidak ada pesan error yang tampil saat password salah"
    assert "password" in error.lower() or "incorrect" in error.lower(), (
        f"Pesan error tidak menyebut kredensial salah: {error!r}"
    )
    assert not login.is_dashboard_visible(), "Dashboard tercapai padahal password salah"


@pytest.mark.web
@pytest.mark.negative
@allure.title("TC-WEB-003 Login blocked when email empty")
def test_login_empty_email(anon_page, env):
    login = LoginPage(anon_page)
    login.open(env["base_url"])
    login.submit_email("")

    # Negative: pesan required-field yang spesifik untuk field email.
    error = login.error_text()
    assert error.strip(), "Tidak ada pesan error saat email dikosongkan"
    assert "email" in error.lower(), f"Pesan error tidak menyebut field email: {error!r}"


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-004 Email accepted regardless of case and whitespace")
def test_login_email_normalization(anon_page, env):
    """
    Edge case: input hasil copy-paste sering membawa spasi tak terlihat.

    Kalau sistem justru menolak, JANGAN ubah expected value agar hijau —
    catat sebagai temuan. Brief menyebut hal itu sebagai non-negotiable failure.
    """
    padded = f"  {env['email'].upper()}  "

    login = LoginPage(anon_page)
    login.open(env["base_url"])
    login.login(padded, env["password"])

    assert login.is_dashboard_visible(), (
        f"Login gagal dengan email ber-spasi dan huruf besar: {padded!r}. "
        "Bila ini perilaku yang disengaja, sistem harus menampilkan error spesifik."
    )
