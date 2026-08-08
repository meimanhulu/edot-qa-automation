"""
RegisterCompanyWizard — wizard 3 langkah Register Company.

Bagian tersulit: cascade dependen
    Country > Province > City > District > Zone > Postal Code

Tiap child baru terisi setelah parent dipilih, dan Next tetap disabled
sampai seluruh Step 1 valid.
"""
from playwright.sync_api import Page

from .base_page import BasePage

# SELECTOR — ganti setelah inspeksi DOM.
SEL = {
    "name": "wizard-company-name",
    "email": "wizard-email",
    "phone": "wizard-phone",
    "industry_type": "wizard-industry-type",
    "company_type": "wizard-company-type",
    "language": "wizard-language",
    "street_address": "wizard-street-address",
    "country": "wizard-country",
    "province": "wizard-province",
    "city": "wizard-city",
    "district": "wizard-district",
    "zone": "wizard-zone",
    "postal_code": "wizard-postal-code",
    "next_button": "wizard-next",
    "submit_button": "wizard-submit",
}

# Urutan cascade — dipakai select_cascade() dan get_cascade_values().
# Didefinisikan sekali supaya urutannya tidak pernah salah di salah satu tempat.
CASCADE_ORDER = ["country", "province", "city", "district", "zone", "postal_code"]

# Field teks biasa pada Step 1.
TEXT_FIELDS = ["name", "email", "phone", "street_address"]

# Dropdown non-cascade pada Step 1.
SIMPLE_SELECTS = ["industry_type", "company_type", "language"]


class RegisterCompanyWizard(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.f = {key: page.get_by_test_id(testid) for key, testid in SEL.items()}

    # ---------------- Step 1 ----------------

    def fill_basic_fields(self, data: dict) -> None:
        """Isi field non-cascade. Cascade ditangani terpisah karena butuh menunggu."""
        for key in TEXT_FIELDS:
            self.f[key].fill(str(data[key]))
        for key in SIMPLE_SELECTS:
            self.f[key].select_option(label=str(data[key]))

    def select_cascade(self, country, province, city, district, zone, postal_code) -> None:
        """
        Pilih cascade berurutan, MENUNGGU tiap child terisi sebelum memilihnya.

        Ini alasan utama select_and_wait_child() ada di BasePage: pola
        'pilih parent lalu tunggu child' harus terjadi di SETIAP level.
        Melewatkannya di satu level saja sudah cukup membuat suite flaky —
        Playwright akan mengklik dropdown yang opsinya belum termuat.
        """
        values = [country, province, city, district, zone, postal_code]

        for i in range(len(CASCADE_ORDER) - 1):
            parent_key = CASCADE_ORDER[i]
            child_key = CASCADE_ORDER[i + 1]
            self.select_and_wait_child(
                parent=self.f[parent_key],
                value=values[i],
                child=self.f[child_key],
            )

        # Level terakhir tidak punya child yang perlu ditunggu.
        self.f["postal_code"].select_option(label=str(postal_code))

    def get_cascade_values(self) -> dict[str, str]:
        """
        Nilai terpilih keenam dropdown cascade.

        Dipakai TC-WEB-006 untuk membuktikan child TER-RESET saat parent diubah:
        ambil snapshot sebelum dan sesudah mengubah Province, lalu bandingkan.
        """
        return {key: self.value_of(self.f[key]) for key in CASCADE_ORDER}

    def change_province(self, new_province: str) -> None:
        """
        Ubah Province saja, tanpa menyentuh child-nya.

        Dipakai TC-WEB-006. Sengaja TIDAK menunggu child terisi di sini —
        yang sedang diuji justru apa yang terjadi pada child setelah parent
        berubah. Menunggu di sini akan menyembunyikan perilaku yang diuji.
        """
        self.f["province"].select_option(label=new_province)

    def is_next_enabled(self) -> bool:
        """
        Status enabled tombol Next.

        Dipakai TC-WEB-006 (Next disabled sampai step valid) dan TC-WEB-007
        (Next kembali disabled saat field required dikosongkan).
        """
        return self.f["next_button"].is_enabled()

    def clear_field(self, field: str) -> None:
        """Kosongkan satu field. Dipakai TC-WEB-007."""
        self.f[field].fill("")

    def click_next(self) -> None:
        self.f["next_button"].click()
        self.page.wait_for_load_state("networkidle")

    # ---------------- Step 2 & 3 ----------------
    # TODO(inspeksi): isi setelah tahu field apa saja yang ada di Step 2 dan 3.
    # Brief hanya merinci Step 1; sisanya harus dilihat langsung di aplikasi.

    def complete_step_two(self, data: dict) -> None:
        """TODO: isi field Step 2, lalu click_next()."""
        self.click_next()

    def complete_step_three(self, data: dict) -> None:
        """TODO: isi field Step 3 sebelum submit()."""
        pass

    def submit(self) -> None:
        self.f["submit_button"].click()
        self.page.wait_for_load_state("networkidle")

    def submit_twice(self) -> None:
        """
        Klik submit dua kali secepat mungkin.

        Dipakai TC-WEB-010. Sengaja TANPA menunggu di antara dua klik —
        justru itu kondisi yang menghasilkan record duplikat di produksi.
        """
        self.f["submit_button"].click()
        self.f["submit_button"].click(force=True, timeout=2000)
        self.page.wait_for_load_state("networkidle")

    # ---------------- Validasi ----------------

    def field_error_text(self, field: str) -> str:
        """
        Teks error untuk field tertentu.

        Konvensi: elemen error memakai testid `<field-testid>-error`.
        Sesuaikan bila DOM eSuite memakai pola berbeda.
        """
        return self.text_of(self.page.get_by_test_id(f"{SEL[field]}-error"))
