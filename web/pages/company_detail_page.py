"""
CompanyDetailPage — halaman /companies/manage-companies/<id>/profile

Halaman ini melayani TIGA skenario sekaligus:
    TC-WEB-013  verify detail (Tier 2)
    TC-WEB-014  edit + Save Changes (Tier 2)
    TC-WEB-015  delete (Tier 2)

STRUKTUR SEBENARNYA (hasil inspeksi 09 Agustus 2026):

  idx  field                 tipe              editable
  ---  --------------------  ----------------  --------
   1   Company Name          input             ya
   2   Company ID            input             TIDAK (disabled)
   3   Industry Type         combobox          ya
   4   Company Type          combobox          ya
   5   Number of Employee    combobox          ya
   6   Country               combobox          TIDAK
   7   Province              combobox          TIDAK
   8   City                  combobox          TIDAK
   9   District              combobox          TIDAK
  10   Zone                  combobox          TIDAK
  11   Postal Code           input             TIDAK
  12   Email                 input             ya
  14   Mobile Number         input             ya
  16   Telephone             input             ya

TEMUAN YANG MEMBENTUK IMPLEMENTASI INI:

1. SELURUH CASCADE READONLY.
   Country, Province, City, District, Zone, Postal Code semuanya
   disabled=true. Nilainya terisi tapi tidak bisa diubah dari UI.
   Konsekuensi: TC-WEB-006 (cascade parent reset) TIDAK DAPAT DIUJI —
   tidak di wizard (hanya ada Country) maupun di sini (terkunci).
   Dicatat di README sebagai batasan aplikasi, bukan skenario yang dilewati.

2. COMBOBOX TIDAK PUNYA LABEL TEKS SETELAH TERISI.
   Nilai terpilih menjadi teks tombolnya, sehingga locator berbasis label
   ("Choose Industry Type") tidak lagi cocok. Karena itu field diakses
   lewat URUTAN (nth), bukan lewat teks.

3. DUA JENIS ID.
   URL memuat mongo id (6864b55c92cac0a28773aabe) sedangkan Company ID
   yang tampil di form adalah 5102559. Keduanya dibutuhkan: mongo id untuk
   navigasi langsung, company id untuk skenario mobile.
"""
from playwright.sync_api import Locator, Page, expect

from .base_page import BasePage

# Urutan elemen pada form, hasil inspeksi. Dipetakan sebagai konstanta agar
# get_all_fields() bisa mengiterasinya alih-alih menulis belasan baris serupa.
INPUT_INDEX = {
    "name": 1,
    "company_id": 2,
    "postal_code": 11,
    "email": 12,
    "mobile_number": 14,
    "telephone": 16,
}

COMBOBOX_INDEX = {
    "industry_type": 3,
    "company_type": 4,
    "number_of_employee": 5,
    "country": 6,
    "province": 7,
    "city": 8,
    "district": 9,
    "zone": 10,
}

# Field yang bisa diubah — dipakai TC-WEB-014.
EDITABLE_INPUTS = ["name", "email", "mobile_number", "telephone"]
EDITABLE_COMBOBOXES = ["industry_type", "company_type", "number_of_employee"]

# Field readonly — diverifikasi nilainya, tidak pernah diubah.
READONLY_FIELDS = [
    "company_id", "country", "province", "city", "district", "zone", "postal_code",
]


class CompanyDetailPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

        self.save_button = page.get_by_role("button", name="Save Changes")
        self.delete_button = page.get_by_role("button", name="Delete", exact=True)
        self.back_button = page.get_by_role("button", name="Back to Company List")
        self.heading = page.get_by_text("Company Details", exact=True)

    # ------------------------------------------------------------------
    # Akses elemen
    # ------------------------------------------------------------------

    def _input(self, key: str) -> Locator:
        """
        Input berdasarkan urutannya di form.

        Kenapa lewat urutan, bukan placeholder: sebagian input punya
        placeholder yang sama-sama generik, dan Company ID justru tidak
        punya nilai pembeda selain posisinya. Urutan diverifikasi lewat
        inspeksi dan dicatat di INPUT_INDEX.
        """
        return self.page.locator("input").nth(INPUT_INDEX[key])

    def _combobox(self, key: str) -> Locator:
        """
        Combobox berdasarkan urutannya, DIHITUNG DARI SELURUH input+combobox.

        Indeks pada COMBOBOX_INDEX mengikuti urutan gabungan hasil inspeksi,
        sehingga locator-nya menyaring elemen gabungan, bukan combobox saja.
        """
        return self.page.locator("input, button[role=combobox]").nth(COMBOBOX_INDEX[key])

    def is_loaded(self) -> bool:
        return self.heading.is_visible()

    def wait_loaded(self) -> None:
        expect(self.heading).to_be_visible()

    # ------------------------------------------------------------------
    # Pembacaan — untuk TC-WEB-013 (Tier 2)
    # ------------------------------------------------------------------

    def get_all_fields(self) -> dict[str, str]:
        """
        Seluruh field yang tampil, sebagai dict.

        Nilai dikembalikan APA ADANYA — tidak di-strip. TC-WEB-008 menguji
        apakah sistem menyimpan tanpa spasi berlebih; kalau page object ikut
        men-trim, bug itu tersembunyi dan test selalu hijau tanpa
        membuktikan apa pun.

        Page object melaporkan KEADAAN; test yang memutuskan lulus/gagal.
        """
        values = {}
        for key in INPUT_INDEX:
            values[key] = self._input(key).input_value()
        for key in COMBOBOX_INDEX:
            values[key] = self._combobox(key).inner_text()
        return values

    def get_field(self, key: str) -> str:
        """Satu field saja. Berguna saat test hanya peduli pada satu nilai."""
        if key in INPUT_INDEX:
            return self._input(key).input_value()
        return self._combobox(key).inner_text()

    def is_field_editable(self, key: str) -> bool:
        """
        Apakah field bisa diubah.

        Dipakai untuk membuktikan cascade memang readonly — bukan asumsi,
        melainkan hasil pembacaan langsung dari DOM.
        """
        locator = self._input(key) if key in INPUT_INDEX else self._combobox(key)
        return locator.is_enabled()

    def company_id(self) -> str:
        """
        Company ID yang tampil di form (mis. 5102559).

        Berbeda dari mongo id di URL. ID inilah yang dipakai skenario
        mobile untuk login ke eWork SFA.
        """
        return self._input("company_id").input_value()

    def mongo_id_from_url(self) -> str:
        """
        ID pada URL: /companies/manage-companies/<mongo_id>/profile

        Dipakai TC-WEB-015 untuk menguji apakah halaman detail masih bisa
        diakses langsung setelah company dihapus.
        """
        parts = self.page.url.split("/manage-companies/")
        return parts[1].split("/")[0] if len(parts) > 1 else ""

    # ------------------------------------------------------------------
    # Perubahan — untuk TC-WEB-014 (Tier 2)
    # ------------------------------------------------------------------

    def set_input(self, key: str, value: str) -> None:
        """Ubah nilai satu input. Hanya untuk field yang editable."""
        self._input(key).fill(value)

    def set_combobox(self, key: str, value: str) -> None:
        """
        Ubah nilai combobox — klik trigger, tunggu listbox, klik opsi.

        Pola yang sama dipakai di wizard. select_option() bawaan Playwright
        tidak bisa dipakai karena ini Radix UI, bukan <select> asli.
        """
        self._combobox(key).click()

        listbox = self.page.get_by_role("listbox")
        expect(listbox).to_be_visible()
        listbox.get_by_role("option", name=value, exact=True).click()
        expect(listbox).not_to_be_visible()

    def save(self) -> None:
        """
        Simpan perubahan.

        Menunggu jaringan tenang setelah klik: pembacaan berikutnya harus
        terjadi setelah respons server masuk, bukan saat form masih
        menampilkan nilai lama.
        """
        self.save_button.click()
        self.page.wait_for_load_state("networkidle")

    # ------------------------------------------------------------------
    # Penghapusan — untuk TC-WEB-015 (Tier 2)
    # ------------------------------------------------------------------

    def delete(self) -> None:
        """
        Hapus company.

        Dialog konfirmasi belum terverifikasi saat inspeksi. Implementasi ini
        mengklik Delete lalu mencari tombol konfirmasi bila muncul; bila tidak
        ada, penghapusan dianggap langsung. Test tetap membuktikan hasilnya
        lewat pengecekan record, bukan lewat asumsi soal dialog.
        """
        self.delete_button.click()

        confirm = self.page.get_by_role("button", name="Delete", exact=True).last
        try:
            confirm.click(timeout=5000)
        except Exception:
            # Tidak ada dialog konfirmasi — klik pertama sudah cukup.
            pass

        self.page.wait_for_load_state("networkidle")