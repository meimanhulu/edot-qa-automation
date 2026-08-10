"""
BasePage — perilaku bersama semua page object.

ATURAN PROJECT:
  - Locator HANYA hidup di page class. Tidak ada selector mentah di berkas test.
  - Prioritas locator: data-testid > role + accessible name > atribut stabil
    (name/id/aria-*) > text sebagai PILIHAN TERAKHIR, wajib dijustifikasi
    di komentar tepat di atasnya.
  - Dilarang time.sleep(). Pakai auto-waiting Playwright dan expect().
"""
from playwright.sync_api import Locator, Page, expect


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    # ------------------------------------------------------------------
    # Navigasi
    # ------------------------------------------------------------------

    def goto(self, url: str) -> None:
        """
        Buka URL dan tunggu dokumen selesai dimuat.

        Memakai 'load', BUKAN 'networkidle'. Playwright sendiri menyarankan
        menghindari networkidle untuk aplikasi SPA: eSuite memuat data lewat
        XHR yang berjalan terus, sehingga kondisi "jaringan tenang" mungkin
        tidak pernah tercapai dan penantiannya menggantung sampai timeout.

        Kesiapan data ditunggu oleh page object masing-masing lewat elemen
        penanda yang spesifik — itu lebih tepat daripada menebak lewat
        aktivitas jaringan.
        """
        self.page.goto(url, wait_until="load")

    # ------------------------------------------------------------------
    # Menunggu — tanpa sleep
    # ------------------------------------------------------------------

    def expect_visible(self, locator: Locator, timeout: int | None = None) -> None:
        """Bungkus expect() supaya timeout diatur dari satu tempat."""
        expect(locator).to_be_visible(timeout=timeout) if timeout else expect(locator).to_be_visible()

    def wait_options_populated(self, select_locator: Locator, minimum: int = 2) -> None:
        """
        Tunggu dropdown child terisi setelah parent dipilih.

        INI KUNCI CASCADE Country > Province > City > District > Zone > Postal.

        Kenapa `minimum=2`: dropdown biasanya sudah punya satu opsi placeholder
        ("Pilih Provinsi") sejak awal. Menunggu >= 1 akan langsung lolos padahal
        data belum termuat. Menunggu >= 2 berarti setidaknya satu opsi asli masuk.

        Kenapa bukan sleep: durasi muat bergantung jaringan. sleep(2) kadang
        terlalu cepat (flaky) dan kadang terlalu lambat (suite jadi lama).
        wait_for_function melakukan polling sampai kondisinya benar, lalu lanjut.
        """
        select_locator.wait_for(state="visible")
        self.page.wait_for_function(
            "([el, min]) => el && el.options && el.options.length >= min",
            arg=[select_locator.element_handle(), minimum],
        )

    def select_and_wait_child(
        self, parent: Locator, value: str, child: Locator, minimum: int = 2
    ) -> None:
        """
        Pilih nilai pada parent, lalu tunggu child terisi.

        Dipakai berulang di cascade. Diekstrak jadi satu method supaya pola
        'pilih lalu tunggu' tidak pernah terlewat di salah satu level —
        melewatkannya di satu level saja sudah cukup membuat suite flaky.
        """
        parent.select_option(label=value)
        self.wait_options_populated(child, minimum=minimum)

    # ------------------------------------------------------------------
    # Pembacaan
    # ------------------------------------------------------------------

    def text_of(self, locator: Locator) -> str:
        """
        Kembalikan teks APA ADANYA — tanpa strip.

        Kenapa tidak di-strip: TC-WEB-008 menguji apakah sistem menyimpan
        nilai tanpa spasi berlebih. Kalau page object ikut men-trim, bug itu
        tersembunyi dan test selalu hijau tanpa membuktikan apa pun.
        """
        return locator.inner_text()

    def value_of(self, locator: Locator) -> str:
        """Nilai input form, apa adanya. Alasan sama dengan text_of()."""
        return locator.input_value()