"""
RegisterCompanyWizard — wizard 3 langkah di /companies/registration-companies.

STRUKTUR SEBENARNYA (hasil inspeksi 09 Agustus 2026):

ALUR LENGKAP:
    Step 1/3  Register Company    4 input + 4 combobox        -> Next
    Step 2/3  Register Legal      Legal Document (opsional)   -> Next
    Step 3/3  Create Your Branch  Branch Name (auto-isi),
                                  Street Address, Country,
                                  checkbox persetujuan        -> Register

Step 1 berisi:

    Company Name*     input[placeholder="Input Company Name"]
    Email*            input[placeholder="Input Email"]
    Phone*            [flag +62] input[placeholder="Input Phone"]
    Industry Type*    button[role=combobox] "Choose Industry Type"
    Company Type*     button[role=combobox] "Choose Company Type"
    Language*         button[role=combobox] "Choose Language"
    Street Address*   input[placeholder="Input Address"]
    Country*          button[role=combobox] "Choose Country"
                                                              [Next]

TIGA TEMUAN YANG MEMBENTUK IMPLEMENTASI INI:

1. CASCADE MUNCUL BERTAHAP (progressive disclosure).
   Sebelum Country dipilih, form hanya menampilkan 8 field. Setelah Country
   dipilih, lima field BARU muncul: Province, City, District, Sub District,
   dan Postal Code.

   Dua perbedaan dari brief:
     - brief menyebut level keempat "Zone"; aplikasi memakai "Sub District"
     - brief menyebut Postal Code sebagai pilihan; aplikasi mengisinya
       OTOMATIS setelah Sub District dipilih, dan field-nya read-only

2. SEMUA DROPDOWN ADALAH button[role=combobox], BUKAN <select>.
   Diverifikasi: querySelectorAll('select') mengembalikan nol elemen.
   Konsekuensinya select_option() TIDAK BISA dipakai sama sekali —
   dropdown harus diklik untuk membuka, lalu opsinya diklik.

3. FIELD TIDAK PUNYA ATRIBUT name.
   Yang tersedia hanya placeholder, sehingga get_by_placeholder() menjadi
   pilihan terbaik yang ada. Ini prioritas ke-3 brief (atribut stabil);
   data-testid tidak tersedia di seluruh aplikasi.

4. COMBOBOX TIDAK PUNYA ACCESSIBLE NAME SAMA SEKALI.
   Diverifikasi lewat Console: aria-label, aria-labelledby, dan title
   kosong pada kelima combobox. Akibatnya get_by_role(..., name=...)
   selalu gagal — combobox terpaksa diakses lewat URUTAN (nth).
   Ini sekaligus temuan aksesibilitas: pengguna screen reader tidak
   mendapat informasi apa pun tentang fungsi tiap dropdown.
"""
from playwright.sync_api import Locator, Page, expect

from .base_page import BasePage

WIZARD_PATH = "/companies/registration-companies"

# Placeholder dipakai sebagai selector karena field tidak punya name maupun id.
PLACEHOLDERS = {
    "name": "Input Company Name",
    "email": "Input Email",
    "phone": "Input Phone",
    "street_address": "Input Address",
}

# Teks awal tiap combobox — dipakai untuk menemukannya sebelum dipilih.
# Setelah opsi dipilih, teksnya berganti menjadi nilai terpilih, sehingga
# locator berbasis teks awal tidak lagi cocok. Karena itu combobox diakses
# lewat urutan (nth), bukan lewat teks, setelah pemilihan pertama.
COMBOBOX_LABELS = {
    "industry_type": "Choose Industry Type",
    "company_type": "Choose Company Type",
    "language": "Choose Language",
    "country": "Choose Country",
}

# Urutan combobox di Step 1, hasil inspeksi DOM.
#
# Dipakai karena SELURUH combobox tidak memiliki accessible name —
# diverifikasi lewat Console: aria-label, aria-labelledby, dan title
# semuanya kosong pada kelima combobox. Teks yang tampil hanya ada di
# innerText, yang TIDAK dihitung Playwright sebagai accessible name,
# sehingga get_by_role(..., name=...) selalu gagal dengan timeout.
#
# Indeks 0 adalah kode negara telepon (+62), bukan bagian form utama.
COMBOBOX_ORDER = {
    "industry_type": 1,
    "company_type": 2,
    "language": 3,
    "country": 4,
    # Lima berikut baru MUNCUL setelah Country dipilih (progressive disclosure).
    # Sebelum itu, indeks 5+ tidak ada di DOM.
    "province": 5,
    "city": 6,
    "district": 7,
    "sub_district": 8,
}

# Urutan cascade, dipakai select_cascade() dan snapshot_cascade().
# Postal Code TIDAK termasuk: ia input read-only yang terisi otomatis.
CASCADE_ORDER = ["province", "city", "district", "sub_district"]


class RegisterCompanyWizard(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

        self.f = {
            key: page.get_by_placeholder(ph) for key, ph in PLACEHOLDERS.items()
        }

        # Postal Code adalah INPUT read-only yang terisi otomatis setelah
        # Sub District dipilih, bukan dropdown yang bisa dipilih.
        self.postal_code_input = page.get_by_placeholder("Choose Postal Code")

        self.next_button = page.get_by_role("button", name="Next")
        self.back_button = page.get_by_role("button", name="Back", exact=True)
        self.back_to_companies = page.get_by_role("button", name="Back to Companies")
        self.heading = page.get_by_text("Register Company", exact=True)

        # --- Step 3: Create Your Branch ---
        self.fill_from_company_records = page.get_by_role(
            "button", name="Fill in with the same data from the Company records"
        )
        self.register_button = page.get_by_role("button", name="Register", exact=True)
        # Step 3 hanya punya SATU combobox (Country), jadi indeksnya 0.
        self.branch_country = page.locator("[role=combobox]").first
        # Checkbox persetujuan tidak punya label yang bisa dipakai get_by_label,
        # jadi diakses lewat role — hanya ada satu checkbox di step ini.
        self.agree_checkbox = page.get_by_role("checkbox")

    # ------------------------------------------------------------------
    # Combobox — pola yang dipakai seluruh dropdown di aplikasi ini
    # ------------------------------------------------------------------

    def _combobox(self, key: str) -> Locator:
        """
        Combobox berdasarkan URUTANNYA di form.

        Pendekatan berbasis nama TIDAK BISA dipakai di aplikasi ini:
        seluruh combobox tidak punya accessible name. Diverifikasi lewat
        inspeksi DOM — aria-label, aria-labelledby, dan title kosong pada
        kelimanya, dan teks yang tampil hanya ada di innerText yang tidak
        dihitung sebagai accessible name.

        Elemennya juga memasang role="combobox" secara eksplisit meski
        tag-nya <button>, sehingga get_by_role("button", ...) pun tidak
        pernah cocok. Kedua jalan berbasis role+name buntu.

        Konsekuensi yang diterima sadar: locator ini rapuh terhadap
        perubahan URUTAN field. Alternatifnya hanya text selector, yang
        justru lebih rapuh — teksnya berubah begitu opsi dipilih.
        """
        return self.page.locator("[role=combobox]").nth(COMBOBOX_ORDER[key])

    def select_option(self, key: str, value: str) -> None:
        """
        Pilih nilai pada combobox Radix.

        Alurnya tiga langkah, dan ketiganya perlu:
          1. klik tombol untuk membuka listbox
          2. TUNGGU listbox benar-benar muncul — opsi dimuat setelah klik,
             bukan sebelumnya
          3. klik opsi dengan nama persis

        Kenapa bukan select_option() bawaan Playwright: method itu hanya
        bekerja pada elemen <select> asli. Aplikasi ini memakai Radix UI,
        di mana dropdown adalah <button> plus listbox yang dirender terpisah.
        """
        trigger = self._combobox(key)
        trigger.click()

        # Listbox Radix dirender di luar tombolnya (portal), jadi dicari
        # dari page, bukan dari trigger.
        listbox = self.page.get_by_role("listbox")
        expect(listbox).to_be_visible()

        listbox.get_by_role("option", name=value, exact=True).click()

        # Tunggu listbox tertutup sebelum lanjut ke field berikutnya.
        # Tanpa ini, klik berikutnya bisa mengenai overlay yang masih terbuka.
        expect(listbox).not_to_be_visible()

    def select_first_option(self, key: str) -> str:
        """
        Pilih opsi PERTAMA pada combobox, kembalikan teks yang terpilih.

        Kenapa opsi pertama, bukan nilai dari data test:
          Opsi cascade bergantung pada parent yang dipilih — Sub District
          untuk "SIPATANA" berbeda dari untuk "KOTA TENGAH". Validitas
          kombinasi hanya bisa diketahui saat runtime, sehingga menentukan
          nilainya di data test selalu berisiko memilih kombinasi tak sah.
          Kegagalannya pun tidak jelas: berupa timeout, bukan pesan error.

          Mengambil opsi pertama menjamin nilainya SELALU sah, karena
          aplikasi sendiri yang menyediakannya untuk parent tersebut.

        Nilai terpilih DIKEMBALIKAN supaya test bisa memakainya sebagai
        expected value saat verifikasi Tier 2 — kita membandingkan terhadap
        apa yang benar-benar dipilih, bukan terhadap tebakan.
        """
        trigger = self._combobox(key)
        trigger.click()

        listbox = self.page.get_by_role("listbox")
        expect(listbox).to_be_visible()

        options = listbox.locator("[role=option]")
        expect(options.first).to_be_visible()

        chosen = options.first.inner_text().strip()
        options.first.click()

        expect(listbox).not_to_be_visible()
        return chosen

    def selected_value(self, index: int) -> str:
        """
        Teks combobox pada urutan tertentu.

        Dipakai setelah pemilihan, saat locator berbasis label sudah tidak
        cocok lagi. Urutan combobox di Step 1:
            0 = country code telepon (+62)
            1 = Industry Type
            2 = Company Type
            3 = Language
            4 = Country
        """
        return self.page.locator("[role=combobox]").nth(index).inner_text().strip()

    # ------------------------------------------------------------------
    # Step 1
    # ------------------------------------------------------------------

    def open(self, base_url: str) -> None:
        self.goto(f"{base_url.rstrip('/')}{WIZARD_PATH}")
        expect(self.heading).to_be_visible()

    def fill_text_fields(self, data: dict) -> None:
        """Isi keempat field teks Step 1."""
        for key, locator in self.f.items():
            locator.fill(str(data[key]))

    def fill_dropdowns(self, data: dict) -> dict[str, str]:
        """
        Isi seluruh combobox dengan opsi PERTAMA masing-masing.

        Mengembalikan dict nilai yang benar-benar terpilih — dipakai test
        sebagai expected value saat verifikasi Tier 2.

        Country dipilih setelah tiga lainnya karena memilihnya MEMUNCULKAN
        lima field baru (Province s/d Postal Code). Mengisinya lebih awal
        akan menggeser indeks combobox lain di tengah pengisian.
        """
        chosen = {}
        for key in ("industry_type", "company_type", "language", "country"):
            chosen[key] = self.select_first_option(key)

        chosen.update(self.select_cascade())
        return chosen

    def select_cascade(self) -> dict[str, str]:
        """
        Isi cascade Province > City > District > Sub District dengan opsi
        pertama tiap level. Mengembalikan nilai yang terpilih.

        Tiap child baru terisi setelah parent dipilih, lewat XHR. Karena itu
        setiap level menunggu comboboxnya benar-benar muncul sebelum diklik —
        bukan langsung memilih keempatnya berurutan.

        Postal Code TIDAK dipilih: aplikasi mengisinya otomatis setelah Sub
        District dipilih. Nilainya ikut dikembalikan hasil pembacaan form.
        """
        chosen = {}
        for key in CASCADE_ORDER:
            combobox = self._combobox(key)
            expect(combobox).to_be_visible()
            chosen[key] = self.select_first_option(key)

        # Postal Code terisi otomatis — tunggu sampai benar-benar ada isinya
        # sebelum menganggap Step 1 selesai.
        expect(self.postal_code_input).not_to_have_value("")
        chosen["postal_code"] = self.postal_code()
        return chosen

    def postal_code(self) -> str:
        """
        Kode pos yang diisi OTOMATIS oleh aplikasi.

        Dibaca, bukan ditentukan — nilainya berasal dari Sub District yang
        dipilih. Dipakai sebagai expected value saat verifikasi detail.
        """
        return self.postal_code_input.input_value()

    def snapshot_cascade(self) -> dict[str, str]:
        """
        Nilai keempat combobox cascade plus Postal Code, saat ini.

        Dipakai TC-WEB-006: ambil snapshot sebelum dan sesudah mengubah
        Province, lalu bandingkan untuk membuktikan child ter-reset.
        """
        values = {
            key: self._combobox(key).inner_text().strip() for key in CASCADE_ORDER
        }
        values["postal_code"] = self.postal_code()
        return values

    def change_province_to_second_option(self) -> str:
        """
        Ganti Province ke opsi KEDUA, kembalikan nilai barunya.

        Opsi kedua dipakai supaya nilainya dijamin berbeda dari yang sedang
        terpilih (opsi pertama) — tanpa perlu tahu nama provinsi apa pun.

        Sengaja TIDAK menunggu child terisi ulang: perilaku child setelah
        parent berubah itulah yang sedang diuji TC-WEB-006. Menunggu di sini
        justru akan menyembunyikannya.
        """
        self._combobox("province").click()

        listbox = self.page.get_by_role("listbox")
        expect(listbox).to_be_visible()

        second = listbox.locator("[role=option]").nth(1)
        expect(second).to_be_visible()

        chosen = second.inner_text().strip()
        second.click()
        expect(listbox).not_to_be_visible()
        return chosen

    def fill_step_one(self, data: dict) -> dict[str, str]:
        """
        Isi seluruh Step 1: field teks dari data, dropdown dari opsi pertama.

        Mengembalikan dict nilai dropdown yang terpilih. Test menggabungkannya
        dengan data teks untuk membentuk expected value Tier 2 — sehingga
        perbandingan dilakukan terhadap apa yang BENAR-BENAR masuk ke form,
        bukan terhadap nilai yang diasumsikan.
        """
        self.fill_text_fields(data)
        return self.fill_dropdowns(data)

    def is_next_enabled(self) -> bool:
        """
        Status enabled tombol Next.

        Aplikasi men-disable Next selama Step 1 belum valid — sama seperti
        tombol Log In di Account Center. Dipakai TC-WEB-006 dan TC-WEB-007.
        """
        return self.next_button.is_enabled()

    def clear_field(self, key: str) -> None:
        """Kosongkan satu field teks. Dipakai TC-WEB-007."""
        self.f[key].fill("")

    def click_next(self) -> None:
        self.next_button.click()
        self.page.wait_for_load_state("networkidle")

    def current_step(self) -> str:
        """
        Penunjuk langkah, mis. "1/3".

        Dipakai untuk memastikan wizard benar-benar berpindah setelah Next,
        bukan sekadar menunggu jaringan tenang.
        """
        return self.page.get_by_text("/3").first.inner_text().strip()

    # ------------------------------------------------------------------
    # Step 2 — Register Legal
    # ------------------------------------------------------------------

    def complete_step_two(self) -> None:
        """
        Step 2 hanya berisi Legal Document yang OPSIONAL.

        Diverifikasi lewat inspeksi: nol input, nol combobox. Satu-satunya
        kontrol adalah "+ Add Document" yang membuka dialog terpisah.

        Karena opsional, step ini dilewati dengan klik Next langsung —
        tidak ada yang perlu diisi untuk membuat company.
        """
        expect(self.page.get_by_text("Register Legal", exact=True)).to_be_visible()
        self.click_next()

    # ------------------------------------------------------------------
    # Step 3 — Create Your Branch
    # ------------------------------------------------------------------

    def complete_step_three(self, data: dict, use_company_data: bool = True) -> None:
        """
        Step 3 membuat branch pertama.

        Form ini mengaku opsional ("If left unfilled, a default branch will
        be created"), TETAPI Branch Name sudah terisi otomatis dengan
        "Headquarter" — dan catatan di bawah form menyatakan bahwa mengisi
        Branch Name membuat seluruh field wajib diisi.

        Jadi dalam praktiknya form ini TIDAK opsional: Street Address dan
        Country tetap harus diisi.

        Tombol "Fill in with the same data from the Company records"
        menyalin alamat dan negara dari Step 1. Dipakai secara default
        karena mengurangi kemungkinan salah ketik dan mencerminkan alur
        yang paling wajar dipakai pengguna.
        """
        expect(self.page.get_by_text("Create Your Branch", exact=True)).to_be_visible()

        if use_company_data:
            self.fill_from_company_records.click()
        else:
            self.page.get_by_placeholder("Input Address").fill(data["street_address"])
            # Step 3 punya combobox sendiri di indeks 0 — bukan indeks Step 1.
            self.branch_country.click()
            listbox = self.page.get_by_role("listbox")
            expect(listbox).to_be_visible()
            listbox.get_by_role("option", name=data["country"], exact=True).click()
            expect(listbox).not_to_be_visible()

        # Persetujuan syarat & ketentuan wajib dicentang sebelum Register aktif.
        self.agree_checkbox.check()

        expect(self.register_button).to_be_enabled()
        self.register_button.click()
        self.page.wait_for_load_state("networkidle")

    def branch_name(self) -> str:
        """
        Nilai Branch Name yang terisi otomatis (biasanya "Headquarter").

        Dibaca, bukan diasumsikan — nilai default bisa berubah, dan test
        yang memverifikasi branch perlu tahu nilai sebenarnya.
        """
        return self.page.get_by_placeholder("Input Branch Name").input_value()

    def is_register_enabled(self) -> bool:
        """Status tombol Register. Dipakai memverifikasi checkbox wajib dicentang."""
        return self.register_button.is_enabled()

    # ------------------------------------------------------------------
    # Validasi
    # ------------------------------------------------------------------

    def field_error_text(self, key: str) -> str:
        """
        Pesan error untuk satu field.

        Struktur elemen error belum terverifikasi — form belum pernah
        disubmit dalam keadaan tidak valid saat inspeksi. Implementasi ini
        mencari teks error di dekat field, dan mengembalikan string kosong
        bila tidak ketemu agar test yang memanggilnya tetap punya assert
        sendiri yang bermakna.
        """
        field = self.f.get(key)
        if field is None:
            return ""

        container = field.locator("xpath=ancestor::div[1]")
        error = container.locator("text=/required|wajib|invalid|tidak valid/i")
        return error.first.inner_text().strip() if error.count() > 0 else ""