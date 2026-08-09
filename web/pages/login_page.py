"""
LoginPage — alur login eSuite via eDOT Account Center (OIDC).

ALUR SEBENARNYA (hasil inspeksi 09 Agustus 2026, berbeda dari brief):

    esuite.edot.id
        ↓ redirect
    cronus.edot.id/oidc/interaction/<id>      ← Account Center
        ↓
    Layar 1: tombol "Use Email or Username"
        ↓
    Layar 2: input[name=username]  → tombol "Log In"
        ↓
    Layar 3: input[name=password]  → tombol "Log In"
        ↓ redirect balik
    esuite.edot.id → "Welcome Back," + daftar company

Brief menyebut tombolnya "Continue" lalu "Sign In". Kenyataannya KEDUANYA
bertuliskan "Log In". Ditemukan saat inspeksi manual dan dicatat di README.
"""
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import Page, expect

from .base_page import BasePage

# ---------------------------------------------------------------------------
# STRATEGI SELECTOR
#
# Aplikasi ini punya NOL data-testid (diverifikasi:
# document.querySelectorAll('[data-testid]').length === 0), sehingga prioritas
# pertama pada brief tidak tersedia. Yang dipakai, berurutan:
#
#   1. atribut stabil `name`  -> untuk kedua input (prioritas ke-3 brief)
#   2. role + accessible name -> untuk semua tombol (prioritas ke-2 brief)
#   3. text                   -> hanya untuk greeting dashboard, dijustifikasi
#
# Frontend memakai Radix UI, jadi role ARIA-nya benar dan get_by_role andal.
# `id` yang ada bernilai "radix-:rd:" — di-generate ulang tiap render, jadi
# TIDAK boleh dipakai sebagai selector.
# ---------------------------------------------------------------------------


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

        # Layar 1
        self.use_email_button = page.get_by_role("button", name="Use Email or Username")

        # Layar 2 dan 3.
        # `:visible` WAJIB: pada layar 2, input[name=password] sudah ada di DOM
        # sebagai type=hidden, dan pada layar 3 giliran input[name=username]
        # yang tersembunyi. Tanpa filter ini, locator cocok ke elemen yang
        # salah dan fill() gagal dengan pesan yang menyesatkan.
        self.username_input = page.locator('input[name="username"]:visible')
        self.password_input = page.locator('input[name="password"]:visible')

        # Kedua layar memakai tombol dengan nama sama — "Log In".
        self.login_button = page.get_by_role("button", name="Log In")

        # Penanda dashboard setelah redirect balik ke eSuite.
        # JUSTIFIKASI pemakaian text selector: greeting ini tidak punya
        # data-testid maupun role semantik, dan brief sendiri menyebut
        # "Welcome Back," sebagai penanda yang diharapkan.
        self.dashboard_greeting = page.get_by_text("Welcome Back,")

        # Pesan error. Account Center tidak memakai atribut khusus untuk ini,
        # jadi dipakai role="alert" yang standar; error_text() punya fallback
        # bila role tersebut ternyata tidak dipasang.
        self.error_alert = page.get_by_role("alert")

    # ------------------------------------------------------------------
    # Aksi
    # ------------------------------------------------------------------

    def open(self, base_url: str) -> None:
        """
        Buka eSuite; aplikasi akan me-redirect sendiri ke Account Center.

        Menunggu tombol layar 1 muncul, bukan menunggu URL tertentu —
        path OIDC mengandung interaction id yang berubah tiap sesi
        (mis. /oidc/interaction/3NM_mdM8fPSq-BklYOgvA).
        """
        self.goto(base_url)
        expect(self.use_email_button).to_be_visible()

    def open_username_screen(self) -> None:
        """Layar 1 → 2: buka form username tanpa mengisi apa pun."""
        self.use_email_button.click()
        expect(self.username_input).to_be_visible()

    def fill_username(self, username: str) -> None:
        """Isi field username tanpa menekan Log In."""
        self.username_input.fill(username)

    def is_login_button_enabled(self) -> bool:
        """
        Status enabled tombol Log In.

        Aplikasi men-disable tombol selama input belum valid — perilaku yang
        benar. Test Negative untuk field kosong memverifikasi INI, bukan
        mengklik lalu mengharap pesan error yang tidak akan pernah muncul.
        """
        return self.login_button.is_enabled()

    def submit_username(self, username: str) -> None:
        """Layar 1 → 2: buka form, isi username, kirim."""
        self.open_username_screen()
        self.fill_username(username)
        self.login_button.click()

    def submit_password(self, password: str) -> None:
        """
        Layar 3: isi password, kirim.

        Menunggu password_input terlihat lebih dulu — itu penanda transisi
        dari layar 2 ke layar 3 sudah selesai. Tanpa ini, fill() bisa
        berjalan saat DOM masih menampilkan layar sebelumnya.
        """
        expect(self.password_input).to_be_visible()
        self.password_input.fill(password)
        self.login_button.click()

    def login(self, username: str, password: str) -> None:
        """
        Jalankan seluruh alur sampai dashboard eSuite benar-benar termuat.

        Baris terakhir menunggu greeting — itu yang menandai redirect balik
        dari Account Center sudah selesai. Tanpa itu, test berikutnya bisa
        berjalan saat browser masih berada di cronus.edot.id.
        """
        self.submit_username(username)
        self.submit_password(password)

        # Timeout diperpanjang: setelah password dikirim, browser melewati
        # RANTAI redirect OIDC sebelum sampai ke dashboard —
        #   /callback?code=... -> /oidc/token -> /authentication?access_token=...
        # Timeout default expect() 5 detik tidak cukup; halaman masih
        # menampilkan "Redirecting..." saat waktu habis.
        expect(self.dashboard_greeting).to_be_visible(timeout=60000)

    # ------------------------------------------------------------------
    # Pembacaan
    # ------------------------------------------------------------------

    def error_text(self) -> str:
        """
        Teks pesan error yang tampil.

        Dipakai test Negative — brief mensyaratkan assert pesan SPESIFIK,
        bukan sekadar "masih di halaman login".

        Fallback ke pencarian teks bila role="alert" tidak dipasang:
        lebih baik mengembalikan string kosong daripada melempar exception,
        karena test yang memanggil ini sudah punya assert-nya sendiri.
        """
        # Account Center menaruh pesan error di QUERY PARAMETER, bukan di DOM.
        # Contoh: /oidc/interaction/<id>?err=Incorrect%20password&srcPage=...
        # Diperiksa lebih dulu karena ini sumber yang sebenarnya dipakai.
        err = parse_qs(urlparse(self.page.url).query).get("err")
        if err:
            return unquote(err[0])

        if self.error_alert.count() > 0:
            text = self.text_of(self.error_alert.first)
            if text.strip():
                return text

        candidates = self.page.locator("text=/incorrect|invalid|salah|tidak valid|required/i")
        return self.text_of(candidates.first) if candidates.count() > 0 else ""

    def is_dashboard_visible(self, timeout: int = 15000) -> bool:
        """
        Apakah greeting dashboard terlihat.

        Memakai wait_for(), bukan is_visible(), karena halaman bisa masih
        berada di tengah rantai redirect OIDC. is_visible() memeriksa saat
        itu juga dan mengembalikan False untuk halaman yang sebenarnya
        sedang dalam perjalanan.

        Dipakai juga test Negative untuk membuktikan dashboard TIDAK tercapai —
        di situ timeout dipendekkan agar test tidak menunggu sia-sia.
        """
        try:
            self.dashboard_greeting.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False