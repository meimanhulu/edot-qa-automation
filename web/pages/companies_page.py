"""CompaniesPage — daftar company, pencarian, aksi Manage dan Delete."""
from playwright.sync_api import Page, expect

from .base_page import BasePage

SEL = {
    "add_company_button": "btn-add-company",
    "search_input": "companies-search",
    "table": "companies-table",
    "row": "company-row",
    "row_name": "company-row-name",
    "manage_button": "company-manage",
    "delete_button": "company-delete",
    "confirm_delete": "confirm-delete",
}

COMPANIES_PATH = "/companies"


class CompaniesPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.add_company_button = page.get_by_test_id(SEL["add_company_button"])
        self.search_input = page.get_by_test_id(SEL["search_input"])
        self.table = page.get_by_test_id(SEL["table"])
        self.rows = page.get_by_test_id(SEL["row"])
        self.confirm_delete = page.get_by_test_id(SEL["confirm_delete"])

    def open(self) -> None:
        self.page.goto(COMPANIES_PATH, wait_until="networkidle")
        expect(self.table).to_be_visible()

    def click_add_company(self) -> None:
        self.add_company_button.click()

    def search(self, keyword: str) -> None:
        """
        Cari, lalu tunggu tabel selesai difilter.

        networkidle dipakai karena pencarian memicu XHR. Tanpa menunggu,
        count_rows_matching() bisa menghitung hasil pencarian SEBELUMNYA.
        """
        self.search_input.fill(keyword)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")

    def count_rows_matching(self, exact_name: str) -> int:
        """
        JUMLAH baris yang namanya sama PERSIS.

        Kenapa menghitung, bukan sekadar cek keberadaan:
          - TC-WEB-011 memastikan tidak ada duplikat  -> harus 1
          - TC-WEB-010 double submit                  -> harus tetap 1
          - TC-WEB-015 delete                         -> harus 0

        Kenapa perbandingan PERSIS, bukan 'contains':
          'PT Sinar' akan cocok dengan 'PT Sinar Rejeki' dan 'PT Sinar Jaya'.
          Untuk TC-WEB-008 (trimming), 'contains' bahkan meloloskan nilai
          yang masih ber-spasi — persis bug yang sedang diuji.
        """
        self.search(exact_name)
        names = self.page.get_by_test_id(SEL["row_name"]).all_inner_texts()
        return sum(1 for n in names if n == exact_name)

    def open_manage(self, exact_name: str) -> None:
        """Buka detail lewat tombol Manage pada baris yang namanya persis."""
        self.search(exact_name)
        row = self.rows.filter(has_text=exact_name).first
        row.get_by_test_id(SEL["manage_button"]).click()
        self.page.wait_for_load_state("networkidle")

    def delete_company(self, exact_name: str) -> None:
        """Hapus lalu konfirmasi dialog."""
        self.search(exact_name)
        row = self.rows.filter(has_text=exact_name).first
        row.get_by_test_id(SEL["delete_button"]).click()
        self.confirm_delete.click()
        self.page.wait_for_load_state("networkidle")
