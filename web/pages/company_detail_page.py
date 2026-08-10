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
import re

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

        # True bila halaman perlu dimuat ulang sebelum datanya muncul.
        # Lihat wait_loaded() — ini penanda cacat produk, bukan detail teknis.
        self.needed_reload = False

        self.save_button = page.get_by_role("button", name="Save Changes")
        self.delete_button = page.get_by_role("button", name="Delete", exact=True)
        self.back_button = page.get_by_role("button", name="Back to Company List")
        self.heading = page.get_by_text("Company Details", exact=True)

    # ------------------------------------------------------------------
    # Akses elemen
    # ------------------------------------------------------------------

    # Locator gabungan input + combobox. INDEKS PADA INPUT_INDEX DAN
    # COMBOBOX_INDEX MENGACU KE DAFTAR GABUNGAN INI, bukan ke masing-masing
    # jenis elemen secara terpisah.
    #
    # Inspeksi DOM dilakukan dengan querySelectorAll('input, button[role=combobox]'),
    # sehingga Postal Code tercatat di indeks 11. Bila dihitung dari <input>
    # saja, jumlahnya hanya 7 dan indeks 11 tidak pernah ada — kegagalannya
    # berupa timeout "waiting for input.nth(11)" yang menyesatkan.
    ALL_FIELDS_SELECTOR = "input, button[role=combobox]"

    def _input(self, key: str) -> Locator:
        """
        Input berdasarkan urutannya di daftar GABUNGAN input + combobox.

        Kenapa lewat urutan, bukan placeholder: sebagian input punya
        placeholder generik, dan Company ID tidak punya pembeda selain
        posisinya. Urutan diverifikasi lewat inspeksi dan dicatat di
        INPUT_INDEX.

        Kenapa memakai selector gabungan: indeks pada INPUT_INDEX berasal
        dari inspeksi yang mencampur input dan combobox. Memakai locator
        "input" saja membuat indeksnya bergeser.
        """
        return self.page.locator(self.ALL_FIELDS_SELECTOR).nth(INPUT_INDEX[key])

    def _combobox(self, key: str) -> Locator:
        """
        Combobox berdasarkan urutannya, DIHITUNG DARI SELURUH input+combobox.

        Indeks pada COMBOBOX_INDEX mengikuti urutan gabungan hasil inspeksi,
        sehingga locator-nya menyaring elemen gabungan, bukan combobox saja.
        """
        return self.page.locator(self.ALL_FIELDS_SELECTOR).nth(COMBOBOX_INDEX[key])

    def is_loaded(self) -> bool:
        """Apakah halaman detail sedang tampil (belum tentu datanya sudah masuk)."""
        return self.heading.is_visible()

    def wait_loaded(self, timeout: int = 30000) -> None:
        """
        Tunggu halaman detail tampil DAN datanya benar-benar termuat.

        Menunggu Company ID terisi angka, bukan sekadar judul "Company Details"
        muncul.

        Kenapa: halaman ini memuat data secara asinkron. Judul tampil lebih
        dulu sementara seluruh field masih kosong — Company Name kosong,
        dropdown masih "Choose ...". Membaca field pada saat itu menghasilkan
        nilai kosong, dan verifikasi Tier 2 gagal karena alasan yang salah:
        bukan karena aplikasi menyimpan nilai keliru, melainkan karena kita
        membaca terlalu cepat.

        Company ID dipakai sebagai penanda karena ia dihasilkan sistem dan
        selalu terisi angka begitu data masuk.
        """
        expect(self.heading).to_be_visible(timeout=timeout)

        # Dicatat supaya pemanggil tahu apakah reload dibutuhkan. Reload yang
        # senyap akan menyembunyikan cacat produk di balik test yang hijau.
        self.needed_reload = False

        company_id = self._input("company_id")

        # Coba sekali; bila data tidak masuk, MUAT ULANG halaman lalu coba lagi.
        #
        # Halaman ini kadang terbuka dengan seluruh field kosong meski URL-nya
        # benar (mengandung ?cid=). Reload menyelesaikannya. Pengulangan
        # dibatasi sekali supaya kegagalan sungguhan tetap muncul cepat,
        # bukan tersamar oleh percobaan berulang.
        try:
            expect(company_id).to_have_value(re.compile(r"^\d+$"), timeout=timeout // 3)
            return
        except AssertionError:
            pass

        # Pembukaan pertama tidak memuat data — ini perilaku yang layak
        # dilaporkan, bukan sekadar diakali. Ditandai agar test bisa
        # melampirkannya ke Allure.
        self.needed_reload = True

        self.page.reload(wait_until="load")
        expect(self.heading).to_be_visible(timeout=timeout)

        try:
            expect(self._input("company_id")).to_have_value(
                re.compile(r"^\d+$"), timeout=timeout // 3
            )
        except AssertionError:
            # Gagal CEPAT dengan diagnosis, bukan timeout di locator berikutnya.
            #
            # Tanpa ini, kegagalan muncul sebagai "waiting for input.nth(11)"
            # saat membaca field — pesan yang menunjuk cacat locator, padahal
            # penyebabnya halaman tidak memuat data sama sekali. Triage akan
            # salah memvonisnya.
            raise AssertionError(
                f"Halaman detail tidak memuat data setelah dibuka DAN dimuat ulang.\n"
                f"  URL           : {self.page.url}\n"
                f"  jumlah field  : {self.page.locator(self.ALL_FIELDS_SELECTOR).count()} "
                f"(diharapkan minimal {max(list(INPUT_INDEX.values()) + list(COMBOBOX_INDEX.values())) + 1})\n"
                f"  Company ID    : {company_id.input_value()!r} (diharapkan angka)\n\n"
                "Verifikasi manual: buka company ini di browser lewat Companies > Manage. "
                "Bila field-nya juga kosong secara manual, ini BUG PRODUK — halaman "
                "detail tidak memuat data untuk company yang baru dibuat."
            ) from None

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
        # Pastikan data benar-benar termuat sebelum dibaca. Tanpa ini,
        # pembacaan pada halaman kosong menghasilkan timeout di indeks
        # tertinggi — pesan yang menyesatkan.
        self.wait_loaded()

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

        # Tunggu tombol Save kembali stabil setelah request selesai, bukan
        # menunggu jaringan tenang — eSuite punya XHR yang berjalan terus.
        expect(self.save_button).to_be_enabled(timeout=30000)

    # ------------------------------------------------------------------
    # Penghapusan — untuk TC-WEB-015 (Tier 2)
    # ------------------------------------------------------------------

    def delete(self) -> None:
        """
        Hapus company lewat dialog konfirmasi.

        STRUKTUR DIALOG (hasil inspeksi):

            Confirmation Delete                              [X]
            Are you agree to delete the company?
            Deleting the company data will affect to other related data...
            [ ] I understand & agree to delete
                                      [Cancel]  [Confirm]

        Dua hal yang berbeda dari dugaan awal:
          1. tombol konfirmasinya bernama "Confirm", BUKAN "Delete"
          2. ada CHECKBOX persetujuan yang wajib dicentang lebih dulu —
             Confirm tetap terkunci sebelum itu

        Pola yang sama dengan Step 3 wizard: aksi berisiko dikunci di balik
        checkbox persetujuan.
        """
        self.delete_button.click()

        # Dialog dirender di portal, jadi dicari dari page.
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible()

        # Checkbox persetujuan wajib dicentang sebelum Confirm terbuka.
        dialog.get_by_role("checkbox").check()

        confirm = dialog.get_by_role("button", name="Confirm")
        expect(confirm).to_be_enabled()
        confirm.click()

        # Setelah dihapus, aplikasi mengarahkan kembali ke daftar companies.
        self.page.wait_for_url("**/companies", timeout=30000)