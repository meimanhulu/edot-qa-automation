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
   dipilih, lima field BARU tampil: Province, City, District, Sub District,
   dan Postal Code.

   Field-field itu sudah ADA di DOM sejak awal, hanya tersembunyi — bukan
   ditambahkan belakangan. Karena itu seluruh locator combobox memakai
   filter `:visible`; tanpanya, indeks menunjuk elemen tersembunyi.

   Dua perbedaan dari brief:
     - brief menyebut level keempat "Zone"; aplikasi memakai "Sub District"
     - brief menyebut Postal Code sebagai pilihan; aplikasi mengisinya
       OTOMATIS setelah Sub District dipilih. Elemennya COMBOBOX ber-status
       disabled, bukan <input> — sehingga get_by_placeholder() tidak
       menemukannya dan nilainya dibaca lewat inner_text()

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
import re

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

        self.next_button = page.get_by_role("button", name="Next")

        # Penanda unik tiap langkah — dipakai click_next() untuk memastikan
        # transisi benar-benar selesai. Elemen, bukan teks: lebih pasti.
        self.step_two_marker = page.get_by_role("button", name="+ Add Document")
        self.step_three_marker = page.get_by_placeholder("Input Branch Name")
        self.back_button = page.get_by_role("button", name="Back", exact=True)
        self.back_to_companies = page.get_by_role("button", name="Back to Companies")
        self.heading = page.get_by_text("Register Company", exact=True)

        # --- Step 3: Create Your Branch ---
        self.fill_from_company_records = page.get_by_role(
            "button", name="Fill in with the same data from the Company records"
        )
        self.register_button = page.get_by_role("button", name="Register", exact=True)
        # Step 3 hanya punya SATU combobox (Country), jadi indeksnya 0.
        self.branch_country = page.locator("[role=combobox]:visible").first
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

        Filter `:visible` WAJIB. Keempat combobox cascade (Province, City,
        District, Sub District) sudah dirender di DOM sejak awal dalam
        keadaan tersembunyi, lalu ditampilkan setelah Country dipilih —
        bukan ditambahkan belakangan. Tanpa filter ini, nth(4) menunjuk
        combobox tersembunyi alih-alih Country, dan gagalnya berbunyi
        "element is not visible" yang menyesatkan.

        Pola yang sama juga muncul di halaman login: input password sudah
        ada sebagai type=hidden sebelum layarnya tampil.

        Konsekuensi yang diterima sadar: locator ini rapuh terhadap
        perubahan URUTAN field. Alternatifnya hanya text selector, yang
        justru lebih rapuh — teksnya berubah begitu opsi dipilih.
        """
        return self.page.locator("[role=combobox]:visible").nth(COMBOBOX_ORDER[key])

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

        # `.last` dipakai, bukan get_by_role("listbox") polos.
        #
        # Radix kadang menyisakan listbox sebelumnya di DOM sesaat setelah
        # ditutup. Dengan locator polos, dua listbox memicu strict mode
        # violation dan penantiannya menggantung. `.last` selalu menunjuk
        # listbox yang paling baru dibuka.
        listbox = self.page.get_by_role("listbox").last
        expect(listbox).to_be_visible(timeout=15000)

        # Dropdown cascade punya kotak Search. Untuk daftar panjang (Province
        # punya puluhan opsi), opsi yang dicari mungkin belum ter-render
        # sampai difilter. Mengetik lebih dulu membuatnya pasti terlihat.
        search = listbox.get_by_placeholder("Search")
        if search.count() > 0:
            search.fill(value)

        option = listbox.get_by_text(value, exact=True)

        # Gagal CEPAT dengan pesan yang menyebut penyebabnya.
        #
        # Tanpa ini, nilai yang tidak ada di daftar berujung timeout 30 detik
        # dengan pesan "waiting for locator" — yang terbaca seperti aplikasi
        # rusak, padahal DATANYA yang salah.
        if option.count() == 0:
            available = [
                t.strip() for t in listbox.locator("[role=option]").all_inner_texts()
            ][:15]
            raise AssertionError(
                f"Opsi {value!r} tidak ada di dropdown {key!r}.\n"
                f"Pilihan yang tersedia: {available}\n"
                "Periksa data test — untuk cascade, kemungkinan besar "
                "kombinasi wilayahnya tidak sah."
            )

        option.first.click()

        # Tunggu listbox tertutup sebelum menyentuh field berikutnya, supaya
        # klik berikutnya tidak mengenai overlay yang masih terbuka.
        expect(listbox).not_to_be_visible(timeout=15000)

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

        listbox = self.page.get_by_role("listbox").last
        expect(listbox).to_be_visible(timeout=15000)

        options = listbox.locator("[role=option]")
        expect(options.first).to_be_visible(timeout=15000)

        chosen = options.first.inner_text().strip()
        options.first.click()

        expect(listbox).not_to_be_visible(timeout=15000)
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
        return self.page.locator("[role=combobox]:visible").nth(index).inner_text().strip()

    # ------------------------------------------------------------------
    # Step 1
    # ------------------------------------------------------------------

    def open(self, base_url: str) -> None:
        """
        Buka wizard dan tunggu judulnya tampil.

        Timeout 30 detik: halaman ini kerap menampilkan "Please wait..." lebih
        lama daripada bawaan expect(), terutama saat aplikasi sedang berat.
        """
        self.goto(f"{base_url.rstrip('/')}{WIZARD_PATH}")
        expect(self.heading).to_be_visible(timeout=30000)

    def fill_text_fields(self, data: dict) -> None:
        """Isi keempat field teks Step 1."""
        for key, locator in self.f.items():
            locator.fill(str(data[key]))

    def fill_dropdowns(self, data: dict) -> dict[str, str]:
        """
        Isi seluruh combobox Step 1.

        Pembagiannya:
          - Industry Type, Company Type, Language  -> opsi pertama
          - Country                                -> eksplisit dari data
          - cascade (Province s/d Sub District)    -> opsi pertama

        Mengembalikan dict nilai yang benar-benar terpilih — dipakai test
        sebagai expected value saat verifikasi Tier 2.

        Country diisi setelah tiga dropdown pertama karena memilihnya
        MEMUNCULKAN lima field baru. Mengisinya lebih awal akan menggeser
        indeks combobox lain di tengah pengisian.
        """
        chosen = {}

        # Tiga dropdown ini isinya statis dan tidak saling bergantung,
        # jadi opsi pertama selalu sah.
        for key in ("industry_type", "company_type", "language"):
            chosen[key] = self.select_first_option(key)

        # Country DIPILIH EKSPLISIT, tidak memakai opsi pertama.
        #
        # Opsi pertama adalah "Philippines", dan memilihnya mengubah seluruh
        # bentuk form: cascade-nya menjadi Region > Province > City > Barangay
        # (bukan Province > City > District > Sub District), dan prefix telepon
        # berubah jadi +63 sehingga nomor Indonesia ditolak.
        #
        # Suite ini fokus pada wilayah Indonesia, jadi negaranya ditentukan
        # oleh data test — bukan oleh urutan opsi.
        self.select_option("country", data["country"])
        chosen["country"] = data["country"]

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

        # Postal Code terisi otomatis setelah Sub District dipilih.
        #
        # Ditunggu dengan pola 5 DIGIT, bukan sekadar "tidak kosong":
        # sebelum terisi, isinya adalah teks placeholder "Choose Postal Code",
        # sehingga pengecekan not_to_have_text("") akan lolos padahal
        # nilainya belum ada.
        postal = self.page.locator("[role=combobox][disabled]").first
        expect(postal).to_be_visible()
        expect(postal).to_have_text(re.compile(r"^\s*\d{5}\s*$"), timeout=30000)

        chosen["postal_code"] = self.postal_code()
        return chosen

    def postal_code(self) -> str:
        """
        Kode pos yang diisi OTOMATIS oleh aplikasi.

        Dibaca, bukan ditentukan — nilainya berasal dari Sub District yang
        dipilih. Dipakai sebagai expected value saat verifikasi detail.

        PENTING: Postal Code adalah COMBOBOX ber-status disabled, bukan
        <input>. get_by_placeholder() tidak akan menemukannya karena hanya
        cocok ke input/textarea — dan kegagalannya berupa timeout saat
        menunggu nilai, padahal nilainya sudah ada di layar.

        Karena disabled, ia TIDAK ikut terhitung oleh selector `:visible`
        yang dipakai combobox lain, sehingga diakses lewat locator terpisah.
        """
        return self.page.locator("[role=combobox][disabled]").first.inner_text().strip()

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

        listbox = self.page.get_by_role("listbox").last
        expect(listbox).to_be_visible(timeout=15000)

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
        Status enabled tombol Next SAAT INI, tanpa menunggu.

        Dipakai hanya untuk membaca keadaan, bukan untuk assert. Untuk
        assert, pakai expect_next_enabled() atau expect_next_disabled()
        yang melakukan polling.
        """
        return self.next_button.is_enabled()

    def expect_next_enabled(self) -> None:
        """
        Tunggu sampai Next benar-benar enabled.

        Memakai expect() yang melakukan polling, bukan is_enabled() yang
        memeriksa saat itu juga. Validasi form berjalan di React dan butuh
        satu siklus render setelah field berubah — pemeriksaan seketika bisa
        gagal padahal aplikasinya berperilaku benar.
        """
        expect(self.next_button).to_be_enabled()

    def expect_next_disabled(self) -> None:
        """
        Tunggu sampai Next benar-benar disabled.

        Dipakai test Negative: setelah field wajib dikosongkan, tombol harus
        kembali terkunci. Polling diperlukan karena perubahannya tidak
        seketika.
        """
        expect(self.next_button).to_be_disabled()

    def clear_field(self, key: str) -> None:
        """Kosongkan satu field teks. Dipakai TC-WEB-007."""
        self.f[key].fill("")

    def click_next(self, expect_locator: Locator | None = None) -> None:
        """
        Klik Next dan tunggu langkah berikutnya benar-benar tampil.

        `expect_locator` adalah ELEMEN penanda halaman tujuan — bukan teks.

        Kenapa elemen, bukan teks: pencocokan teks rapuh. Heading bisa
        terpecah antar elemen, membawa spasi tersembunyi, atau dibungkus
        node lain, sehingga get_by_text(..., exact=True) meleset dan
        penantiannya menggantung sampai timeout — padahal halamannya sudah
        berpindah.

        Kenapa BUKAN networkidle: Playwright menyarankan menghindarinya untuk
        SPA. eSuite memuat data lewat XHR yang berjalan terus, sehingga
        kondisi "jaringan tenang" mungkin tidak pernah tercapai.
        """
        self.next_button.click()

        if expect_locator is not None:
            expect(expect_locator).to_be_visible(timeout=30000)
        else:
            expect(self.next_button).not_to_be_visible(timeout=30000)

    def current_step(self) -> str:
        """
        Penunjuk langkah, mis. "1/3".

        Dipakai untuk memastikan wizard benar-benar berpindah setelah Next,
        bukan sekadar menunggu jaringan tenang.
        """
        indicator = self.page.get_by_text("/3")
        if indicator.count() == 0:
            return ""
        return indicator.first.inner_text().strip()

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
        expect(self.step_two_marker).to_be_visible()
        self.click_next(expect_locator=self.step_three_marker)

    # ------------------------------------------------------------------
    # Step 3 — Create Your Branch
    # ------------------------------------------------------------------

    def complete_step_three(self, data: dict | None = None) -> None:
        """
        Selesaikan Step 3 (Create Your Branch) dan tekan Register.

        STRUKTUR STEP 3 (hasil inspeksi):
          Saat Branch Name KOSONG, form hanya menampilkan Branch Name dan
          checkbox persetujuan. Street Address, Country, dan tombol "Fill in
          with the same data from the Company records" BARU MUNCUL setelah
          Branch Name diisi.

          Ini sesuai catatan di bawah form: "by filling in the branch name
          column, it is mandatory to fill in all the forms provided".

        Jalur yang dipakai: BIARKAN Branch Name kosong.
          Form menyatakan dirinya opsional — "If left unfilled, a default
          branch will be created". Membiarkannya kosong adalah jalur paling
          sedikit langkah dan paling sedikit yang bisa gagal.

          Bila ternyata Register tetap terkunci dengan Branch Name kosong,
          method ini mengisi Branch Name lalu field yang menyusul. Itu berarti
          klaim "optional" pada form tidak benar — dan perbedaannya dicatat
          lewat pesan assert, bukan disembunyikan.
        """
        expect(self.step_three_marker).to_be_visible()

        # Persetujuan syarat & ketentuan wajib dicentang lebih dulu.
        self.agree_checkbox.check()

        if self.is_register_enabled():
            self.register_button.click()
            self._wait_after_register()
            return

        # Register masih terkunci -> form ternyata tidak benar-benar opsional.
        # Isi Branch Name; Street Address dan Country akan menyusul muncul.
        branch_input = self.page.get_by_placeholder("Input Branch Name")
        branch_input.fill("Headquarter")

        # Tombol penyalin data company baru tersedia setelah Branch Name diisi.
        if self.fill_from_company_records.count() > 0:
            self.fill_from_company_records.click()
        elif data:
            self.page.get_by_placeholder("Input Address").fill(data["street_address"])
            self.branch_country.click()
            listbox = self.page.get_by_role("listbox")
            expect(listbox).to_be_visible()
            listbox.get_by_text(data["country"], exact=True).click()
            expect(listbox).not_to_be_visible()

        expect(self.register_button).to_be_enabled(timeout=15000)
        self.register_button.click()
        self._wait_after_register()

    def _wait_after_register(self) -> None:
        """
        Tunggu proses pendaftaran selesai setelah tombol Register ditekan.

        Setelah Register, aplikasi mengarahkan ke DAFTAR companies
        (/companies), BUKAN ke halaman detail company yang baru dibuat.
        Diverifikasi lewat log navigasi Playwright:

            navigated to "https://esuite.edot.id/companies"

        Company-nya memang terbuat — jumlah di header bertambah — hanya saja
        pemanggil harus mencarinya sendiri di daftar untuk membuka detailnya
        dan membaca Company ID.
        """
        self.page.wait_for_url("**/companies", timeout=60000)

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