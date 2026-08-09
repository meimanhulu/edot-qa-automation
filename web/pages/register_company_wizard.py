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

1. CASCADE TIDAK ADA DI STEP 1.
   Brief menyebut Country > Province > City > District > Zone > Postal Code
   berada di Step 1. Kenyataannya Step 1 hanya punya Country. Lima level
   sisanya baru muncul di halaman Manage Company setelah company dibuat.

2. SEMUA DROPDOWN ADALAH button[role=combobox], BUKAN <select>.
   Diverifikasi: querySelectorAll('select') mengembalikan nol elemen.
   Konsekuensinya select_option() TIDAK BISA dipakai sama sekali —
   dropdown harus diklik untuk membuka, lalu opsinya diklik.

3. FIELD TIDAK PUNYA ATRIBUT name.
   Yang tersedia hanya placeholder, sehingga get_by_placeholder() menjadi
   pilihan terbaik yang ada. Ini prioritas ke-3 brief (atribut stabil);
   data-testid tidak tersedia di seluruh aplikasi.
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


class RegisterCompanyWizard(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

        self.f = {
            key: page.get_by_placeholder(ph) for key, ph in PLACEHOLDERS.items()
        }

        self.next_button = page.get_by_role("button", name="Next")
        self.back_button = page.get_by_role("button", name="Back", exact=True)
        self.back_to_companies = page.get_by_role("button", name="Back to Companies")
        self.heading = page.get_by_text("Register Company", exact=True)

        # --- Step 3: Create Your Branch ---
        self.fill_from_company_records = page.get_by_role(
            "button", name="Fill in with the same data from the Company records"
        )
        self.register_button = page.get_by_role("button", name="Register", exact=True)
        # Checkbox persetujuan tidak punya label yang bisa dipakai get_by_label,
        # jadi diakses lewat role — hanya ada satu checkbox di step ini.
        self.agree_checkbox = page.get_by_role("checkbox")

    # ------------------------------------------------------------------
    # Combobox — pola yang dipakai seluruh dropdown di aplikasi ini
    # ------------------------------------------------------------------

    def _combobox(self, key: str) -> Locator:
        """
        Combobox berdasarkan teks labelnya.

        Dipakai SEBELUM opsi dipilih. Setelah dipilih, teks tombol berganti
        jadi nilai terpilih, sehingga locator ini tidak lagi cocok — itulah
        sebabnya ada selected_value() yang membaca lewat urutan.
        """
        return self.page.get_by_role("button", name=COMBOBOX_LABELS[key])

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
        return self.page.get_by_role("combobox").nth(index).inner_text().strip()

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

    def fill_dropdowns(self, data: dict) -> None:
        """
        Isi keempat combobox Step 1.

        Country dipilih TERAKHIR: pada halaman Manage, mengubah Country
        me-reset Province dan turunannya. Urutan ini menjaga polanya
        konsisten meski di Step 1 belum ada dependensi.
        """
        self.select_option("industry_type", data["industry_type"])
        self.select_option("company_type", data["company_type"])
        self.select_option("language", data["language"])
        self.select_option("country", data["country"])

    def fill_step_one(self, data: dict) -> None:
        """Isi seluruh Step 1: field teks lalu dropdown."""
        self.fill_text_fields(data)
        self.fill_dropdowns(data)

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
            self.select_option("country", data["country"])

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