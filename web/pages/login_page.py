"""
LoginPage — alur login 3 layar eSuite.

Alur dari brief:
  1. klik "Use Email or Username"
  2. submit email
  3. submit password
  4. redirect via eDOT Account Center, lalu KEMBALI ke eSuite

Langkah 4 sering terlewat: assert dashboard tepat setelah klik Sign In akan
gagal karena browser masih di Account Center.
"""
from playwright.sync_api import Page, expect

from .base_page import BasePage

# ---------------------------------------------------------------------------
# SELECTOR — ganti nilainya setelah inspeksi DOM eSuite.
# Prioritas: data-testid > role+name > atribut stabil > text (justifikasi).
# Dikumpulkan di sini supaya saat DOM berubah, cukup satu blok yang disunting.
# ---------------------------------------------------------------------------
SEL = {
    # role + accessible name: tahan terhadap perubahan class/styling
    "use_email_button": ("role", "button", "Use Email or Username"),
    "email_input": ("label", "Email"),
    "continue_button": ("role", "button", "Continue"),
    "password_input": ("label", "Password"),
    "signin_button": ("role", "button", "Sign In"),
    # text sebagai pilihan terakhir — JUSTIFIKASI: greeting dashboard adalah
    # teks statis tanpa data-testid maupun role semantik. Brief sendiri
    # menyebut "Welcome Back," sebagai penanda yang diharapkan.
    "dashboard_greeting": ("text", "Welcome Back,"),
    "error_message": ("testid", "auth-error"),
}


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.use_email_button = page.get_by_role("button", name=SEL["use_email_button"][2])
        self.email_input = page.get_by_label(SEL["email_input"][1])
        self.continue_button = page.get_by_role("button", name=SEL["continue_button"][2])
        self.password_input = page.get_by_label(SEL["password_input"][1])
        self.signin_button = page.get_by_role("button", name=SEL["signin_button"][2])
        self.dashboard_greeting = page.get_by_text(SEL["dashboard_greeting"][1])
        self.error_message = page.get_by_test_id(SEL["error_message"][1])

    def open(self, base_url: str) -> None:
        self.goto(base_url)

    def submit_email(self, email: str) -> None:
        """Layar 1 dan 2: buka form email, isi, lanjut."""
        self.use_email_button.click()
        self.email_input.fill(email)
        self.continue_button.click()

    def submit_password(self, password: str) -> None:
        """Layar 3: isi password, kirim."""
        self.password_input.fill(password)
        self.signin_button.click()

    def login(self, email: str, password: str) -> None:
        """
        Jalankan ketiga layar sampai dashboard benar-benar termuat.

        Baris terakhir menunggu greeting, BUKAN sleep. Itu yang menandai
        redirect Account Center sudah selesai dan kita kembali di eSuite.
        """
        self.submit_email(email)
        self.submit_password(password)
        expect(self.dashboard_greeting).to_be_visible()

    def error_text(self) -> str:
        """
        Teks pesan error yang tampil.

        Dipakai test Negative. Brief mensyaratkan assert pesan SPESIFIK,
        bukan sekadar "masih di halaman login".
        """
        return self.text_of(self.error_message)

    def is_dashboard_visible(self) -> bool:
        """Dipakai test Negative untuk membuktikan dashboard TIDAK tercapai."""
        return self.dashboard_greeting.is_visible()
