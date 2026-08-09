"""TC-WEB-001 s/d TC-WEB-004 — login."""
import allure
import pytest

from web.pages.login_page import LoginPage


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-001 Login with valid credentials")
def test_login_valid(page, env):
    """
    Login sudah terjadi di fixture session (storage_state), jadi test ini
    memverifikasi HASILNYA — bukan mengulang prosesnya.

    Halaman tetap perlu dibuka: storage_state memulihkan sesi, tetapi
    context baru selalu mulai dari about:blank.
    """
    login = LoginPage(page)
    login.goto(env["base_url"])

    assert login.is_dashboard_visible(), (
        "Greeting 'Welcome Back,' tidak tampil setelah membuka eSuite "
        "dengan sesi yang sudah login"
    )


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
    login.submit_username(env["email"])
    login.submit_password("WrongPass123!")

    # Negative: assert ISI pesan error, bukan sekadar "masih di halaman login".
    # Account Center menaruh pesannya di query parameter `err`, bukan di DOM.
    error = login.error_text()
    allure.attach(
        f"URL setelah submit: {anon_page.url}\npesan error: {error!r}",
        name="bukti penolakan login",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert error.strip(), "Tidak ada pesan error yang tampil saat password salah"
    assert any(k in error.lower() for k in ("password", "incorrect", "invalid")), (
        f"Pesan error tidak menyebut kredensial salah: {error!r}"
    )

    # Timeout dipendekkan: di sini kita justru MENGHARAP dashboard tidak muncul,
    # jadi tidak perlu menunggu penuh.
    assert not login.is_dashboard_visible(timeout=3000), (
        "Dashboard tercapai padahal password salah"
    )


@pytest.mark.web
@pytest.mark.negative
@allure.title("TC-WEB-003 Log In button disabled when username is empty")
def test_login_button_disabled_when_username_empty(anon_page, env):
    """
    Aplikasi men-disable tombol Log In selama username kosong — itu perilaku
    yang benar, dan bentuk validasi yang dipakai Account Center.

    Karena itu test ini memverifikasi STATUS TOMBOL, bukan mengklik lalu
    mengharap pesan error yang memang tidak akan pernah muncul.
    """
    login = LoginPage(anon_page)
    login.open(env["base_url"])
    login.open_username_screen()

    # Negative: tombol harus disabled saat field kosong.
    assert not login.is_login_button_enabled(), (
        "Tombol Log In enabled padahal username masih kosong"
    )

    # Dan harus kembali enabled setelah diisi — membuktikan validasinya
    # bereaksi terhadap isi field, bukan sekadar disabled permanen.
    login.fill_username(env["email"])
    assert login.is_login_button_enabled(), (
        "Tombol Log In tetap disabled padahal username sudah diisi"
    )


@pytest.mark.web
@pytest.mark.tier1
@allure.title("TC-WEB-004 Email with surrounding whitespace and different case")
def test_login_email_normalization(anon_page, env):
    """
    Edge case: input hasil copy-paste sering membawa spasi tak terlihat.

    Temuan: aplikasi TIDAK men-trim input, sehingga tombol Log In tetap
    disabled untuk email ber-spasi. Test ini mendokumentasikan perilaku
    sebenarnya, bukan memaksanya hijau.

    Kalau kelak aplikasi menormalisasi input, test ini akan gagal — dan itu
    justru benar: perubahan perilaku harus terlihat, bukan lolos diam-diam.
    """
    padded = f"  {env['email'].upper()}  "

    login = LoginPage(anon_page)
    login.open(env["base_url"])
    login.open_username_screen()
    login.fill_username(padded)

    enabled = login.is_login_button_enabled()

    allure.attach(
        f"input: {padded!r}\ntombol Log In enabled: {enabled}",
        name="perilaku terhadap email ber-spasi",
        attachment_type=allure.attachment_type.TEXT,
    )

    assert not enabled, (
        f"Tombol Log In enabled untuk email ber-spasi {padded!r}. "
        "Perilaku aplikasi berubah — sebelumnya input tidak di-trim. "
        "Verifikasi apakah normalisasi memang sudah ditambahkan."
    )