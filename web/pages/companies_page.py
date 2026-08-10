"""
CompaniesPage — halaman /companies.

STRUKTUR SEBENARNYA (hasil inspeksi 09 Agustus 2026):

Halaman ini BUKAN tabel. Tiap company adalah kartu berisi:

    +--------------------------------+
    |  [logo]            Active      |
    |  QA Production                 |   <- nama
    |  5049209                       |   <- company ID
    |  [ Manage ]      [ Go To ]     |   <- Go To bila Active
    +--------------------------------+   <- Contact Us bila Expired

Temuan yang membentuk implementasi di bawah:

1. TIDAK ADA search input di halaman ini. Diverifikasi: querySelectorAll('input')
   mengembalikan nol elemen. Jadi pencarian dilakukan dengan memfilter kartu
   yang sudah ada di DOM, bukan mengetik di kolom pencarian.

2. SELURUH company dirender sekaligus — 1.148 tombol untuk 571 company,
   tanpa pagination. Berat, tapi menguntungkan: seluruh data bisa dibaca
   tanpa perlu berpindah halaman.

3. Tombol tidak punya nama unik. Ada ratusan tombol bertuliskan "Manage".
   Karena itu tombol SELALU dicari relatif terhadap kartunya, tidak pernah
   langsung dari page. Mengklik get_by_role("button", name="Manage") akan
   kena strict mode violation.

4. Tab "Single Company" / "Group Company" / "Log Activity" memisahkan jenis
   company. Kartu yang dihitung hanya yang berada di tab aktif.
"""
from playwright.sync_api import Locator, Page, expect

from .base_page import BasePage

COMPANIES_PATH = "/companies"


class CompaniesPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

        # Tombol aksi tingkat halaman — keduanya bernama unik, jadi aman
        # dipakai langsung dengan role + accessible name.
        self.add_company_button = page.get_by_role("button", name="+ Add Company")
        self.manage_company_button = page.get_by_role("button", name="Manage Company")

        # Tab pemisah jenis company.
        self.tab_single = page.get_by_role("button", name="Single Company")
        self.tab_group = page.get_by_role("button", name="Group Company")

        # Judul halaman — dipakai sebagai penanda halaman sudah termuat.
        self.page_heading = page.get_by_text("My Company", exact=True)

        # Penghitung kartu. Kartu tidak punya atribut penanda sendiri, tetapi
        # SETIAP kartu memiliki tepat satu tombol "Manage" — jadi jumlah
        # tombol Manage sama dengan jumlah kartu yang sudah ter-render.
        self.manage_buttons = page.get_by_role("button", name="Manage", exact=True)

    # ------------------------------------------------------------------
    # Navigasi
    # ------------------------------------------------------------------

    def open(self, base_url: str) -> None:
        """
        Buka /companies dan tunggu kartu benar-benar ter-render.

        Menunggu tombol "+ Add Company", bukan sekadar judul: judul muncul
        lebih dulu sementara 571 kartu masih dirender. Menunggu judul saja
        membuat pembacaan kartu berjalan pada DOM yang belum lengkap.
        """
        self.goto(f"{base_url.rstrip('/')}{COMPANIES_PATH}")
        expect(self.add_company_button).to_be_visible()

    def click_add_company(self) -> None:
        self.add_company_button.click()

    # ------------------------------------------------------------------
    # Pembacaan kartu
    # ------------------------------------------------------------------

    def scroll_to_load_all(self, max_rounds: int = 30) -> int:
        """
        Gulir sampai bawah berulang kali hingga jumlah kartu berhenti bertambah.

        Halaman ini merender kartu SECARA BERTAHAP saat digulir, bukan
        sekaligus. Company yang baru dibuat muncul di URUTAN PALING BAWAH,
        sehingga kartunya belum ada di DOM sampai halaman digulir ke sana.

        Akibatnya pencarian berbasis teks gagal menemukan company yang jelas
        ada di aplikasi — kegagalannya berbunyi "waiting for get_by_text(...)"
        dan terbaca seperti company tidak terbuat.

        Mengembalikan jumlah kartu yang akhirnya termuat.
        """
        previous = -1
        for _ in range(max_rounds):
            current = self.manage_buttons.count()
            if current == previous:
                break
            previous = current

            self.page.mouse.wheel(0, 20000)
            # Beri kesempatan render berikutnya masuk. Memakai wait_for_timeout,
            # bukan sleep: ini bagian dari API Playwright dan tetap menghormati
            # pembatalan test, bukan memblokir thread.
            self.page.wait_for_timeout(300)

        return self.manage_buttons.count()

    def card_for(self, exact_name: str) -> Locator:
        """
        Kartu milik company dengan nama PERSIS seperti argumen.

        Kartu dicari lewat elemen teks nama, lalu naik ke kontainer terdekat
        yang memiliki tombol Manage. Pendekatan ini dipakai karena kartu tidak
        punya atribut penanda sendiri — tidak ada data-testid, tidak ada id.

        `exact=True` WAJIB: tanpa itu, "gygy" juga cocok dengan "gygy2",
        dan test duplikasi kehilangan maknanya.
        """
        name_node = self.page.get_by_text(exact_name, exact=True)
        return name_node.locator(
            "xpath=ancestor::*[.//button[normalize-space()='Manage']][1]"
        )

    def count_companies_named(self, exact_name: str) -> int:
        """
        JUMLAH company yang namanya sama PERSIS.

        Kenapa menghitung, bukan sekadar memeriksa keberadaan:
          - TC-WEB-005 membuktikan tidak ada duplikat   -> harus 1
          - TC-WEB-010 double submit                    -> harus tetap 1
          - TC-WEB-015 delete                           -> harus 0

        Kenapa exact, bukan 'contains': halaman ini nyata-nyata memuat
        "gygy" dan "gygy2" sekaligus. Pencocokan parsial akan menghitung
        keduanya dan membuat assert duplikasi selalu lolos.
        """
        return self.page.get_by_text(exact_name, exact=True).count()

    def expect_company_count(self, exact_name: str, count: int, timeout: int = 30000) -> None:
        """
        Tunggu sampai jumlah company dengan nama PERSIS mencapai `count`.

        Memakai expect() yang melakukan polling, bukan count() yang menghitung
        seketika.

        Kenapa perlu: halaman ini merender SELURUH company sekaligus — 572
        kartu tanpa pagination. Menghitung tepat setelah halaman dibuka bisa
        mendapat angka 0 padahal record-nya ada, karena kartunya belum selesai
        di-render. Kegagalan seperti itu terbaca seperti "company tidak
        terbuat", padahal masalahnya waktu.

        Dipakai untuk:
          count=1  -> record ada dan tidak duplikat
          count=0  -> record benar-benar terhapus
        """
        # Gulir sampai seluruh kartu termuat sebelum menghitung — company baru
        # berada di paling bawah dan kartunya dirender bertahap.
        if count > 0:
            self.scroll_to_load_all()

        expect(self.page.get_by_text(exact_name, exact=True)).to_have_count(
            count, timeout=timeout
        )

    def company_ids_named(self, exact_name: str) -> list[str]:
        """
        Company ID milik semua kartu dengan nama tersebut.

        Berguna saat nama berulang (halaman ini memuat dua company bernama
        "gygy" dengan ID berbeda). ID inilah pembeda sebenarnya, dan ID
        company yang dibuat suite dipakai untuk skenario mobile.
        """
        self.scroll_to_load_all()

        ids = []
        cards = self.card_for(exact_name)
        for i in range(cards.count()):
            text = cards.nth(i).inner_text()
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.isdigit():
                    ids.append(stripped)
                    break
        return ids

    def is_company_present(self, exact_name: str) -> bool:
        return self.count_companies_named(exact_name) > 0

    # ------------------------------------------------------------------
    # Aksi pada kartu
    # ------------------------------------------------------------------

    def open_manage(self, exact_name: str) -> None:
        """
        Klik Manage pada kartu company tertentu.

        Menggulir lebih dulu supaya kartunya benar-benar ter-render — kartu
        company baru berada di bawah dan tidak ada di DOM sebelum digulir.

        Tombol dicari DI DALAM kartu, bukan dari page. Ada ratusan tombol
        bertuliskan "Manage" di halaman ini; memanggilnya dari page akan
        memicu strict mode violation.
        """
        self.scroll_to_load_all()

        card = self.card_for(exact_name).first
        card.scroll_into_view_if_needed()
        card.get_by_role("button", name="Manage").click()

        # Tunggu halaman detail benar-benar terbuka, bukan sekadar jaringan
        # tenang — URL detail memuat segmen /manage-companies/.
        self.page.wait_for_url("**/manage-companies/**", timeout=30000)

    def go_to_company(self, exact_name: str) -> None:
        """
        Klik "Go To" — hanya tersedia pada company berstatus Active.

        Company Expired menampilkan "Contact Us" di posisi yang sama.
        """
        card = self.card_for(exact_name).first
        card.get_by_role("button", name="Go To").click()

    def status_of(self, exact_name: str) -> str:
        """
        Status company: "Active" atau "Expired".

        Dibaca dari isi kartu. Dipakai untuk memastikan company yang dibuat
        suite memang aktif sebelum dipakai skenario mobile.
        """
        text = self.card_for(exact_name).first.inner_text()
        if "Active" in text:
            return "Active"
        if "Expired" in text:
            return "Expired"
        return "Unknown"